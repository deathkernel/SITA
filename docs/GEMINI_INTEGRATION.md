# Gemini Developer API integration

SITA uses the Google Gemini Developer API directly for language-model inference. The local SITA router still selects the specialist (Chat, Code, Vision, Creative, or Model Hub); each specialist sends its bounded request to the configured Gemini model. SITA retains conversation context, local memory, permissions, Security policy, and desktop tool execution.

There is no Gemini API dependency in the active inference path and no silent fallback to Ollama or another provider. If the Gemini key, model access, quota, or API is unavailable, the request fails closed.

## Configure on Windows (PowerShell)

Create a Gemini API key in Google AI Studio. In the SITA repository root, create a local `.env` file (the file is ignored by Git):

```dotenv
GEMINI_API_KEY=your_actual_api_key_here
TARA_GEMINI_MODEL=gemini-3.8-flash
```

SITA loads `.env` automatically from the same directory as the selected `sita.toml`. Existing process environment variables take precedence over `.env`. Keep the real key out of `sita.toml`, source files, frontend configuration, prompts, logs, and Git. The launcher passes the key only to explicitly enabled remote model specialists.

Copy `sita.example.toml` to `sita.toml`. Each remote specialist must explicitly set `allow_remote = true`; this remains a deliberate privacy opt-in. Set it only for the specialists whose prompts, source attachments, or images you approve sending to Google.

## Model selection

The example config uses `gemini-3.8-flash` for Chat, Code, Vision, Creative, and Model Hub. Select a different model by editing `[gemini.models]` or setting a specialist-specific environment variable:

| Specialist | Environment variable |
|---|---|
| Chat | `TARA_GEMINI_MODEL` |
| Code | `TARA_CODE_MODEL` |
| Vision | `TARA_VISION_MODEL` |
| Creative | `TARA_CREATIVE_MODEL` |
| Model Hub | `TARA_MODELS_MODEL` |

Model names must be Gemini model IDs (for example `gemini-3.8-flash`), not Gemini API aliases. The Model Hub lists Gemini models exposed to the configured key that support `generateContent`.

## API and security

- Model discovery: `GET https://generativelanguage.googleapis.com/v1beta/models`.
- Text and multimodal inference: `POST /v1beta/models/{model}:generateContent`.
- Authentication: `x-goog-api-key: <key>` header. The key is never sent in the URL or query string.
- Vision images use Gemini `inlineData` parts; the image data is sent to Google's API when Vision is enabled.
- Requests are non-streaming where the specialist expects a complete response. Redirects are rejected and response sizes/timeouts are bounded.
- The model output remains untrusted data. It cannot execute host commands, change files, or bypass SITA's local capability registry, security checks, or approval flow.
- Review Google's current API terms, data handling, quotas, region availability, and billing before sending sensitive content. Do not send passwords, API keys, or confidential workspace material unless you have explicitly accepted that transfer.

## Troubleshooting

1. Confirm `GEMINI_API_KEY` is set in the same shell that launches SITA.
2. Check that the key's Google AI project has Gemini API access and that the selected model is available.
3. A 401/403 generally indicates invalid key or access configuration; 429 indicates quota/rate limiting; a 5xx or timeout may indicate service/provider failure.
4. Confirm the specialist is enabled in `sita.toml` with `allow_remote = true`.
5. Check `/api/health` and `/api/models`; Model Hub availability depends on an authenticated model-list request.

SITA currently uses the Gemini `generateContent` REST method for specialist requests. Keep the provider transport isolated so it can be moved to Google's newer Interactions API in a later migration without changing specialist permissions or data boundaries.
