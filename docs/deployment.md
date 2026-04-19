# Deployment

## Docker (recommended)

The easiest way to run the full stack is with the demo app in `application-demo/`.

```bash
cd application-demo
cp .env.example .env
docker compose -f docker-compose.local.yaml up --build
```

See [`application-demo/README.md`](../application-demo/README.md) for the full guide including production setup, AWS S3, and HTTPS.

---

## API server only

If you only need the API (no frontend, no MinIO):

```bash
pip install lamisema
lamisema serve
# → http://localhost:9001/docs
```

Default storage is in-memory (data lost on restart). For persistence:

```bash
# Disk storage
LAMI_STORAGE_TYPE=disk lamisema serve

# S3 storage
LAMI_STORAGE_TYPE=s3 \
LAMI_S3_ENDPOINT=http://localhost:9000 \
LAMI_S3_ACCESS_KEY=... \
LAMI_S3_SECRET_KEY=... \
lamisema serve
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LAMI_STORAGE_TYPE` | `memory` | `memory`, `disk`, or `s3` |
| `LAMI_S3_ENDPOINT` | — | S3-compatible endpoint URL |
| `LAMI_S3_ACCESS_KEY` | — | S3 access key |
| `LAMI_S3_SECRET_KEY` | — | S3 secret key |
| `LAMI_S3_BUCKET` | `lamisema-vault` | Bucket name |
| `PORT` | `9001` | Server port |

---

## Storage fallback

If `LAMI_STORAGE_TYPE=s3` is set but the connection fails, LamiSema automatically falls back to disk storage. Check the active backend via the health endpoint:

```bash
curl http://localhost:9001/
# → { "storage_backend": "InMemoryStorage" | "LocalStorage" | "S3Storage" }
```

---

## Security

The API has no built-in authentication. For production:

- Deploy behind a reverse proxy (Nginx, Caddy, Traefik)
- Restrict access to a private network or VPN
- Implement bucket lifecycle rules to purge old files
