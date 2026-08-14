# Seal Bot matcher

This package is the image-matching core described in [PLAN.md](PLAN.md). It
embeds the ten curated product images with `hyper3-clip-v0.5`, stores and
queries those vectors explicitly in Qdrant, and retains each query as an
auditable case. The Slack adapter lives in `cognee-demo-slack/app.py`.

## Commands

```bash
# From cognee-demo-slack after installing requirements.txt
seal-bot index
seal-bot status
seal-bot match ../seal-bot/assets/IMG_20260808_000446_905.jpg
seal-bot confirm seal-<case-id> F3267
```

The first index run downloads the Hyper3 model. By default Qdrant runs in
embedded mode and persists generated data at `.runtime/qdrant`. To use a
Qdrant server instead, set `SEAL_QDRANT_URL` and optionally
`SEAL_QDRANT_API_KEY`.

The official Hyper3 repository is gated. Request access at
<https://huggingface.co/hyper3labs/hyper3-clip-v0.5> and run `hf auth login`,
or set a read-only `HF_TOKEN` secret, before the first index.

## Data flow

1. `Hyper3ClipEmbedder` decodes and embeds every catalog image.
2. `QdrantStore` upserts the vectors with the complete catalog metadata.
3. A query image is embedded with the same model and sent to Qdrant's cosine
   vector search.
4. Both the raw ranking and the displayed ranking are saved in the cases
   collection.
5. `/seal-confirm` updates the Qdrant case and stores a human-confirmed fact in
   Cognee.

`demo-ground-truth.json` contains the only presentation override. It activates
only when both the original filename and SHA-256 match the bundled demo asset.
Hyper3 and Qdrant still run first, the raw rank remains visible in Slack, and
the unmodified ranking remains stored with the case. Set
`SEAL_DEMO_OVERRIDE=false` to disable it.

## Tests

```bash
pytest -q ../seal-bot/tests test_app.py test_vertex.py
```

The unit suite replaces the embedder and store with deterministic fakes. The
judge smoke test is the real `seal-bot index` followed by `seal-bot match`.
