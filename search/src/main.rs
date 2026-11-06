//! Semantic search for the Guelph council site.
//!
//!   app                                        serve the API (radify sets PORT, STATIC_DIR, DATA_DIR)
//!   app fetch-model <dir>                      download the pinned embedding model
//!   app index <chunks.jsonl> <db> <model dir>  embed chunks into a SQLite search database
//!   app query <db> <model dir> <text>          try a search from the command line

mod embed;
mod index;
mod search;
mod server;

use anyhow::{bail, Result};
use candle_core::DType;
use std::path::PathBuf;

fn dtype() -> DType {
    match std::env::var("EMBED_DTYPE").as_deref() {
        Ok("f16") => DType::F16,
        Ok("bf16") => DType::BF16,
        _ => DType::F32,
    }
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        None | Some("serve") => server::run(),
        Some("fetch-model") if args.len() == 2 => embed::fetch(&PathBuf::from(&args[1])),
        Some("index") if args.len() == 4 => {
            index::build(&PathBuf::from(&args[1]), &PathBuf::from(&args[2]), &PathBuf::from(&args[3]), dtype())
        }
        Some("query") if args.len() >= 4 => {
            let store = search::Store::open(&PathBuf::from(&args[1]))?;
            let model = embed::Embedder::load(&PathBuf::from(&args[2]), dtype())?;
            let q = args[3..].join(" ");
            let t = std::time::Instant::now();
            let v = model.embed_query(&q)?;
            let found = store.search(&search::Params::new(&q), &v)?;
            for r in &found.results {
                println!("{:.4} {:.3} {:10} {} {} | {}", r.score, r.similarity, r.kind, r.meeting, r.title, r.url);
            }
            eprintln!("{} results in {:?}", found.results.len(), t.elapsed());
            Ok(())
        }
        Some("embed-test") if args.len() >= 3 => {
            // Prints similarities between the first text and the rest, for sanity checks.
            let model = embed::Embedder::load(&PathBuf::from(&args[1]), dtype())?;
            let t = std::time::Instant::now();
            let q = model.embed_query(&args[2])?;
            let docs = model.embed(&args[3..].to_vec())?;
            for (d, v) in args[3..].iter().zip(docs) {
                println!("{:.4}  {d}", q.iter().zip(&v).map(|(a, b)| a * b).sum::<f32>());
            }
            eprintln!("{:?}", t.elapsed());
            Ok(())
        }
        _ => bail!("usage: app [serve | fetch-model <dir> | index <chunks.jsonl> <db> <model> | query <db> <model> <text>]"),
    }
}
