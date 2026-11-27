# Central Gemini API configuration

SITA uses one project-level Gemini API credential for Chat, Code, Vision, Creative, and Model Hub. The app loads the credential once at startup and injects it into the configured Gemini specialists. Individual module entries do not need API-key environment lists or separate key setup.

## One-time setup (Windows)

1. Copy .env.example to .env.
2. Open .env and replace the placeholder with your Google AI Studio key.
3. Copy sita.example.toml to sita.toml if it does not already exist.
4. Run run-sita.bat normally.

Example .env:

    GEMINI_API_KEY=your-real-key-here
    TARA_GEMINI_MODEL=gemini-3.8-flash

On macOS/Linux, use the same project-root .env file and run ./run-sita.sh.

No API key needs to be pasted into Chat, Code, Vision, Creative, Model Hub, or separate module settings. Existing process environment variables take precedence over .env, which makes CI and deployment overrides possible. The loader uses only Python's standard library; no additional dotenv package is required.

## Central model configuration

Set the default model once with TARA_GEMINI_MODEL in .env, or configure models in sita.toml:

    [gemini]
    model = "gemini-3.8-flash"

    [gemini.models]
    chat = "gemini-3.8-flash"
    code = "gemini-3.8-flash"
    vision = "gemini-3.8-flash"
    creative = "gemini-3.8-flash"
    models = "gemini-3.8-flash"

Per-specialist model overrides are optional; they do not require separate API keys. The runtime centrally passes the same credential and each selected model to its specialist process.

## Privacy and security

- .env and all .env.* files are ignored by Git; .env.example is the only exception and contains placeholders only.
- Never put the real key in sita.toml, source code, frontend configuration, prompts, logs, or commits.
- Each remote specialist still requires allow_remote = true in its [[modules]] entry. Central key configuration does not automatically enable remote data transfer.
- Chat prompts/history/memory excerpts, Code attachments, Creative briefs, and Vision images are sent to Google's service only when that specialist is enabled.
- The key is sent in the x-goog-api-key HTTP header, never in the URL.
- SITA fails closed if the key, model access, quota, or API is unavailable; it does not silently switch providers.

## Troubleshooting

1. Confirm .env is in the same project/config directory from which SITA is launched.
2. Confirm the variable is spelled exactly GEMINI_API_KEY.
3. Check that the Google AI project has Gemini API access and that the selected model is available.
4. A 401/403 generally indicates invalid key or access configuration; 429 indicates quota/rate limiting; a 5xx or timeout may indicate service/provider failure.
5. Check SITA's health panel or Model Hub for authenticated connectivity and model discovery.
