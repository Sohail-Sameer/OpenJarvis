# Deploy on Hugging Face Spaces

Spaces has no blueprint-as-code equivalent to `render.yaml` — the deploy
config instead lives in two places already in this repo: the YAML frontmatter
at the very top of `README.md` (`sdk: docker`, `app_port: 7860`) and
`deploy/docker/Dockerfile` itself, which Spaces builds and runs with **no
command override** (unlike Render, there's nothing to point at a custom
`--engine`/`--model`/`--port`, so the Dockerfile's own default `CMD` is what
actually runs). That default already points at Ollama's hosted Cloud API
(`gpt-oss:120b`) via `configs/openjarvis/config.toml`, and listens on port
`7860` to match Spaces' convention.

## Create the Space

1. On huggingface.co, create a **new Space** → SDK: **Docker** → template:
   **Blank**. Note the Space's git URL, e.g.
   `https://huggingface.co/spaces/<you>/<space-name>`.
2. Push this repository's contents to that Space repo. Two ways to do it:
   - **One-time push:** add the Space as a second git remote and push:
     ```bash
     git remote add space https://huggingface.co/spaces/<you>/<space-name>
     git push space main
     ```
   - **Keep it in sync with GitHub automatically:** use the included
     `.github/workflows/sync-to-hf-space.yml` — set two repo secrets on your
     GitHub repo (`HF_TOKEN`, a Hugging Face access token with write access
     to the Space; and `HF_SPACE_REPO`, e.g. `<you>/<space-name>`), and every
     push to `main` mirrors automatically. This avoids the exact
     copy-some-files-by-hand problem that caused the missing `tests/` folder
     earlier in this project's history — one push updates everything.
3. In the Space's **Settings → Variables and secrets**, add:
   - `OLLAMA_API_KEY` (secret) — from https://ollama.com/settings/keys
   - `GROQ_API_KEY` (secret, optional) — from https://console.groq.com/keys,
     powers voice input; chat works without it and the mic button just stays
     disabled
   - `OPENJARVIS_API_KEY` (secret) — Spaces has no equivalent to Render's
     `generateValue: true`, so generate one yourself, e.g.
     `openssl rand -hex 32`, and use it as the `Authorization: Bearer <key>`
     value on API requests
   - `OLLAMA_HOST` (variable, not secret) — `https://ollama.com`
4. The Space rebuilds automatically on push. Once the build finishes, the
   app is live at `https://<you>-<space-name>.hf.space`.

## Storage and free-tier limits

!!! warning "Free Spaces do not preserve OpenJarvis data"
    Same caveat as Render: the free CPU Basic tier's filesystem is
    ephemeral. Everything under `/home/openjarvis/.openjarvis` — config,
    connector tokens, local databases, learned state — is lost on every
    restart or rebuild. Free Spaces also sleep after a period of
    inactivity and take a noticeable moment to wake on the next request.

For durable state, Spaces offers a paid **persistent storage** add-on
(Settings → persistent storage) — mount it at `/home/openjarvis/.openjarvis`
for the same reason a Render persistent disk would need to go there.

## Why Hugging Face over Render here

The free CPU Basic tier gives substantially more RAM (16GB) than Render's
free tier (512MB) for the same $0 — worth trying if a Render deploy is
failing silently (`Exited with status 128`) with no logs to go on; see
`docs/deployment/render.md`'s troubleshooting notes for that specific
symptom.
