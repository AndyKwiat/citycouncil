//! Sentence embeddings with Snowflake's arctic-embed-m-v1.5, run with candle (pure Rust, no Python or ONNX).
//! The laptop (documents) and the server (queries) run this same code, so both sides land in the same vector space.

use anyhow::{bail, Context, Result};
use candle_core::{DType, Device, Tensor};
use candle_nn::VarBuilder;
use candle_transformers::models::bert::{BertModel, Config};
use sha2::{Digest, Sha256};
use std::{fs, io::Read, path::Path};
use tokenizers::{PaddingParams, Tokenizer, TruncationParams};

pub const MODEL_ID: &str = "Snowflake/snowflake-arctic-embed-m-v1.5";
pub const MODEL_REVISION: &str = "e58a8f756156a1293d763f17e3aae643474e9b8a";
const WEIGHTS_SHA256: &str = "463d27a3e88a748997316367c419bbdab4d809300a5f24b9b19ba9b2dc08ffdd";
/// The model was trained to see this before a search query (documents get no prefix).
pub const QUERY_PREFIX: &str = "Represent this sentence for searching relevant passages: ";
pub const MAX_TOKENS: usize = 512;

pub struct Embedder {
    model: BertModel,
    tokenizer: Tokenizer,
    device: Device,
    #[allow(dead_code)]
    pub dims: usize,
}

impl Embedder {
    pub fn load(dir: &Path, dtype: DType) -> Result<Self> {
        let device = Device::Cpu;
        let config: Config = serde_json::from_str(&fs::read_to_string(dir.join("config.json"))?)?;
        let mut tokenizer = Tokenizer::from_file(dir.join("tokenizer.json")).map_err(anyhow::Error::msg)?;
        tokenizer
            .with_truncation(Some(TruncationParams { max_length: MAX_TOKENS, ..Default::default() }))
            .map_err(anyhow::Error::msg)?;
        tokenizer.with_padding(Some(PaddingParams::default()));
        let vb = unsafe { VarBuilder::from_mmaped_safetensors(&[dir.join("model.safetensors")], dtype, &device)? };
        let model = BertModel::load(vb, &config)?;
        Ok(Self { model, tokenizer, device, dims: config.hidden_size })
    }

    /// Unit-length embeddings (CLS pooling, as the model card specifies).
    pub fn embed(&self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(vec![]);
        }
        let enc = self.tokenizer.encode_batch(texts.to_vec(), true).map_err(anyhow::Error::msg)?;
        let ids: Vec<Tensor> = enc.iter().map(|e| Tensor::new(e.get_ids(), &self.device)).collect::<candle_core::Result<_>>()?;
        let mask: Vec<Tensor> = enc.iter().map(|e| Tensor::new(e.get_attention_mask(), &self.device)).collect::<candle_core::Result<_>>()?;
        let ids = Tensor::stack(&ids, 0)?;
        let mask = Tensor::stack(&mask, 0)?;
        let types = ids.zeros_like()?;
        let hidden = self.model.forward(&ids, &types, Some(&mask))?;
        let cls = hidden.narrow(1, 0, 1)?.squeeze(1)?.to_dtype(DType::F32)?;
        let rows: Vec<Vec<f32>> = cls.to_vec2()?;
        Ok(rows.into_iter().map(normalize).collect())
    }

    pub fn embed_query(&self, q: &str) -> Result<Vec<f32>> {
        Ok(self.embed(&[format!("{QUERY_PREFIX}{q}")])?.remove(0))
    }
}

pub fn normalize(mut v: Vec<f32>) -> Vec<f32> {
    let n = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if n > 0.0 {
        v.iter_mut().for_each(|x| *x /= n);
    }
    v
}

/// Download the pinned model files into `dir` if they aren't there, checking the weights' hash.
pub fn fetch(dir: &Path) -> Result<()> {
    fs::create_dir_all(dir)?;
    for name in ["config.json", "tokenizer.json", "model.safetensors"] {
        let path = dir.join(name);
        if path.exists() && (name != "model.safetensors" || sha256_file(&path)? == WEIGHTS_SHA256) {
            continue;
        }
        let url = format!("https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{name}");
        eprintln!("downloading {url}");
        let client = reqwest::blocking::Client::builder().timeout(std::time::Duration::from_secs(900)).build()?;
        let bytes = client.get(&url).send()?.error_for_status()?.bytes()?;
        let tmp = dir.join(format!("{name}.part"));
        fs::write(&tmp, &bytes)?;
        if name == "model.safetensors" && sha256_file(&tmp)? != WEIGHTS_SHA256 {
            fs::remove_file(&tmp).ok();
            bail!("downloaded weights don't match the pinned hash");
        }
        fs::rename(&tmp, &path).with_context(|| format!("saving {name}"))?;
    }
    Ok(())
}

fn sha256_file(path: &Path) -> Result<String> {
    let mut f = fs::File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(h.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
