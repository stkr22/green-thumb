# Setup & Deployment

How to run Green Thumb — locally for development, via docker-compose, and in
production on Kubernetes. For configuration values and external services
(Zitadel, ntfy), see [administration.md](administration.md).

## Prerequisites

| Tool | Used for |
| --- | --- |
| [uv](https://docs.astral.sh/uv/) | Python dependency management & running the backend |
| Python 3.14 | Backend runtime (uv can install it) |
| Node.js 20+ and npm | Frontend build & dev server |
| Docker / Podman | Building images; docker-compose for local full stack |
| A Zitadel instance | OIDC login (see [administration.md](administration.md#zitadel-oidc-setup)) |
| An ntfy server | Push notifications (optional) |

## Local development

The backend and frontend run as two processes. The Vite dev server proxies
`/api` and `/auth` to the backend, so the browser talks to a single origin
(`http://localhost:5173`), mirroring production.

### Backend

```bash
uv sync --group dev                       # install dependencies
uv run alembic upgrade head               # create / migrate the SQLite database
uv run uvicorn greenthumb.main:app --reload
```

The backend reads configuration from the environment (and a `.env` file if
present). At minimum it needs `SESSION_SECRET_KEY`, and the `OIDC_*` values for
real login. For a quick local run without Zitadel, see the **dev-login bypass**
in [administration.md](administration.md#dev-login-bypass-local-only).

By default the database is a `greenthumb.db` file in the working directory
(`DATABASE_URL=sqlite+aiosqlite:///./greenthumb.db`).

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api and /auth to :8000
```

Set `DEV_BACKEND_URL` if your backend isn't on `http://localhost:8000`.

### Full stack with docker-compose

`docker-compose.yml` runs the backend (with an embedded SQLite volume) and the
frontend dev server together:

```bash
cp .env.local.example .env.local     # fill in OIDC (and optionally ntfy) values
docker compose up --build
```

- Frontend: <http://localhost:5173>
- Backend API docs: <http://localhost:8000/docs>

`.env.local` is gitignored and supplies the secrets; the fixed local values
(redirect URI, cookie settings) are set in `docker-compose.yml`. See
[administration.md](administration.md#configuration-reference) for every variable.

## Production: Kubernetes + ArgoCD

greenthumb ships as a **Helm chart** in `charts/green-thumb/`, published as an OCI
artifact to `ghcr.io/stkr22/charts/green-thumb` on every release (by
`.github/workflows/helm-release.yml`). The backend is a **single stateful
instance**: the SQLite database lives on a `ReadWriteOnce` PersistentVolumeClaim
and the Deployment uses the `Recreate` strategy (the in-process reminder loop
must not run in parallel — see
[architecture.md](architecture.md#why-sqlite--single-instance)).

### Chart overview

| Template | Purpose |
| --- | --- |
| `backend-deployment.yaml` | Single replica, `Recreate`, `fsGroup: 1001`, migration `initContainer`, `/healthz` + `/readyz` probes; serves the API and the built SPA |
| `backend-service.yaml` | Backend ClusterIP service |
| `pvc.yaml` | `ReadWriteOnce` volume for the SQLite file (kept on uninstall) |
| `ingress.yaml` | Traefik routing on one hostname |

The namespace and the `green-thumb-backend` secret are **not** part of the chart:
the namespace is created by the install (`--create-namespace` /
`CreateNamespace=true`), and the secret is managed out-of-band (see below).
`k8s/backend/secret.example.yaml` (the secret template) is kept for reference.
The ArgoCD `Application` is **not** in this repo — it lives in the GitOps repo
that owns the cluster's ArgoCD applications. See `charts/green-thumb/README.md`
for the full values reference.

### Deployment steps

1. **Create the backend secret** out-of-band (it is intentionally not in Git):
   ```bash
   kubectl -n green-thumb create secret generic green-thumb-backend \
     --from-literal=OIDC_ISSUER_URL=https://auth.example.com \
     --from-literal=OIDC_CLIENT_ID=... \
     --from-literal=OIDC_CLIENT_SECRET=... \
     --from-literal=OIDC_REDIRECT_URI=https://plants.example.com/auth/callback \
     --from-literal=SESSION_SECRET_KEY="$(openssl rand -hex 32)" \
     --from-literal=FRONTEND_URL=https://plants.example.com \
     --from-literal=NTFY_URL=https://ntfy.example.com \
     --from-literal=NTFY_TOPIC=greenthumb \
     --from-literal=NTFY_TOKEN=...
   ```
   For GitOps, manage this with sealed-secrets or SOPS instead of `kubectl create`.
2. **Install the chart** — directly with Helm:
   ```bash
   helm install green-thumb oci://ghcr.io/stkr22/charts/green-thumb \
     --version <chart-version> \
     --namespace green-thumb --create-namespace \
     --set ingress.host=plants.example.com
   ```
   The image tag defaults to the chart `appVersion`; override with
   `--set backend.image.tag=...` if needed.
3. **…or via ArgoCD** — register the OCI registry as a Helm repo once, then point
   an ArgoCD `Application` (managed in your GitOps repo) at the chart, setting the
   hostname under `helm.valuesObject`:
   ```bash
   argocd repo add ghcr.io/stkr22/charts --type helm --enable-oci \
     --username <user> --password <ghcr-token>
   ```
   The `Application` should target chart `greenthumb` from `ghcr.io/stkr22/charts`
   with sync `prune` + `selfHeal` and `CreateNamespace=true`. The migration
   `initContainer` runs `alembic upgrade head` before the app container starts on
   every rollout. The PVC carries `helm.sh/resource-policy: keep`, so the database
   is not pruned.

### TLS

`SESSION_COOKIE_SECURE` defaults to `true`, so the app expects to be served over
HTTPS in production. Terminate TLS at Traefik (e.g. with cert-manager) and set
`ingress.tls.enabled=true` (with `ingress.tls.secretName`). The session cookie will not be
sent over plain HTTP unless you set `SESSION_COOKIE_SECURE=false` (development
only).

### Same-origin routing

The whole hostname (`plants.example.com/*`) routes to the backend, which serves
both the API (`/api/*`, `/auth/*`) and the built SPA from the same origin, so
there is no CORS to configure. The SPA is built with `VITE_API_BASE_URL=""` so
it calls `/api/...` and `/auth/...` on its own origin.

## Building the container image

```bash
# From the repo root
docker build -f Containerfile -t ghcr.io/<you>/green-thumb:<tag> .
```

One image builds the SPA, runs the FastAPI app, serves the static SPA, and
contains Alembic + the migrations (used by the migration `initContainer`).
