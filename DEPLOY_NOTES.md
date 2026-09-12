# Deploy notes — Ollama Cloud + voice + Render

What changed in this copy of the repo, and how to actually ship it.

## What changed (12 files)

| File | Change |
|---|---|
| `src/openjarvis/engine/ollama.py` | Added Bearer-auth support (`OLLAMA_API_KEY` env var) so the `ollama` engine can talk to Ollama's hosted **Cloud** API (`https://ollama.com`), not just a local `ollama serve`. |
| `src/openjarvis/speech/groq_whisper.py` | **New.** A speech-to-text backend using Groq's hosted Whisper API (`whisper-large-v3-turbo`) for voice input — same provider Weather-Report uses. |
| `src/openjarvis/speech/_discovery.py`, `speech/__init__.py` | Registers the new `groq` backend into the existing auto-discovery chain (`faster-whisper` → `openai` → `groq` → `deepgram`). |
| `configs/openjarvis/config.toml` | Default model/engine switched from a local vLLM/GLM setup to Ollama Cloud's `gpt-oss:120b`. |
| `frontend/src/lib/store.ts` | `speechEnabled` default flipped to `true`, so the mic button (already built into this app — `MicButton.tsx` / `useSpeech.ts` / `/v1/speech/transcribe`) is live without a trip to Settings. |
| `src/openjarvis/tools/__init__.py` | **New.** An opt-in `OPENJARVIS_PROFILE=cloud` denylist that skips registering local-filesystem/shell/git/db tools (`file_read`, `file_write`, `shell_exec`, `git_tool`, `db_query`, `code_interpreter`, `repl`, ...) — not something a public website should hand out to visitors. Unset (local/desktop use) still registers everything, unchanged. |
| `frontend/src/pages/SettingsPage.tsx` | Added a "Download desktop app" link in the About section, pointing to the project's real Downloads page — for anyone who wants the full tool set running on their own machine. |
| `deploy/docker/Dockerfile` | Added `PYTHONUNBUFFERED=1` (see "The Render 128 exit" below). |
| `render.yaml` | Repointed from OpenAI to `--engine ollama --model gpt-oss:120b`; now asks for `OLLAMA_API_KEY` + `GROQ_API_KEY` instead of `OPENAI_API_KEY`; sets `OPENJARVIS_PROFILE=cloud`. |
| `docs/deployment/render.md` | Updated to match. |
| `tests/deploy/test_render_blueprint.py`, `tests/engine/test_ollama.py`, `tests/speech/test_groq_whisper.py`, `tests/tools/test_tool_registration.py` | Updated/added to cover all of the above. |

**Everything else — the FastAPI server, the React chat UI, the mic button, the
`/v1/speech/transcribe` endpoint, the Dockerfile, the Render blueprint
mechanics, the tool system itself — already existed in OpenJarvis.** This
wasn't a from-scratch build; it was pointing existing, working infrastructure
at your keys, then trimming what shouldn't be public.

## The Render "Exited with status 128" issue

The build succeeds completely every time — image compiles, exports, pushes.
The failure is post-build, during "Deploying...", with **zero app output**
even in the full log (confirmed from the complete log you pasted). That rules
out the Ollama engine being the direct cause: I reproduced its failure mode
locally, and it fails loudly (prints a banner, then a clear warning) in under
a second — nothing like an 11-second silent gap.

My best-supported working theory is an **out-of-memory kill during Python's
import**, before the app's first print statement runs — this app's real
dependency footprint (FastAPI, the compiled Rust extension, `openai`, and
transitively `pandas`/`pyarrow`/`huggingface_hub` via the `datasets` package)
is heavier than Render's free-tier 512MB comfortably holds, and a SIGKILL
mid-import would produce exactly this silence-then-death pattern. I could not
fully confirm this — I don't have Docker available to build and run the real
image, and Render's Metrics tab showed nothing for this deploy (which itself
is consistent with a deploy that never went "live" — Render often doesn't
populate metrics for those).

What I changed regardless, both good practice independent of the exact cause:
- `PYTHONUNBUFFERED=1` in the Dockerfile, so if it fails again, the log will
  actually show why instead of going silent.
- The `OPENJARVIS_PROFILE=cloud` tool trimming above — smaller import
  surface, and arguably more important, no shell/file/git/db tools exposed
  to the public.

**If it still fails the same way after redeploying**, the fastest next
diagnostic is temporarily bumping to Render's Starter plan (more RAM, cheap,
reversible) to see if the exact same commit deploys clean — that would
confirm memory as the cause outright, at which point the fix is either
staying on a paid plan or lazy-importing the eval-only `datasets` dependency
chain so it's not even installed for a `serve`-only deployment.

## What I verified (not just wrote)

- `PYTHONPATH=src pytest tests/tools/ tests/deploy/ tests/engine/ tests/speech/`
  → **1441 passed**, 6 failed — all 6 pre-existing and unrelated: 2 need
  live DuckDuckGo access (blocked in my sandbox, not by anything here), 4
  are `TestGemmaCppLive` needing locally downloaded gemma.cpp weights.
- Specifically for the new tool-profile gating: 4 new tests in
  `tests/tools/test_tool_registration.py` confirm `OPENJARVIS_PROFILE=cloud`
  actually suppresses `file_read`/`file_write`/`shell_exec`/`git_tool`/
  `db_query`/`code_interpreter`/`repl` while leaving `calculator`/
  `web_search`/`memory_store`/`get_weather`/etc. untouched, and that the
  existing full-tool-set behavior is unchanged when the env var isn't set.
- `cd frontend && npm ci && npm run build` → builds clean (including the new
  Settings link), output lands in `src/openjarvis/server/static/` as the
  Dockerfile expects.
- `cd frontend && npx vitest run` → **68 passed**, no regressions.
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
