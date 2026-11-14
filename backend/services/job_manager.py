
import json
import logging
import sqlite3

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import BaseModel

from agents.graph import run_agent_workflow
from agents.schemas import PreAuthRequest


logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).resolve().parents[1] / "jobs.db"


def current_time():
    return datetime.now(timezone.utc).isoformat()


def make_json_safe(value):
    """Convert agent output into JSON-compatible data."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]

    return value


class JobManager:
    """Manages asynchronous agent jobs and SQLite persistence."""

    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.executor = ThreadPoolExecutor(max_workers=1)
        self._lock = Lock()

        self._initialize_database()

    def _connect(self):
        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self):
        with self._lock:
            connection = self._connect()

            try:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        request_data TEXT NOT NULL,
                        result_data TEXT,
                        error TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                connection.execute("""
                    UPDATE jobs
                    SET status = 'failed',
                        error = 'Server restarted before job completion',
                        updated_at = ?
                    WHERE status IN ('queued', 'running')
                """, (current_time(),))

                connection.commit()

            finally:
                connection.close()

    def _update_job(
        self,
        job_id,
        status,
        result_data=None,
        error=None,
    ):
        connection = self._connect()

        try:
            connection.execute("""
                UPDATE jobs
                SET status = ?,
                    result_data = ?,
                    error = ?,
                    updated_at = ?
                WHERE job_id = ?
            """, (
                status,
                result_data,
                error,
                current_time(),
                job_id,
            ))

            connection.commit()

        finally:
            connection.close()

    def submit_job(self, request: PreAuthRequest):
        job_id = str(uuid4())
        timestamp = current_time()
        request_data = request.model_dump_json()

        connection = self._connect()

        try:
            connection.execute("""
                INSERT INTO jobs (
                    job_id,
                    status,
                    request_data,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                "queued",
                request_data,
                timestamp,
                timestamp,
            ))

            connection.commit()

        finally:
            connection.close()

        logger.info("Job %s submitted", job_id)

        self.executor.submit(
            self._execute_job,
            job_id,
            request_data,
        )

        return self.get_job(job_id)

    def _execute_job(self, job_id, request_data):
        try:
            logger.info("Job %s started", job_id)

            self._update_job(job_id, "running")

            request = PreAuthRequest.model_validate_json(
                request_data
            )

            workflow_result = run_agent_workflow(request)

            safe_result = make_json_safe(workflow_result)

            self._update_job(
                job_id,
                "completed",
                result_data=json.dumps(safe_result),
            )

            logger.info("Job %s completed", job_id)

        except Exception:
            logger.exception("Job %s failed", job_id)

            try:
                self._update_job(
                    job_id,
                    "failed",
                    error="Agent workflow execution failed",
                )
            except Exception:
                logger.exception(
                    "Could not update failed status for job %s",
                    job_id,
                )

    def get_job(self, job_id):
        connection = self._connect()

        try:
            row = connection.execute("""
                SELECT
                    job_id,
                    status,
                    created_at,
                    updated_at
                FROM jobs
                WHERE job_id = ?
            """, (job_id,)).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_job_result(self, job_id):
        connection = self._connect()

        try:
            row = connection.execute("""
                SELECT
                    job_id,
                    status,
                    result_data,
                    error
                FROM jobs
                WHERE job_id = ?
            """, (job_id,)).fetchone()

            if row is None:
                return None

            return {
                "job_id": row["job_id"],
                "status": row["status"],
                "result": (
                    json.loads(row["result_data"])
                    if row["result_data"]
                    else None
                ),
                "error": row["error"],
            }

        finally:
            connection.close()


job_manager = JobManager()
