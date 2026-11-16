# TARA ↔ n8n integration

Status: **read-only API adapter foundation**. The adapter is not yet wired into the application facade, HTTP UI, or workflow tool loop.

## Connection setup

TARA uses the n8n public REST API. Configure these environment variables before launching TARA:

- `TARA_N8N_BASE_URL`: n8n instance URL, for example `http://127.0.0.1:5678` for a local instance or `https://your-instance.example` for HTTPS hosting.
- `TARA_N8N_API_KEY`: API key created in n8n under **Settings → n8n API**.
- `TARA_N8N_TIMEOUT_SECONDS`: optional request timeout from 1 to 30 seconds (default 8).

The adapter adds `/api/v1` when it is absent. It sends the key in the `X-N8N-API-KEY` header. Never put API keys in TOML, workflow exports, source code, logs, or frontend configuration.

Plain HTTP is accepted only for loopback addresses. Use HTTPS for remote instances. Redirects are rejected to prevent forwarding the API key to a different host.

## Implemented read-only operations

- Connection check: a one-item workflow-list request.
- Workflow listing: one bounded page (1–100 items), with optional cursor.
- Execution listing: one bounded page (1–100 items), optionally filtered by workflow ID.

Only selected metadata fields are returned. Workflow node definitions, execution payloads, credentials, and secret-bearing fields are intentionally omitted. Responses are capped at 1 MiB and each request has a timeout.

## Not implemented / disabled

- Create, update, delete, activate, deactivate, execute, retry, or stop workflows.
- Importing workflow JSON into the n8n instance.
- Automatic scheduling or background polling.
- UI integration, approval flow, and durable audit events for n8n operations.

These operations must not be added until each has a separate policy decision, explicit user approval, and audit coverage. A read-only API key is preferred. On n8n Enterprise, scope keys to only `workflow:list`, `workflow:read`, and `execution:list` where available.

## Current API references

- [n8n API authentication](https://docs.n8n.io/api/authentication/)
- [n8n public API reference](https://docs.n8n.io/api/)

The public API requires an API key in `X-N8N-API-KEY`. API availability depends on the n8n edition/trial status; verify the API menu exists on the target instance before configuring TARA.
