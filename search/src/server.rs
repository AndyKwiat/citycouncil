//! The HTTP API. Radify's gate (Google login, allowlist) sits in front and adds X-Auth-Email; this server
//! also refuses any request that doesn't come from the council site's own pages (the Origin check),
//! so only the app, used by a signed-in person, can query it.

use crate::{
    embed::Embedder,
    search::{Params, Store, KINDS},
};
use anyhow::{Context, Result};
use axum::{
    extract::{Query, State},
    http::{header, HeaderMap, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use serde::Deserialize;
use serde_json::json;
use std::{
    env,
    path::PathBuf,
    sync::{Arc, OnceLock},
    time::Instant,
};
use tokio::sync::Semaphore;

pub struct App {
    pub store: Store,
    pub model: OnceLock<Embedder>,
    pub failed: OnceLock<String>,
    pub origins: Vec<String>,
    pub require_login: bool,
    /// One embedding at a time keeps memory flat on a small server.
    pub gate: Semaphore,
}

#[derive(Deserialize, Default)]
pub struct SearchQuery {
    q: Option<String>,
    kinds: Option<String>,
    from: Option<String>,
    to: Option<String>,
    limit: Option<usize>,
}

fn is_date(s: &str) -> bool {
    s.len() == 10 && s.chars().enumerate().all(|(i, c)| if i == 4 || i == 7 { c == '-' } else { c.is_ascii_digit() })
}

pub fn params(q: &SearchQuery) -> Result<Params, String> {
    let text: String = q.q.clone().unwrap_or_default().trim().chars().take(300).collect();
    if text.is_empty() {
        return Err("Type something to search for.".into());
    }
    let mut p = Params::new(&text);
    if let Some(k) = &q.kinds {
        p.kinds = k.split(',').map(str::trim).filter(|k| KINDS.contains(k)).map(String::from).collect();
        if p.kinds.is_empty() {
            return Err("Pick at least one kind of result.".into());
        }
    }
    for (value, slot) in [(&q.from, &mut p.from), (&q.to, &mut p.to)] {
        if let Some(v) = value.as_deref().filter(|v| !v.is_empty()) {
            if !is_date(v) {
                return Err("Dates must look like 2025-01-31.".into());
            }
            *slot = v.to_string();
        }
    }
    p.limit = q.limit.unwrap_or(25).clamp(1, 60);
    Ok(p)
}

fn cors(origin: Option<&str>, mut r: Response) -> Response {
    if let Some(o) = origin.and_then(|o| HeaderValue::from_str(o).ok()) {
        let h = r.headers_mut();
        h.insert(header::ACCESS_CONTROL_ALLOW_ORIGIN, o);
        h.insert(header::ACCESS_CONTROL_ALLOW_CREDENTIALS, HeaderValue::from_static("true"));
        h.insert(header::VARY, HeaderValue::from_static("Origin"));
    }
    r.headers_mut().insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
    r
}

fn fail(code: StatusCode, msg: &str) -> Response {
    (code, Json(json!({ "error": msg }))).into_response()
}

pub async fn search(State(app): State<Arc<App>>, headers: HeaderMap, Query(q): Query<SearchQuery>) -> Response {
    let origin = headers.get(header::ORIGIN).and_then(|v| v.to_str().ok()).filter(|o| app.origins.iter().any(|a| a == o));
    if origin.is_none() {
        return fail(StatusCode::FORBIDDEN, "This API only answers the council site.");
    }
    let origin = origin.map(String::from);
    if app.require_login && headers.get("x-auth-email").is_none() {
        return cors(origin.as_deref(), fail(StatusCode::UNAUTHORIZED, "Sign in first."));
    }
    let p = match params(&q) {
        Ok(p) => p,
        Err(e) => return cors(origin.as_deref(), fail(StatusCode::BAD_REQUEST, &e)),
    };
    if let Some(e) = app.failed.get() {
        return cors(origin.as_deref(), fail(StatusCode::SERVICE_UNAVAILABLE, &format!("The search model failed to load: {e}")));
    }
    if app.model.get().is_none() {
        return cors(origin.as_deref(), fail(StatusCode::SERVICE_UNAVAILABLE, "Search is starting up. Try again in a minute."));
    }
    let _permit = app.gate.acquire().await.expect("semaphore");
    let worker = app.clone();
    let result = tokio::task::spawn_blocking(move || {
        let t = Instant::now();
        let v = worker.model.get().expect("loaded").embed_query(&p.q)?;
        let embed_ms = t.elapsed().as_millis();
        let found = worker.store.search(&p, &v)?;
        Ok::<_, anyhow::Error>(json!({ "query": p.q, "results": found.results, "searched": found.searched,
                                       "keyword_matches": found.keyword_matches, "weak": found.weak,
                                       "embed_ms": embed_ms, "total_ms": t.elapsed().as_millis() }))
    })
    .await;
    match result {
        Ok(Ok(body)) => cors(origin.as_deref(), Json(body).into_response()),
        Ok(Err(e)) => cors(origin.as_deref(), fail(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string())),
        Err(e) => cors(origin.as_deref(), fail(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string())),
    }
}

pub async fn health(State(app): State<Arc<App>>) -> Response {
    // Healthy as soon as it serves; the model may still be loading (searches say so).
    Json(json!({ "ok": true, "chunks": app.store.len(), "model_ready": app.model.get().is_some(),
                 "model_error": app.failed.get() }))
    .into_response()
}

pub fn router(app: Arc<App>) -> Router {
    Router::new().route("/healthz", get(health)).route("/search", get(search)).with_state(app)
}

pub fn run() -> Result<()> {
    let port: u16 = env::var("PORT").unwrap_or_else(|_| "8760".into()).parse()?;
    let static_dir = PathBuf::from(env::var("STATIC_DIR").unwrap_or_else(|_| ".".into()));
    let data_dir = PathBuf::from(env::var("DATA_DIR").unwrap_or_else(|_| "model-cache".into()));
    let db = env::var("SEARCH_DB").map(PathBuf::from).unwrap_or_else(|_| static_dir.join("search.sqlite"));
    let model_dir = env::var("MODEL_DIR").map(PathBuf::from).unwrap_or_else(|_| data_dir.join("model"));
    let store = Store::open(&db).with_context(|| format!("opening {}", db.display()))?;
    eprintln!("loaded {} chunks from {}", store.len(), db.display());
    let origins = env::var("ALLOWED_ORIGINS").unwrap_or_else(|_| "https://citycouncil.akwiat.com".into());
    let app = Arc::new(App {
        store,
        model: OnceLock::new(),
        failed: OnceLock::new(),
        origins: origins.split(',').map(|s| s.trim().trim_end_matches('/').to_string()).filter(|s| !s.is_empty()).collect(),
        require_login: env::var("REQUIRE_LOGIN").map(|v| v != "0").unwrap_or(true),
        gate: Semaphore::new(1),
    });
    let loader = app.clone();
    std::thread::spawn(move || {
        let t = Instant::now();
        let result = crate::embed::fetch(&model_dir).and_then(|_| Embedder::load(&model_dir, crate::dtype()));
        match result {
            Ok(m) => {
                eprintln!("model ready in {:?}", t.elapsed());
                let _ = loader.model.set(m);
            }
            Err(e) => {
                eprintln!("model failed: {e:#}");
                let _ = loader.failed.set(format!("{e:#}"));
            }
        }
    });
    tokio::runtime::Builder::new_multi_thread().enable_all().build()?.block_on(async move {
        let listener = tokio::net::TcpListener::bind(("127.0.0.1", port)).await?;
        eprintln!("listening on 127.0.0.1:{port}");
        axum::serve(listener, router(app)).await?;
        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn q(text: &str, kinds: Option<&str>, from: Option<&str>) -> SearchQuery {
        SearchQuery { q: Some(text.into()), kinds: kinds.map(Into::into), from: from.map(Into::into), ..Default::default() }
    }

    #[test]
    fn params_are_checked() {
        assert!(params(&q("  ", None, None)).is_err());
        assert!(params(&q("x", Some("bogus"), None)).is_err());
        assert_eq!(params(&q("x", Some("vote, minutes,bogus"), None)).unwrap().kinds, vec!["vote", "minutes"]);
        assert!(params(&q("x", None, Some("2025-1-1"))).is_err());
        assert_eq!(params(&q("x", None, Some("2025-01-01"))).unwrap().from, "2025-01-01");
        assert_eq!(params(&q(&"y".repeat(1000), None, None)).unwrap().q.len(), 300);
        assert_eq!(params(&SearchQuery { q: Some("x".into()), limit: Some(500), ..Default::default() }).unwrap().limit, 60);
    }
}
