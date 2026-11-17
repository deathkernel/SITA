# SITA Local DevOps & Self-Hosted Platform Plan

**Status:** Phase 0 audit complete; implementation branch opened  
**Target:** Local development first, self-hosted Kubernetes later  
**Repository:** `deathkernel/SITA`  
**Branch:** `devops/local-platform-foundation`

## 1. Goals and non-goals

Build a reproducible local deployment and a path to a self-hosted Kubernetes environment without changing SITA's product architecture.

Goals:
- Package the existing Python application and compiled React UI as one application image.
- Keep the default deployment private to the local machine.
- Preserve local SQLite/memory, audit data, explicit approvals, and the OmniRoute-only inference boundary.
- Add Kubernetes packaging, GitOps, infrastructure automation, metrics, dashboards, and centralized logs in dependency order.
- Keep optional infrastructure services disabled until explicitly requested.

Non-goals:
- Do not split every SITA specialist into a microservice.
- Do not deploy an internet-facing ingress by default.
- Do not embed OmniRoute or model weights into the SITA image.
- Do not mount the Docker socket into the SITA application container.
- Do not enable model-generated host commands or code execution as part of containerization.
- Do not log prompts, attachments, credentials, approval tokens, or provider responses.

## 2. Audit findings

The initial audit reviewed the repository metadata, README, project roadmap, remaining-features inventory, security/architecture documents, Python package metadata, example configuration, launchers, frontend package manifest, CLI, and web server.

### Existing application shape

- Python monorepo, installable from `pyproject.toml`; core package declares no mandatory third-party dependencies.
- React + TypeScript + Vite frontend, compiled into `src/tara_app/web/react-dist`.
- Local web application starts on port 8765.
- `GET /api/health` already exists and reports application/specialist health.
- SQLite-backed memory/session storage is local; audit events are written locally.
- OmniRoute is the only documented language-model gateway.
- Native Handler has a read-only diagnostic fallback when a native toolchain is unavailable.

### Deployment blockers to resolve before Docker/Kubernetes

1. `webapp.serve()` currently binds to `127.0.0.1` only. A container/pod needs an explicit configurable bind address while retaining loopback as the native default.
2. The web server's Host/Origin validation currently accepts only `localhost` and `127.0.0.1` with the application port. The container/Kubernetes port-forward path must preserve strict allowlisting and must not turn this into permissive CORS.
3. The launchers install dependencies at startup. Container builds should install/build dependencies at image-build time and run the already-built application without package installation at startup.
4. The frontend manifest is present, but the repository's current `.gitignore` excludes `frontend/package-lock.json`. A deterministic container build needs a committed lockfile or an explicitly pinned dependency-resolution process.
5. Persistent storage paths for SQLite, memory, and audit output must be made explicit and configurable before adding Kubernetes PVCs.
6. The application health endpoint exists, but readiness/liveness semantics and metrics exposure need to be specified and tested before probes and Prometheus scraping are enabled.

No Dockerfile, Compose manifest, Helm chart, Kubernetes manifests, Terraform configuration, Ansible playbook, Argo CD application, Prometheus/Grafana configuration, or ELK configuration was found in the reviewed repository files/code searches. This is an initial audit, not a claim of exhaustive recursive filesystem inspection.

## 3. Target local architecture

```text
Developer workstation
  |
  +-- Docker Engine / Docker Desktop
  |     |
  |     +-- SITA container
  |     |     +-- Python application
  |     |     +-- prebuilt React assets
  |     |     +-- non-root user
  |     |     +-- read-only root filesystem where practical
  |     |     +-- local data volume
  |     |
  |     +-- Optional observability profile
  |           +-- Prometheus
  |           +-- Grafana
  |           +-- Elasticsearch
  |           +-- Logstash
  |           +-- Kibana
  |
  +-- OmniRoute (existing separately managed local gateway)
        +-- configured model providers

Later:
  k3d/kind local Kubernetes
    +-- SITA Helm release
    +-- ClusterIP service only
    +-- kubectl port-forward for local access
    +-- Argo CD GitOps
    +-- Prometheus/Grafana
    +-- optional ELK profile
```

## 4. Phased implementation

### Phase 0 — Repository and runtime audit (current)

- [x] Confirm repository, default branch, and write access.
- [x] Review product architecture and safety constraints.
- [x] Inspect Python package, frontend build, CLI, web server, and health endpoint.
- [x] Identify loopback binding and Host/Origin validation constraints.
- [x] Record persistence, lockfile, health, and observability gaps.

Exit gate: architecture and blockers documented before adding deployment manifests.

### Phase 1 — Docker foundation

Deliver:
- Multi-stage image: Node build stage + Python runtime stage.
- Build frontend assets at image build time.
- Install SITA package into the runtime image.
- Non-root runtime user, minimal base image, pinned build inputs, OCI labels.
- Configurable bind address; native launch remains loopback-only by default.
- Strict configurable Host/Origin allowlist for the local Docker port mapping.
- Docker Compose with loopback-only published port, health check, restart policy, and explicit persistent data mount.
- `.dockerignore`, `.env.example`, and container build/run documentation.
- No Docker socket mount and no privileged mode.

Exit gate: image builds; container starts without installing packages at runtime; `/api/health` works; UI and API work through localhost; disallowed Host/Origin requests are rejected; persistence survives container recreation; secrets are absent from image/history/logs.

### Phase 2 — Local Kubernetes and Helm

- Use a lightweight local cluster (choose k3d or kind after checking the workstation runtime).
- Create a dedicated namespace and least-privilege service account.
- Package SITA as a Helm chart with environment-specific values.
- Use ClusterIP only; expose access through `kubectl port-forward`, not an ingress.
- Add startup/readiness/liveness probes only after endpoint semantics are tested.
- Add resource requests/limits and persistent volume claims after data paths are configurable.
- Keep secrets external to Git and inject them at deploy time.
- Document rollback and clean teardown.

Exit gate: repeatable install/upgrade/rollback and local-only access.

### Phase 3 — Terraform

Terraform is for actual infrastructure lifecycle, not for duplicating Helm's application deployment.

- Define a backend/state policy suitable for local self-hosted use.
- Model the selected self-hosted substrate (for example, a Proxmox/libvirt host if one exists) only after confirming the actual host platform.
- Keep state, credentials, and generated plans out of Git.
- Use separate modules/environments and validate plans before apply.
- Avoid using `local-exec` as a substitute for a real provider.

Exit gate: a reviewed, reproducible plan for the confirmed self-hosted target.

### Phase 4 — Ansible

- Automate host prerequisites on the selected Linux/WSL2/self-hosted nodes.
- Configure Docker/container runtime, Kubernetes prerequisites, users, firewall rules, and required directories.
- Make playbooks idempotent; use explicit inventories and privilege escalation.
- Do not configure a workstation or server until its OS and access method are confirmed.

Exit gate: a fresh supported host can be prepared repeatably.

### Phase 5 — Argo CD GitOps

- Install Argo CD into the local cluster.
- Use a dedicated project and least-privilege repository/namespace scope.
- Track Helm values and deployment manifests in Git.
- Enable automated sync only after health checks and rollback behavior are proven.
- Keep secrets out of Git; use a local secret injection workflow first.

Exit gate: Git is the deployment source of truth and a revert restores the prior release.

### Phase 6 — Prometheus and Grafana

- Install a resource-bounded monitoring stack.
- Add a SITA metrics endpoint/exporter only after defining a privacy-safe metric contract.
- Scrape Kubernetes and application health without collecting message content, file paths, credentials, or user identifiers.
- Provide dashboards for availability, request counts, latency, errors, resource use, and specialist health.
- Add alert rules only for actionable conditions.

Exit gate: dashboard data is real, useful, and contains no sensitive payloads.

### Phase 7 — ELK Stack

- Add Elasticsearch, Logstash, and Kibana as an opt-in profile, not a default local startup dependency.
- Use structured, redacted application logs and bounded retention.
- Never ship prompts, attachments, API keys, approval tokens, raw environment variables, or provider responses.
- Configure Elasticsearch single-node mode only for local development, with explicit heap and disk limits.
- Validate log rotation, retention, and teardown before enabling it.

Exit gate: searchable operational logs with tested redaction and bounded resource use.

### Phase 8 — Hardening and recovery

- Image/dependency scanning, SBOM, image signing, and pinned image digests.
- Network policies, Pod Security settings, resource quotas, and non-root execution.
- Backup/restore tests for SQLite and audit data.
- Disaster-recovery runbook and upgrade/rollback verification.
- Security review of all exposed ports and service accounts.

## 5. Local resource policy

The default local profile must remain lightweight. Monitoring and logging are opt-in. Elasticsearch is particularly resource-intensive, so ELK must not start automatically with SITA or the Kubernetes cluster. Resource limits will be set from measured usage, not guessed in production values.

## 6. Security invariants

- Native SITA continues to bind to loopback unless the operator explicitly selects a container bind address.
- Docker publishes the application port on host loopback only.
- Kubernetes uses ClusterIP and port-forward only in the local profile.
- Host and Origin validation stays strict and explicitly allowlisted.
- No ingress, NodePort, LoadBalancer, privileged container, host networking, or Docker socket mount by default.
- Secrets are runtime inputs, never baked into layers or committed.
- SITA's model inference continues through OmniRoute only.
- SITA Code remains non-executing until a separately reviewed real sandbox is implemented.

## 7. Working rules

- All work starts from a feature branch; do not commit DevOps changes directly to `main`.
- Implement one phase at a time and keep each phase independently reviewable.
- Update this plan with exact commands, test evidence, and unresolved gaps.
- Never label an item production-ready based on manifests alone.
