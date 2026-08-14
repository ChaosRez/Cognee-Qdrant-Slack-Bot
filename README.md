# Seal Bot — Cognee × Qdrant hackathon

Seal Bot takes a window-seal photo in Slack and recommends the closest product
from a curated Graf-Dichtungen catalog. Hyper3-CLIP supplies image embeddings,
Qdrant performs the explicit vector search, and Cognee remembers product facts
and human-confirmed matches. The existing `/cognee-ask` and
`/cognee-remember` commands remain available.

## Reproduce the demo

Prerequisites: Python 3.10+, `gcloud`, Terraform, and ngrok.

### 1. Configure Vertex AI

```bash
cd infra/vertex
cp terraform.tfvars.example terraform.tfvars
# Set project_id and principal_email in terraform.tfvars.
terraform init
terraform apply

gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
cd ../../cognee-demo-slack
```

Terraform enables Vertex AI and grants the configured principal the Vertex AI
User role. No model endpoint is deployed; Cognee calls the managed
`gemini-3.1-flash-lite` publisher model with Application Default Credentials.

### 2. Install and configure

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Hyper3-CLIP is a gated model. Sign in at
<https://huggingface.co/hyper3labs/hyper3-clip-v0.5>, request access, and then
authenticate this machine before indexing:

```bash
hf auth login
```

For CI, set a read-only `HF_TOKEN` secret instead; never commit it.

Set these values in `cognee-demo-slack/.env`:

```dotenv
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=xoxb-...
LLM_BACKEND=vertex
VERTEXAI_PROJECT=YOUR_PROJECT_ID
VERTEXAI_LOCATION=global
```

`SLACK_BOT_TOKEN` is needed only for real Slack uploads; `/seal-match demo`
uses the checked-in asset. Anthropic remains available by switching
`LLM_BACKEND=anthropic` and setting `ANTHROPIC_API_KEY`.

### 3. Build the real vector index and seed Cognee

```bash
seal-bot index
seal-bot status
python seed_seal_catalog.py
```

The first command downloads `hyper3-clip-v0.5`, embeds all ten checked-in
catalog images, and writes them to embedded Qdrant at
`seal-bot/.runtime/qdrant`. Configure `SEAL_QDRANT_URL` to use a Qdrant server.
The seed command stores the catalog facts in Cognee using the selected LLM.

### 4. Start Slack and ngrok

```bash
python app.py
# In another terminal:
ngrok http 8000
```

Replace the ngrok host in all four command URLs in
[`slack-manifest.yaml`](slack-manifest.yaml), then create or update a Slack app
from that manifest. Install it to the workspace, copy its Signing Secret and
Bot User OAuth Token into `.env`, and restart `app.py`.

The manifest requests only `commands` and `files:read`. Invite the bot to the
channel containing a private upload so Slack allows it to read that file.

### 5. Demo commands

```text
/seal-match demo
/seal-confirm seal-<case-id-from-result> F3267
```

For a new customer image, upload it to a channel containing the bot, copy its
Slack permalink, then run:

```text
/seal-match https://YOUR-WORKSPACE.slack.com/files/.../F.../photo.jpg
```

Slash commands cannot contain a binary attachment, so the file permalink/ID
is the reproducible handoff. The result contains the product image and link,
dimensions, three alternatives, an explicit measurement warning, and the case
ID needed for confirmation.

## Demo integrity

The expected demo asset is
`seal-bot/assets/IMG_20260808_000446_905.jpg` with SHA-256
`ab710508eeb0ca617800588e6642e412bd0335ddc3d63c45f0b89c7f2f8e7dd9`.
For exactly that filename and checksum, F3267 is promoted as the
human-adviser-confirmed answer. Hyper3 and Qdrant still execute, and the raw
rank is displayed and persisted. Disable this behavior with
`SEAL_DEMO_OVERRIDE=false`.

## Verification

```bash
pytest -q ../seal-bot/tests test_app.py test_vertex.py
seal-bot match ../seal-bot/assets/IMG_20260808_000446_905.jpg
```

Health check: `curl http://localhost:8000/healthz`.

## Known limitations

- This is a curated ten-product demo, not the supplier's full catalog.
- Hyper3 model access is gated and the first authenticated download is large.
- Embedded Qdrant is intended for one local bot process; use `SEAL_QDRANT_URL`
  for shared or multi-process deployment.
- Slack slash commands cannot attach a binary, so real uploads are referenced
  by their Slack file permalink or ID.
- The exact demo-file override is presentation logic, not a claim of model
  accuracy; the raw vector ranking is always retained.

## Stack

Cognee, Vertex AI, Gemini Flash Lite, Hyper3-CLIP, Qdrant, FastAPI, Slack,
Terraform, and ngrok.
