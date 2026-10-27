from django.core.checks import Error, run_checks
from django.db import connections


class TestSystemChecks:
    def test_no_system_check_errors(self) -> None:
        # Index and constraint checks (postgres.E005 for GistIndex) only run
        # when the databases are passed in.
        errors = [
            message
            for message in run_checks(databases=list(connections))
            if isinstance(message, Error) or message.level >= 40
        ]
        assert errors == [], [f"{e.id}: {e.msg}" for e in errors]
