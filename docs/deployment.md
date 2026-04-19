# Production Deployment Guide

LamiSema is designed to be deployed as a stateless containerized service with persistent object storage.

---

## 1. Local Production Stack (Docker Compose)

The easiest way to run the full stack (API + Minio) is using Docker Compose.

```bash
docker-compose up -d
```

This starts:
- **API Server**: `http://localhost:8001`
- **Minio Console**: `http://localhost:9001` (User: `minioadmin`, Pass: `minioadmin`)

All uploads and results will be persisted in a Docker volume named `minio_data`.

---

## 2. Environment Variables

Configure the API behavior using these variables:

| Variable | Default | Description |
|---|---|---|
| `LAMI_STORAGE_TYPE` | `memory` | `memory` (volatile), `disk` (persistent /uploads), or `s3` (persistent remote) |
| `LAMI_S3_ENDPOINT` | — | Minio/S3 endpoint (e.g. `http://minio:9000`) |
| `LAMI_S3_ACCESS_KEY` | — | S3 Access Key |
| `LAMI_S3_SECRET_KEY` | — | S3 Secret Key |
| `LAMI_S3_BUCKET` | `lamisema-vault` | Bucket name for storage |
| `PORT` | `9001` | Internal container port |

---

## 3. Automatic Fallback Behavior

LamiSema is designed for high availability:
- If `LAMI_STORAGE_TYPE=s3` is set but the S3/Minio connection fails (e.g., Minio container is down), the API **automatically falls back to disk storage** in the `/uploads` directory.
- This ensures the service remains functional even during storage outages.
- You can check which backend is active via the `GET /` health endpoint (`storage_backend` field).

---

## 4. Kubernetes / Managed Cloud (S3)

To deploy to AWS/GCP without running Minio:

1. Create an S3 bucket.
2. Set `LAMI_STORAGE_TYPE=s3`.
3. Provide the bucket credentials via ENV variables.
4. If using AWS, you can leave `LAMI_S3_ENDPOINT` blank to use the default regional endpoint.

---

## 4. Manual Server Setup (No Docker)

If you must run on a bare Linux server:

1. **System Deps**:
   ```bash
   sudo apt-get install tesseract-ocr tesseract-ocr-nep libgl1
   ```
2. **Install**:
   ```bash
   pip install lamisema[s3]
   ```
3. **Run**:
   ```bash
   export LAMI_STORAGE_TYPE=s3
   # Set other variables...
   lamisema serve
   ```

---

## 5. Security Notes

- **Network**: The API currently has no built-in auth. It should be deployed behind a reverse proxy (Nginx, Traefik) or in a private VPC.
- **Persistence**: Results are stored in the `results/` prefix of your bucket as JSON.
- **Cleanup**: LamiSema does not automatically delete files from the storage backend. Implement bucket lifecycle rules to purge old files if needed.
