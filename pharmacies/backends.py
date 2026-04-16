"""Custom Celery result backend for resilient DB writes."""

from typing import Any

from django.db import close_old_connections
from django_celery_results.backends.database import (
    DatabaseBackend,
)


class ResilientDatabaseBackend(DatabaseBackend):
    """DatabaseBackend that refreshes stale DB connections before each write.

    During worker shutdown (e.g. when the Redis broker becomes unreachable),
    Django may have already closed its DB connections by the time Celery's
    failure path calls _store_result.  Calling close_old_connections() here
    ensures a live connection is used for the write instead of the
    already-closed one that produced ECZANEREDE-P / ECZANEREDE-Q.
    """

    def _store_result(
        self,
        task_id: str,
        result: Any,
        status: str,
        traceback: str | None = None,
        request: Any | None = None,
        using: str | None = None,
    ) -> Any:
        close_old_connections()
        return super()._store_result(task_id, result, status, traceback, request, using)
