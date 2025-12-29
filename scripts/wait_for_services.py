import os
import sys
import time
from urllib.parse import urlparse

import psycopg2  # type: ignore
import redis
from dotenv import load_dotenv

# Load environment variables (useful for local development)
load_dotenv(os.getenv("DOTENV_PATH", ".env"))


def wait_for_postgres() -> bool:
    dbname = os.environ.get("DB_NAME", "postgres")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "password")
    host = os.environ.get("DB_HOST", "db")
    port = os.environ.get("DB_PORT", "5432")

    print(f"Waiting for PostgreSQL at {host}:{port}...")
    start_time = time.time()
    while time.time() - start_time < 60:
        try:
            conn = psycopg2.connect(
                dbname=dbname, user=user, password=password, host=host, port=port
            )
            conn.close()
            print("PostgreSQL is ready!")
            return True
        except psycopg2.OperationalError as e:
            msg = str(e).replace(password, "******") if password else str(e)
            print(f"PostgreSQL not ready: {msg}")
            time.sleep(1)
        except Exception as e:
            print(f"Unexpected error waiting for PostgreSQL: {e}")
            time.sleep(1)

    print("Timeout waiting for PostgreSQL")
    return False


def wait_for_redis() -> bool:
    broker_url = os.environ.get("CELERY_BROKER_URL")
    if not broker_url:
        print("CELERY_BROKER_URL not set, skipping Redis wait.")
        return True

    try:
        url_parts = urlparse(broker_url)
        host = url_parts.hostname
        port = url_parts.port or 6379
        print(f"Waiting for Redis at {host}:{port}...")
    except Exception:
        print("Waiting for Redis...")

    start_time = time.time()
    while time.time() - start_time < 60:
        try:
            r = redis.from_url(broker_url)
            r.ping()
            print("Redis is ready!")
            return True
        except redis.exceptions.ConnectionError as e:
            print(f"Redis not ready: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"Unexpected error waiting for Redis: {e}")
            time.sleep(1)

    print("Timeout waiting for Redis")
    return False


if __name__ == "__main__":
    # Flush stdout to ensure logs appear immediately in Docker
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    if not wait_for_postgres():
        sys.exit(1)

    if not wait_for_redis():
        sys.exit(1)

    sys.exit(0)
