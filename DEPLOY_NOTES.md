# Deploy notes — Ollama Cloud + voice + Render

What changed in this copy of the repo, and how to actually ship it.

## What changed (9 files)

| File | Change |
|---|---|
| `src/openjarvis/engine/ollama.py` | Added Bearer-auth support (`OLLAMA_API_KEY` env var) so the `ollama` engine can talk to Ollama's hosted **Cloud** API (`https://ollama.com`), not just a local `ollama serve`. |
| `src/openjarvis/speech/groq_whisper.py` | **New.** A speech-to-text backend using Groq's hosted Whisper API (`whisper-large-v3-turbo`) for voice input — same provider Weather-Report uses. |
| `src/openjarvis/speech/_discovery.py`, `speech/__init__.py` | Registers the new `groq` backend into the existing auto-discovery chain (`faster-whisper` → `openai` → `groq` → `deepgram`). |
| `configs/openjarvis/config.toml` | Default model/engine switched from a local vLLM/GLM setup to Ollama Cloud's `gpt-oss:120b`. |
| `render.yaml` | Render Blueprint repointed from OpenAI to `--engine ollama --model gpt-oss:120b`; now asks for `OLLAMA_API_KEY` + `GROQ_API_KEY` instead of `OPENAI_API_KEY`. |
| `docs/deployment/render.md` | Updated to match. |
| `frontend/src/lib/store.ts` | `speechEnabled` default flipped to `true`, so the mic button (already built into this app — `MicButton.tsx` / `useSpeech.ts` / `/v1/speech/transcribe`) is live without a trip to Settings. |
| `tests/deploy/test_render_blueprint.py`, `tests/engine/test_ollama.py`, `tests/speech/test_groq_whisper.py` | Updated/added to cover the above. |

**Everything else — the FastAPI server, the React chat UI, the mic button, the
`/v1/speech/transcribe` endpoint, the Dockerfile, the Render blueprint
mechanics — already existed in OpenJarvis.** This wasn't a from-scratch
build; it was pointing existing, working infrastructure at your keys.

## What I verified (not just wrote)

- `PYTHONPATH=src pytest tests/engine/ tests/speech/ tests/deploy/` → **600
  passed** (the only failures are `TestGemmaCppLive`, a pre-existing
  integration test that needs locally downloaded gemma.cpp weights —
  unrelated to anything here).
- `cd frontend && npm ci && npm run build` → builds clean, output lands in
  `src/openjarvis/server/static/` as the Dockerfile expects.
- `cd frontend && npx vitest run` → **68 passed**, no regressions from the
  `speechEnabled` default change.
- `render.yaml` and `configs/openjarvis/config.toml` both parse as valid
  YAML/TOML.

**What I did *not* run:** a full `docker build` (it compiles a Rust
extension from source — realistically 10+ minutes, too slow to run here).
The Dockerfile itself is unmodified, and it's the same one the project's own
CI builds on every push, so risk there is low — but Render's build log is
your first real end-to-end check.

## Deploy steps

1. **Get two API keys:**
   - Ollama: https://ollama.com/settings/keys (you said you already have
     one — reuse it)
   - Groq (for voice input): https://console.groq.com/keys — free tier
     is enough. If you skip this, chat works fine and the mic button just
     stays disabled with a "not configured" tooltip.

2. **Push this to your own GitHub repo.** This folder is still a working
   git clone of `open-jarvis/OpenJarvis` — repoint the remote to your fork
   and push, e.g.:
   ```bash
   git remote set-url origin https://github.com/<you>/<your-repo>.git
   git add -A
   git commit -m "Point at Ollama Cloud (gpt-oss:120b) + Groq voice input"
   git push -u origin main
   ```

3. **On Render:** New → Blueprint → pick your repo. Render will read
   `render.yaml` automatically and ask you for `OLLAMA_API_KEY` and
   `GROQ_API_KEY` — paste them in. Everything else (the generated
   `OPENJARVIS_API_KEY`, the port, the docker command) is already set.

4. **Wait for the build.** First build compiles the Rust extension and the
   frontend — expect several minutes. Watch Render's build log; that's
   where a real problem (e.g. a dependency version drift since I last ran
   the tests) would show up first.

5. Once `/health` is green, open the service URL — that's your voice-
   activated chat website.

## One thing worth knowing

Render's **free plan has an ephemeral filesystem**: conversation memory,
telemetry, and any connector tokens are wiped on every restart/redeploy/
spin-down (the project's own docs say this plainly — see
`docs/deployment/render.md`). Fine for a stateless voice assistant demo;
not fine if you want it to remember things between sessions. Fix is a paid
Render plan with a persistent disk mounted at
`/home/openjarvis/.openjarvis` — not something I turned on by default
since it costs money.
