# Cognee Slack demo

Minimal Slack bot: `/cognee-remember <fact>` stores it in Cognee memory,
`/cognee-ask <question>` recalls it. One shared memory dataset for the whole
workspace — no per-user account linking, no OAuth, no bot token needed since
replies go back directly in the slash-command response.

On top of that, `/seal-match` identifies a product seal from a photo and
`/seal-confirm` writes the confirmed match back into Cognee, so every human
correction becomes memory the next lookup can use.

Built at the [Cognee × Qdrant HackNight](https://luma.com/cognee-m078?tk=WOJVWw).
Event materials and project submissions live in
[qdrant-labs/Cognee_Qdrant_slack_bot](https://github.com/qdrant-labs/Cognee_Qdrant_slack_bot).

## Stack

| Layer | What we use |
|---|---|
| Slack surface | Slash commands only — HMAC signature verification, instant ack + async reply via `response_url` |
| Web | FastAPI + uvicorn on `:8000`, exposed through ngrok |
| LLM | **Google Vertex AI** (`gemini-3.1-flash-lite`) through LiteLLM, authenticated with Google ADC — no API key. Anthropic Claude is a drop-in alternate backend |
| Memory / knowledge graph | **Cognee** (`dev` branch, 1.5.0.dev1) — `remember` / `recall` over a shared dataset |
| Text embeddings | fastembed `BAAI/bge-small-en-v1.5` (384-dim), local, no key |
| Image embeddings | **[Hyper3-CLIP v0.5](https://huggingface.co/hyper3labs/hyper3-clip-v0.5)** via `hyper-models[ml]` |
| Vector DB | **Qdrant** (`qdrant-client` 1.19.0) — `seal_catalog_v1` and `seal_cases_v1` collections |

`llm_provider.py` translates one friendly `LLM_BACKEND` setting (`vertex` or
`anthropic`) into the `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` variables
Cognee expects, and must run *before* `cognee` is imported — Cognee caches its
LLM config at import time.

Qdrant runs embedded on local disk by default; set `SEAL_QDRANT_URL` (plus
`SEAL_QDRANT_API_KEY`) to point at a Qdrant Cloud cluster instead.

### Commands

| Command | What it does |
|---|---|
| `/cognee-remember <fact>` | Store a fact in the `slack` dataset |
| `/cognee-ask <question>` | Recall from the knowledge graph |
| `/seal-match <file/permalink>` | Embed the image with Hyper3-CLIP, search the Qdrant catalog, return ranked SKU candidates |
| `/seal-confirm <case-id> <SKU>` | Record the human-verified match and `cognee.remember` it as a reusable case |

### Hyper3-CLIP access

The model repo is gated. Request access on the
[model page](https://huggingface.co/hyper3labs/hyper3-clip-v0.5), then either run
`hf auth login` or put an `HF_TOKEN` in `.env` — otherwise the first
`/seal-match` fails with `GatedRepoError`. Weights download lazily on first
match, not at server startup.

## Run it

```bash
pip3 install -r requirements.txt
cp .env.example .env   # fill in LLM_API_KEY with your Anthropic key
python3 app.py          # serves on :8000
ngrok http 8000          # get a public https URL
```

Put the ngrok URL into `slack-manifest.yaml` in place of `<public-host>`
(both slash command URLs), then:

1. Go to https://api.slack.com/apps -> Create New App -> From an app manifest
2. Paste the contents of `slack-manifest.yaml`
3. Install the app to your workspace
4. Copy **Signing Secret** (Basic Information) into `.env` as `SLACK_SIGNING_SECRET`, restart `app.py`
5. In Slack: `/cognee-remember Qdrant is Andrei's employer`, then
   `/cognee-ask where does Andrei work`

## Test

```bash
python3 test_app.py
```

Covers signature verification (valid/invalid/expired) and command handling,
with `cognee.remember`/`cognee.recall` mocked — no LLM calls in the test.

## Skipped for this demo

- `/cognee-link` per-user account linking — everyone shares one `slack`
  dataset instead. Add per-user OAuth + encrypted token storage if you need
  private-per-person memory.
- "Remember this" message shortcut, channel allowlist admin endpoints,
  `chat.postMessage`/share-to-channel button — not needed for a single-command demo.
- ngrok free tier gives a new URL on restart; update the manifest URLs (or
  get a reserved domain) if it changes.
