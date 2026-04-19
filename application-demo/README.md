# LamiSema — Application Demo

A full-stack demo of the [lamisema](https://pypi.org/project/lamisema/) package.
Upload Nepali PDFs, run pre-flight encoding analysis, and extract structured entities.

```
application-demo/
├── api/        Dockerfile that installs lamisema from PyPI
├── webapp/     Next.js 15 frontend
├── docker-compose.local.yaml   local dev stack (MinIO console exposed)
├── docker-compose.prod.yaml    production stack (health checks, restart policies)
└── .env.example
```

## Architecture

```
Browser → webapp :3000 → (Next.js rewrites /api/*) → api :9001 → minio :9000
```

The webapp proxies all `/api/*` requests to the API server — the browser never talks
to the API directly, so no CORS configuration is needed.

---

## Local development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker + Docker Compose v2)

### 1. Create your env file

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box for local dev.

### 2. Build and start

```bash
docker compose -f docker-compose.local.yaml up --build
```

| Service       | URL                          | Notes                     |
|---------------|------------------------------|---------------------------|
| Frontend      | http://localhost:3000        | Next.js SPA               |
| API           | http://localhost:8001        | FastAPI + Swagger UI /docs|
| MinIO console | http://localhost:9001        | user: minioadmin / minioadmin |

### 3. Rebuild a single service

```bash
docker compose -f docker-compose.local.yaml up --build api
```

### 4. View logs

```bash
docker compose -f docker-compose.local.yaml logs -f api
```

### 5. Stop everything

```bash
docker compose -f docker-compose.local.yaml down
```

Add `-v` to also delete the MinIO volume: `down -v`

---

## Production deployment

### Prerequisites

- A Linux server with Docker + Docker Compose v2
- A domain pointing to your server (optional, for HTTPS)

### 1. Create and configure `.env`

```bash
cp .env.example .env
```

Update the following for production:

| Variable              | What to set                                      |
|-----------------------|--------------------------------------------------|
| `MINIO_ROOT_USER`     | Strong username (not `minioadmin`)               |
| `MINIO_ROOT_PASSWORD` | Strong password (min 12 chars)                   |
| `LAMI_S3_ACCESS_KEY`  | Match `MINIO_ROOT_USER`                          |
| `LAMI_S3_SECRET_KEY`  | Match `MINIO_ROOT_PASSWORD`                      |
| `LAMI_S3_ENDPOINT`    | `http://minio:9000` (keep for self-hosted MinIO) |

To use AWS S3 instead of MinIO, set:
```
LAMI_S3_ENDPOINT=         # leave empty
LAMI_S3_ACCESS_KEY=<your AWS access key>
LAMI_S3_SECRET_KEY=<your AWS secret key>
LAMI_S3_BUCKET=<your bucket name>
```
Then remove the `minio` service from `docker-compose.prod.yaml`.

### 2. Build and start

```bash
docker compose -f docker-compose.prod.yaml up --build -d
```

Services start in dependency order and wait for health checks before proceeding.
The webapp is exposed on port `3000`. Put a reverse proxy (nginx, Caddy) in front
of it to handle TLS termination.

### 3. Updating to a new lamisema release

The API Dockerfile installs the latest `lamisema` from PyPI on every build.
To upgrade:

```bash
docker compose -f docker-compose.prod.yaml build --no-cache api
docker compose -f docker-compose.prod.yaml up -d api
```

### 4. Check service health

```bash
docker compose -f docker-compose.prod.yaml ps
```

---

## Environment variables reference

| Variable              | Default                  | Description                                      |
|-----------------------|--------------------------|--------------------------------------------------|
| `LAMI_STORAGE_TYPE`   | `s3`                     | `memory`, `disk`, or `s3`                        |
| `LAMI_S3_ENDPOINT`    | `http://minio:9000`      | S3-compatible endpoint URL                       |
| `LAMI_S3_ACCESS_KEY`  | `minioadmin`             | S3 access key                                    |
| `LAMI_S3_SECRET_KEY`  | `minioadmin`             | S3 secret key                                    |
| `LAMI_S3_BUCKET`      | `lamisema-vault`         | Bucket name for PDF and result storage           |
| `MINIO_ROOT_USER`     | `minioadmin`             | MinIO admin username                             |
| `MINIO_ROOT_PASSWORD` | `minioadmin`             | MinIO admin password                             |
| `API_URL`             | `http://api:9001`        | Internal URL the webapp uses to proxy API calls  |
