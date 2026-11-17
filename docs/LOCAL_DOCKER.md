# SITA local Docker deployment

This deployment runs the existing SITA application as one container. It does not split specialists into services and does not include OmniRoute or model weights.

## Requirements

- Docker Engine with the Compose plugin (Docker Desktop on Windows is supported).
- An OmniRoute gateway already running on the host if you want model inference.
- A provider/API key configured in OmniRoute, if required by that gateway.

## Configure

Copy `.env.example` to `.env` and set `TARA_OMNIROUTE_API_KEY` if your gateway requires it. The default gateway URL is `http://host.docker.internal:20128/v1`.

Docker Desktop provides `host.docker.internal` so the SITA container can reach a host service. On Linux, Compose maps that name to the host gateway. The OmniRoute process must listen on an interface reachable from Docker; if it only listens on host loopback, container-to-host connectivity may be refused. Do not expose OmniRoute publicly to solve this. Configure a host firewall rule scoped to the Docker bridge or use a supported private host-gateway binding.

SITA validates the gateway URL and only permits loopback or Docker's host-gateway hostname. It does not permit arbitrary remote gateway URLs through this setting.

## Start

From the repository root:

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 sita
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

The published port is bound to host loopback only. The container listens on its private interface, but the HTTP Host/Origin checks accept only the explicit localhost entries configured in Compose. Do not add public hostnames to `SITA_ALLOWED_HOSTS` or publish the port on all host interfaces.

## Verify

```sh
curl --fail http://127.0.0.1:8765/api/health
docker compose ps
```

The Compose health check performs an HTTP request against the existing health endpoint. A healthy HTTP response means the app process is responding; it does not prove OmniRoute credentials, model availability, or every specialist integration is ready.

## Stop and preserve data

```sh
docker compose down
```

The named `sita-data` volume persists the configured local memory stores. To remove the container but preserve data, do not pass `-v`. Destructive removal:

```sh
docker compose down -v
```

This deletes the named SITA data volume. Back up data before destructive operations.

## Security profile

- Non-root UID/GID 10001.
- Read-only container root filesystem; writable application data is under `/data`.
- `/tmp` is a bounded, no-exec tmpfs.
- All Linux capabilities are dropped; no-new-privileges is enabled.
- No privileged mode, host networking, Docker socket mount, ingress, or public port binding.
- Prompts and supported attachments can still be sent through OmniRoute to providers configured there. Review provider/data handling before using confidential content.
- Code execution and model-generated host shell execution remain unavailable.

## Current build reproducibility limitation

The frontend currently has no committed npm lockfile. The image build runs `npm install` from the version ranges in `frontend/package.json`; therefore transitive frontend dependency resolution is not yet fully reproducible. The next hardening change must generate and commit `frontend/package-lock.json` and switch the Docker build to `npm ci`. The repository currently ignores that lockfile, so this must be corrected as part of that change.

## Troubleshooting

- **Cannot reach OmniRoute:** confirm the gateway is listening on a Docker-reachable host interface and that the host firewall permits the Docker bridge. Do not change SITA to accept arbitrary gateway hosts.
- **Host rejected:** use `http://localhost:8765` or `http://127.0.0.1:8765`; the Host header must match `SITA_ALLOWED_HOSTS`.
- **Permission denied writing memory:** inspect volume ownership and verify the container runs as UID 10001.
- **UI missing:** inspect build logs. The Python application retains its static UI fallback if compiled React assets are unavailable.
