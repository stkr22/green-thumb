# green-thumb Helm chart

Deploys [green-thumb](https://github.com/stkr22/green-thumb), a self-hosted plant
care tracker: a single-instance FastAPI backend (SQLite on a PVC + an in-process
reminder loop) that also serves the built React SPA, behind one Ingress.

## Install

The chart is published as an OCI artifact to GitHub Container Registry:

```bash
# Create the runtime secret first (see "Backend secret" below), then:
helm install green-thumb oci://ghcr.io/stkr22/charts/green-thumb \
  --version <chart-version> \
  --namespace green-thumb --create-namespace \
  --set ingress.host=plants.example.com
```

> Use release name `green-thumb` so the generated object names stay
> `green-thumb-backend` (a different release name prefixes them; internal
> references still resolve either way).

## Backend secret

The backend reads its runtime config via `envFrom` from an existing Secret
(default name `green-thumb-backend`, set via `backend.existingSecret`). The chart
does **not** create it — manage it out-of-band (sealed-secrets, SOPS, ...):

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

`SESSION_SECRET_KEY` must be present even with migrations enabled (settings
validation runs in the migration init container).

## Key values

| Key | Default | Description |
| --- | --- | --- |
| `backend.image.repository` | `ghcr.io/stkr22/green-thumb` | Backend image. Tag defaults to chart `appVersion`. |
| `backend.databaseUrl` | `sqlite+aiosqlite:////data/greenthumb.db` | SQLAlchemy URL (absolute path on the PVC). |
| `backend.existingSecret` | `green-thumb-backend` | Secret consumed via `envFrom`. |
| `backend.migrations.enabled` | `true` | Run `alembic upgrade head` in an init container. |
| `persistence.enabled` | `true` | Create the SQLite PVC. |
| `persistence.existingClaim` | `""` | Use a pre-existing PVC instead of creating one. |
| `persistence.size` | `5Gi` | PVC size (photos are stored inline as BLOBs). |
| `persistence.storageClass` | `""` | `""` = cluster default, `-` = no dynamic provisioning. |
| `ingress.enabled` | `true` | Create the Ingress. |
| `ingress.className` | `traefik` | IngressClass. |
| `ingress.host` | `plants.example.com` | Hostname. |
| `ingress.tls.enabled` | `false` | Terminate TLS at the Ingress. |

The backend is intentionally **not scalable**: `replicas` is fixed at 1 and the
deploy strategy is `Recreate` because the SQLite PVC is `ReadWriteOnce` and the
reminder loop must stay singleton.

## Data safety

The chart-managed PVC carries `helm.sh/resource-policy: keep`, so the database
survives `helm uninstall`. Delete it manually if you really want to discard data.
