//! Hybrid search: cosine similarity over every chunk's vector, plus SQLite FTS5 keyword matches,
//! merged with reciprocal rank fusion. Vectors find related meaning ("homelessness" → encampments);
//! keywords keep exact names and by-law numbers from slipping.

use crate::index::from_blob;
use anyhow::Result;
use rusqlite::{Connection, OpenFlags};
use serde::Serialize;
use std::{collections::HashMap, path::Path, sync::Mutex};

pub const KINDS: [&str; 4] = ["summary", "vote", "minutes", "transcript"];
const CANDIDATES: usize = 150;
const RRF_K: f32 = 60.0;
/// Meaning matters more than exact words here, so vector ranks count for more.
const VECTOR_WEIGHT: f32 = 1.0;
const KEYWORD_WEIGHT: f32 = 0.6;

pub struct Row {
    pub kind: String,
    pub meeting: String,
    pub title: String,
    pub text: String,
    pub url: String,
    pub label: String,
}

pub struct Store {
    rows: Vec<Row>,
    ids: Vec<i64>,
    vecs: Vec<f32>,
    pub dims: usize,
    conn: Mutex<Connection>,
}

#[derive(Debug, Clone)]
pub struct Params {
    pub q: String,
    pub kinds: Vec<String>,
    pub from: String,
    pub to: String,
    pub limit: usize,
}

impl Params {
    pub fn new(q: &str) -> Self {
        Self { q: q.to_string(), kinds: KINDS.iter().map(|s| s.to_string()).collect(), from: String::new(), to: String::new(), limit: 20 }
    }
}

#[derive(Serialize, Debug)]
pub struct Hit {
    pub kind: String,
    pub meeting: String,
    pub title: String,
    pub snippet: String,
    pub url: String,
    pub label: String,
    pub score: f32,
    pub similarity: f32,
}

#[derive(Serialize)]
pub struct Found {
    pub results: Vec<Hit>,
    pub searched: usize,
}

impl Store {
    pub fn open(db: &Path) -> Result<Self> {
        let conn = Connection::open_with_flags(db, OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX)?;
        let (mut rows, mut ids, mut vecs, mut dims) = (vec![], vec![], vec![], 0);
        {
            let mut st = conn.prepare("SELECT id, kind, meeting, title, text, url, label, vec FROM chunks ORDER BY id")?;
            let mut q = st.query([])?;
            while let Some(r) = q.next()? {
                let v = from_blob(&r.get::<_, Vec<u8>>(7)?);
                dims = v.len();
                vecs.extend(v);
                ids.push(r.get(0)?);
                rows.push(Row { kind: r.get(1)?, meeting: r.get(2)?, title: r.get(3)?, text: r.get(4)?, url: r.get(5)?, label: r.get(6)? });
            }
        }
        Ok(Self { rows, ids, vecs, dims, conn: Mutex::new(conn) })
    }

    pub fn len(&self) -> usize {
        self.rows.len()
    }

    fn allowed(&self, i: usize, p: &Params) -> bool {
        let r = &self.rows[i];
        p.kinds.iter().any(|k| k == &r.kind)
            && (p.from.is_empty() || r.meeting.as_str() >= p.from.as_str())
            && (p.to.is_empty() || r.meeting.as_str() <= p.to.as_str())
    }

    fn similarities(&self, q: &[f32]) -> Vec<f32> {
        self.vecs.chunks_exact(self.dims).map(|v| v.iter().zip(q).map(|(a, b)| a * b).sum()).collect()
    }

    fn keyword_ranks(&self, q: &str) -> Vec<usize> {
        let terms: Vec<String> = q
            .split(|c: char| !c.is_alphanumeric())
            .filter(|t| t.len() > 1)
            .map(|t| format!("\"{}\"", t.to_lowercase()))
            .collect();
        if terms.is_empty() {
            return vec![];
        }
        let index: HashMap<i64, usize> = self.ids.iter().enumerate().map(|(i, id)| (*id, i)).collect();
        let conn = self.conn.lock().unwrap();
        let Ok(mut st) = conn.prepare("SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ?1 ORDER BY bm25(chunks_fts, 2.0, 1.0) LIMIT ?2") else {
            return vec![];
        };
        let found = st.query_map(rusqlite::params![terms.join(" OR "), (CANDIDATES * 4) as i64], |r| r.get::<_, i64>(0));
        found.map(|it| it.filter_map(|x| x.ok()).filter_map(|id| index.get(&id).copied()).collect()).unwrap_or_default()
    }

    pub fn search(&self, p: &Params, qvec: &[f32]) -> Result<Found> {
        let sims = self.similarities(qvec);
        let mut by_vector: Vec<usize> = (0..self.rows.len()).filter(|&i| self.allowed(i, p)).collect();
        let searched = by_vector.len();
        by_vector.sort_by(|&a, &b| sims[b].total_cmp(&sims[a]));
        by_vector.truncate(CANDIDATES);
        let by_keyword: Vec<usize> = self.keyword_ranks(&p.q).into_iter().filter(|&i| self.allowed(i, p)).take(CANDIDATES).collect();
        let mut fused: HashMap<usize, f32> = HashMap::new();
        for (rank, &i) in by_vector.iter().enumerate() {
            *fused.entry(i).or_default() += VECTOR_WEIGHT / (RRF_K + rank as f32 + 1.0);
        }
        for (rank, &i) in by_keyword.iter().enumerate() {
            *fused.entry(i).or_default() += KEYWORD_WEIGHT / (RRF_K + rank as f32 + 1.0);
        }
        let mut order: Vec<(usize, f32)> = fused.into_iter().collect();
        order.sort_by(|a, b| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0)));
        let results = order
            .into_iter()
            .take(p.limit)
            .map(|(i, score)| {
                let r = &self.rows[i];
                Hit { kind: r.kind.clone(), meeting: r.meeting.clone(), title: r.title.clone(), snippet: snippet(&r.text, &p.q),
                      url: r.url.clone(), label: r.label.clone(), score, similarity: sims[i] }
            })
            .collect();
        Ok(Found { results, searched })
    }
}

/// About 300 characters around the first query word that appears, or the start of the text.
pub fn snippet(text: &str, q: &str) -> String {
    const WIDTH: usize = 300;
    let lower = text.to_lowercase();
    let hit = q
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| t.len() > 2)
        .filter_map(|t| lower.find(&t.to_lowercase()))
        .min();
    let chars: Vec<char> = text.chars().collect();
    if chars.len() <= WIDTH {
        return text.to_string();
    }
    let at = hit.map(|b| text[..b.min(text.len())].chars().count()).unwrap_or(0);
    let start = at.saturating_sub(WIDTH / 3).min(chars.len() - WIDTH);
    let mut s: String = chars[start..start + WIDTH].iter().collect();
    // Don't start or end mid-word.
    if start > 0 {
        s = format!("…{}", s.split_once(' ').map(|x| x.1).unwrap_or(&s));
    }
    if start + WIDTH < chars.len() {
        s = format!("{}…", s.rsplit_once(' ').map(|x| x.0).unwrap_or(&s));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::index::{to_blob, SCHEMA};

    fn store(rows: &[(&str, &str, &str, [f32; 3])]) -> (tempdir::Dir, Store) {
        let dir = tempdir::Dir::new();
        let db = dir.path.join("t.sqlite");
        let conn = Connection::open(&db).unwrap();
        conn.execute_batch(SCHEMA).unwrap();
        for (kind, meeting, text, v) in rows {
            conn.execute("INSERT INTO chunks (kind, meeting, title, text, url, label, hash, vec) VALUES (?,?,?,?,?,?,?,?)",
                         rusqlite::params![kind, meeting, "t", text, "u", "", "h", to_blob(&crate::embed::normalize(v.to_vec()))]).unwrap();
        }
        conn.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')", []).unwrap();
        drop(conn);
        let s = Store::open(&db).unwrap();
        (dir, s)
    }

    mod tempdir {
        pub struct Dir { pub path: std::path::PathBuf }
        impl Dir {
            pub fn new() -> Self {
                let path = std::env::temp_dir().join(format!("cc-search-{}-{:?}", std::process::id(), std::thread::current().id()));
                let _ = std::fs::remove_dir_all(&path);
                std::fs::create_dir_all(&path).unwrap();
                Self { path }
            }
        }
        impl Drop for Dir {
            fn drop(&mut self) { let _ = std::fs::remove_dir_all(&self.path); }
        }
    }

    #[test]
    fn nearest_vector_wins_and_filters_apply() {
        let (_d, s) = store(&[
            ("vote", "2024-01-01", "encampment response", [1.0, 0.0, 0.0]),
            ("transcript", "2025-01-01", "parking rates", [0.0, 1.0, 0.0]),
            ("summary", "2026-01-01", "shelter funding", [0.9, 0.1, 0.0]),
        ]);
        let q = crate::embed::normalize(vec![1.0, 0.05, 0.0]);
        let mut p = Params::new("housing");
        let r = s.search(&p, &q).unwrap();
        assert_eq!(r.results[0].snippet, "encampment response");
        p.kinds = vec!["summary".into(), "transcript".into()];
        assert_eq!(s.search(&p, &q).unwrap().results[0].kind, "summary");
        p.kinds = KINDS.iter().map(|k| k.to_string()).collect();
        p.from = "2025-01-01".into();
        let r = s.search(&p, &q).unwrap();
        assert!(r.results.iter().all(|h| h.meeting.as_str() >= "2025-01-01"));
        assert_eq!(r.searched, 2);
    }

    #[test]
    fn keywords_lift_exact_matches() {
        let (_d, s) = store(&[
            ("vote", "2024-01-01", "general budget discussion", [1.0, 0.0, 0.0]),
            ("vote", "2024-01-01", "Wyndham Street redesign", [0.7, 0.7, 0.0]),
        ]);
        let q = crate::embed::normalize(vec![1.0, 0.2, 0.0]);
        let r = s.search(&Params::new("Wyndham"), &q).unwrap();
        assert_eq!(r.results[0].snippet, "Wyndham Street redesign");
    }

    #[test]
    fn odd_queries_are_safe() {
        let (_d, s) = store(&[("vote", "2024-01-01", "text", [1.0, 0.0, 0.0])]);
        let q = crate::embed::normalize(vec![1.0, 0.0, 0.0]);
        for text in ["\"", "AND OR NOT", "a*b:c^", "", "'; DROP TABLE chunks; --", "üñíçødé"] {
            assert!(s.search(&Params::new(text), &q).is_ok(), "{text}");
        }
    }

    #[test]
    fn snippet_centres_on_the_match() {
        let text = format!("{} the encampment protocol was approved {}", "word ".repeat(100), "more ".repeat(100));
        let s = snippet(&text, "encampment");
        assert!(s.contains("encampment"));
        assert!(s.starts_with('…') && s.ends_with('…'));
        assert!(s.chars().count() <= 302);
        assert_eq!(snippet("short", "x"), "short");
    }
}
