//! The HTTP API. The public site never calls it directly: its Cloudflare Worker forwards searches here with a
//! secret key (X-App-Key), so only the site can use it. Each visitor (by IP, which the Worker passes on) also
//! has a rate limit, since every search costs CPU on a small server.

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
    collections::HashMap,
    env,
    path::PathBuf,
    sync::{Arc, Mutex, OnceLock},
    time::{Duration, Instant},
};
use tokio::sync::Semaphore;

pub struct App {
    pub store: Store,
    pub model: OnceLock<Embedder>,
    pub failed: OnceLock<String>,
    /// The shared secret the site's Worker sends. With none configured, every search is refused.
    pub app_key: Option<String>,
    pub limits: RateLimit,
    /// One embedding at a time keeps memory flat on a small server.
    pub gate: Semaphore,
}

/// At most `per_window` searches per client in each window.
pub struct RateLimit {
    pub per_window: u32,
    pub window: Duration,
    seen: Mutex<HashMap<String, (Instant, u32)>>,
}

impl RateLimit {
    pub fn new(per_window: u32, window: Duration) -> Self {
        Self { per_window, window, seen: Mutex::new(HashMap::new()) }
    }

    pub fn allow(&self, client: &str, now: Instant) -> bool {
        let mut seen = self.seen.lock().unwrap();
        if seen.len() > 10_000 {
            let window = self.window;
            seen.retain(|_, (start, _)| now.duration_since(*start) < window);
        }
        let entry = seen.entry(client.to_string()).or_insert((now, 0));
        if now.duration_since(entry.0) >= self.window {
            *entry = (now, 0);
        }
        entry.1 += 1;
        entry.1 <= self.per_window
    }
}

/// Compares in constant time, so the key can't be guessed byte by byte from response timing.
pub fn same_key(given: &[u8], expected: &[u8]) -> bool {
    given.len() == expected.len() && given.iter().zip(expected).fold(0u8, |acc, (a, b)| acc | (a ^ b)) == 0
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

fn no_store(mut r: Response) -> Response {
    r.headers_mut().insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
    r
}

fn fail(code: StatusCode, msg: &str) -> Response {
    (code, Json(json!({ "error": msg }))).into_response()
}

pub async fn search(State(app): State<Arc<App>>, headers: HeaderMap, Query(q): Query<SearchQuery>) -> Response {
    let given = headers.get("x-app-key").map(|v| v.as_bytes()).unwrap_or_default();
    if !app.app_key.as_deref().is_some_and(|k| same_key(given, k.as_bytes())) {
        return no_store(fail(StatusCode::FORBIDDEN, "This API only answers the council site."));
    }
    let client = headers.get("x-client-ip").and_then(|v| v.to_str().ok()).unwrap_or("unknown").to_string();
    if !app.limits.allow(&client, Instant::now()) {
        return no_store(fail(StatusCode::TOO_MANY_REQUESTS, "Too many searches in a short time. Wait a minute and try again."));
    }
    let p = match params(&q) {
        Ok(p) => p,
        Err(e) => return no_store(fail(StatusCode::BAD_REQUEST, &e)),
    };
    if let Some(e) = app.failed.get() {
        return no_store(fail(StatusCode::SERVICE_UNAVAILABLE, &format!("The search model failed to load: {e}")));
    }
    if app.model.get().is_none() {
        return no_store(fail(StatusCode::SERVICE_UNAVAILABLE, "Search is starting up. Try again in a minute."));
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
        Ok(Ok(body)) => no_store(Json(body).into_response()),
        Ok(Err(e)) => no_store(fail(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string())),
        Err(e) => no_store(fail(StatusCode::INTERNAL_SERVER_ERROR, &e.to_string())),
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
    let app_key = env::var("APP_KEY").ok().filter(|k| k.len() >= 32);
    if app_key.is_none() {
        eprintln!("APP_KEY is missing or shorter than 32 characters, so every search will be refused");
    }
    let app = Arc::new(App {
        store,
        model: OnceLock::new(),
        failed: OnceLock::new(),
        app_key,
        limits: RateLimit::new(env::var("SEARCHES_PER_MINUTE").ok().and_then(|v| v.parse().ok()).unwrap_or(30), Duration::from_secs(60)),
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
    fn rate_limit_resets_each_window() {
        let limit = RateLimit::new(2, Duration::from_secs(60));
        let t = Instant::now();
        assert!(limit.allow("a", t) && limit.allow("a", t));
        assert!(!limit.allow("a", t));
        assert!(limit.allow("b", t), "other visitors are unaffected");
        assert!(limit.allow("a", t + Duration::from_secs(61)));
    }

    #[test]
    fn keys_must_match_exactly() {
        assert!(same_key(b"secret-key", b"secret-key"));
        assert!(!same_key(b"secret-kez", b"secret-key"));
        assert!(!same_key(b"secret", b"secret-key"));
        assert!(!same_key(b"", b"secret-key"));
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
