# Week 5 — Running Airflow with Docker

This runs a local Airflow cluster (`LocalExecutor` + Postgres metadata DB) using
the provided `docker-compose.yml`. It's a trimmed-down version of the official
Airflow docker-compose file — the Celery/Redis/worker/Flower services are
removed since they're not needed for beginner DAG concepts.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB memory and 2 CPUs available to Docker (the `airflow-init`
  service will warn if you're under this)

## 1. Set up the `.env` file

Copy the example file and fill in the values:

```bash
cp .env.example .env
```

`.env` must contain:

- `AIRFLOW_UID` — your host user ID, so files written by the containers are
  owned by you instead of root. On Linux, get it with:

  ```bash
  echo "AIRFLOW_UID=$(id -u)" 
  ```

- `FERNET_KEY` — encrypts connection passwords/variables in the Airflow
  metadata DB. The example file ships a working key for local dev; generate
  your own with:

  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

- `AIRFLOW_CONN_RIDE_SHARING_WAREHOUSE` / `AIRFLOW_CONN_RIDE_SHARING_OLTP` —
  Airflow connections pointing at the Week4/5 `ride_dw` and `ride_prod`
  Postgres databases. These run natively on the host (not as containers on
  this compose network), so the URIs use `host.docker.internal` instead of
  `localhost`. Fill in the real password before starting.

## 2. Create the required local directories

Airflow expects these to exist next to `docker-compose.yml` (they're bind-mounted
into the containers):

```bash
mkdir -p ./dags ./logs ./plugins ./config ./pipeline
```

- `dags/` — put your DAG files here
- `pipeline/` — importable as `from pipeline.xxx import ...` inside DAGs
  (mounted to `/opt/airflow/pipeline`, on `PYTHONPATH`)

## 3. Initialize Airflow

Runs DB migrations and creates the default `airflow`/`airflow` admin user:

```bash
docker compose up airflow-init
```

## 4. Start the cluster

```bash
docker compose up -d
```

This brings up:

- `postgres` — metadata database
- `airflow-apiserver` — web UI / API, on [http://localhost:8080](http://localhost:8080)
- `airflow-scheduler`
- `airflow-dag-processor`
- `airflow-triggerer`

Log in at `http://localhost:8080` with username `airflow`, password `airflow`
(override via `_AIRFLOW_WWW_USER_USERNAME` / `_AIRFLOW_WWW_USER_PASSWORD` in
`.env` before running `airflow-init`).

## Useful commands

Check service status:

```bash
docker compose ps
```

Tail logs for a service:

```bash
docker compose logs -f airflow-scheduler
```

Run an `airflow` CLI command (e.g. to test a connection or list DAGs):

```bash
docker compose run --rm airflow-cli airflow connections list
```

Stop everything:

```bash
docker compose down
```

Stop everything and delete the Postgres volume (full reset — you'll need to
re-run `airflow-init`):

```bash
docker compose down -v
```

## Notes

- This configuration is for local development only — not production.
- `extra_hosts: host.docker.internal:host-gateway` lets containers reach
  Postgres databases running natively on your host machine, not just other
  containers on the compose network.
