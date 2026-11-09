//! Turns chunks.jsonl (written by the Python pipeline) into a SQLite search database.
//! Chunks whose text hasn't changed reuse their old vector, so re-indexing after a new meeting is quick.

use crate::embed::{Embedder, MODEL_ID, MODEL_REVISION};
use anyhow::{Context, Result};
use candle_core::DType;
use rusqlite::{params, Connection};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{collections::HashMap, fs, io::BufRead, path::Path, time::Instant};

#[derive(Deserialize)]
pub struct Chunk {
    pub kind: String,
    /// The council's slug, e.g. "guelph". Older chunk files have none; they were all Guelph's.
    #[serde(default = "default_city")]
    pub city: String,
    pub meeting: String,
    /// The meeting's date (YYYY-MM-DD); the meeting key starts with it.
    #[serde(default)]
    pub date: String,
    pub title: String,
    pub text: String,
    pub url: String,
    #[serde(default)]
    pub label: String,
    /// What gets embedded: the text with its context (meeting, item), which `text` alone may lack.
    pub embed: String,
}

fn default_city() -> String {
    "guelph".into()
}

pub const SCHEMA: &str = "
CREATE TABLE chunks (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, city TEXT NOT NULL, meeting TEXT NOT NULL, date TEXT NOT NULL,
                     title TEXT NOT NULL, text TEXT NOT NULL, url TEXT NOT NULL, label TEXT NOT NULL, hash TEXT NOT NULL, vec BLOB NOT NULL);
CREATE INDEX chunks_city_date ON chunks (city, date);
CREATE VIRTUAL TABLE chunks_fts USING fts5(title, text, content='chunks', content_rowid='id', tokenize='porter unicode61');
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
";

pub fn to_blob(v: &[f32]) -> Vec<u8> {
    v.iter().flat_map(|x| x.to_le_bytes()).collect()
}

pub fn from_blob(b: &[u8]) -> Vec<f32> {
    b.chunks_exact(4).map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]])).collect()
}

fn hash(text: &str) -> String {
    let mut h = Sha256::new();
    h.update(MODEL_ID.as_bytes());
    h.update(MODEL_REVISION.as_bytes());
    h.update(text.as_bytes());
    h.finalize()[..16].iter().map(|b| format!("{b:02x}")).collect()
}

fn previous(db: &Path) -> HashMap<String, Vec<u8>> {
    let Ok(conn) = Connection::open(db) else { return HashMap::new() };
    let Ok(mut st) = conn.prepare("SELECT hash, vec FROM chunks") else { return HashMap::new() };
    let rows = st.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, Vec<u8>>(1)?)));
    rows.map(|it| it.filter_map(|x| x.ok()).collect()).unwrap_or_default()
}

pub fn build(chunks_path: &Path, db: &Path, model_dir: &Path, dtype: DType) -> Result<()> {
    let chunks: Vec<Chunk> = fs::read(chunks_path)
        .with_context(|| format!("reading {}", chunks_path.display()))?
        .lines()
        .map(|l| serde_json::from_str(&l?).map_err(anyhow::Error::from))
        .collect::<Result<_>>()?;
    let mut cached = previous(db);
    let hashes: Vec<String> = chunks.iter().map(|c| hash(&c.embed)).collect();
    let todo: Vec<usize> = (0..chunks.len()).filter(|&i| !cached.contains_key(&hashes[i])).collect();
    eprintln!("{} chunks, {} already embedded, {} to embed", chunks.len(), chunks.len() - todo.len(), todo.len());
    if !todo.is_empty() {
        let model = Embedder::load(model_dir, dtype)?;
        let t0 = Instant::now();
        // Similar lengths in a batch waste less padding.
        let mut order = todo.clone();
        order.sort_by_key(|&i| chunks[i].embed.len());
        for (n, batch) in order.chunks(16).enumerate() {
            let texts: Vec<String> = batch.iter().map(|&i| chunks[i].embed.clone()).collect();
            for (&i, v) in batch.iter().zip(model.embed(&texts)?) {
                cached.insert(hashes[i].clone(), crate::index::to_blob(&v));
            }
            let done = ((n + 1) * 16).min(order.len());
            if n % 10 == 0 || done == order.len() {
                let rate = done as f64 / t0.elapsed().as_secs_f64();
                eprintln!("  embedded {done}/{} ({rate:.1}/s, about {:.0}s left)", order.len(), (order.len() - done) as f64 / rate);
            }
        }
    }
    let tmp = db.with_extension("sqlite.tmp");
    let _ = fs::remove_file(&tmp);
    let mut conn = Connection::open(&tmp)?;
    conn.execute_batch(SCHEMA)?;
    let tx = conn.transaction()?;
    {
        let mut ins = tx.prepare("INSERT INTO chunks (kind, city, meeting, date, title, text, url, label, hash, vec) VALUES (?,?,?,?,?,?,?,?,?,?)")?;
        for (c, h) in chunks.iter().zip(&hashes) {
            let date = if c.date.is_empty() { c.meeting.chars().take(10).collect() } else { c.date.clone() };
            ins.execute(params![c.kind, c.city, c.meeting, date, c.title, c.text, c.url, c.label, h, cached[h]])?;
        }
        tx.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')", [])?;
        let mut meta = tx.prepare("INSERT INTO meta (key, value) VALUES (?, ?)")?;
        meta.execute(params!["model", format!("{MODEL_ID}@{MODEL_REVISION}")])?;
        meta.execute(params!["chunks", chunks.len().to_string()])?;
    }
    tx.commit()?;
    conn.execute_batch("VACUUM")?;
    drop(conn);
    fs::rename(&tmp, db)?;
    eprintln!("wrote {} ({} chunks)", db.display(), chunks.len());
    Ok(())
}
