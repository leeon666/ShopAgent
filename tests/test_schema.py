import tempfile
from pathlib import Path

from sqlalchemy import create_engine

from app.db import schema_errors


def test_schema_errors_detect_old_columns():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory, "test.db").as_posix()
        test_engine = create_engine(f"sqlite:///{path}")
        with test_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE agent_runs (id INTEGER PRIMARY KEY, status TEXT)"
            )

        errors = schema_errors(test_engine)
        assert any("audit_logs" in error and "request_id" in error for error in errors)
        assert any("agent_runs" in error and "estimated_cost_usd" in error for error in errors)
        test_engine.dispose()
