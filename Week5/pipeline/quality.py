"""
quality.py
----------
Week 5 pipeline module — Quality gate

Responsibilities:
  - Run data quality checks on transformed rows BEFORE load
  - Raise DataQualityError (halts pipeline) if any check fails
  - Log a quality summary even when all checks pass

The quality gate is the pipeline's immune system.
A loud failure here is far better than silent bad data in the warehouse.
"""

import logging

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """
    Raised when a data quality check fails.
    Signals the pipeline to halt — nothing gets loaded.

    Include the check name and failure details in the message
    so on-call engineers can act without reading the code.
    """
    pass


def check_row_count(rows: list, min_rows: int = 1) -> dict:
    """Fail if the transformed row count is below a minimum threshold."""
    count = len(rows)
    passed = count >= min_rows
    return {
        "check": "row_count",
        "passed": passed,
        "detail": f"{count} rows (min: {min_rows})"
    }


def check_no_negative_fares(rows: list) -> dict:
    """Fail if any row has fare_amount <= 0."""
    bad = [r for r in rows if r["fare_amount"] < 0]
    return {
        "check": "no_negative_fares",
        "passed": len(bad) == 0,
        "detail": f"{len(bad)} rows with fare_amount <= 0"
    }


def check_no_null_driver_keys(rows: list) -> dict:
    """Fail if any row is missing a driver_key."""
    bad = [r for r in rows if r.get("driver_key") is None]
    return {
        "check": "no_null_driver_keys",
        "passed": len(bad) == 0,
        "detail": f"{len(bad)} rows with NULL driver_key"
    }


def check_completed_have_duration(rows: list) -> dict:
    """Fail if any completed trip is missing duration_minutes."""
    bad = [
        r for r in rows
        if r["status"] == "completed" and r["duration_minutes"] is None
    ]
    return {
        "check": "completed_have_duration",
        "passed": len(bad) == 0,
        "detail": f"{len(bad)} completed trips with NULL duration_minutes"
    }


def check_valid_status(rows: list) -> dict:
    """Fail if any row has an unrecognised status value."""
    valid = {"completed", "cancelled", "no_show"}
    bad = [r for r in rows if r["status"] not in valid]
    return {
        "check": "valid_status",
        "passed": len(bad) == 0,
        "detail": f"{len(bad)} rows with invalid status"
    }


def run_quality_checks(rows: list) -> dict:
    """
    Run all quality checks on transformed rows.

    Returns a summary dict if all checks pass.
    Raises DataQualityError immediately on the first failure.

    Args:
        rows: transformed fact rows from transform layer

    Returns:
        {'passed': True, 'checks': [...check results...], 'row_count': N}

    Raises:
        DataQualityError: with details of the failing check
    """
    checks = [
        check_row_count(rows),
        check_no_negative_fares(rows),
        check_no_null_driver_keys(rows),
        check_completed_have_duration(rows),
        check_valid_status(rows),
    ]

    failed = [c for c in checks if not c["passed"]]

    if failed:
        first = failed[0]
        raise DataQualityError(
            f"Quality check failed: {first['check']} — {first['detail']}"
        )

    summary = {
        "passed": True,
        "checks": checks,
        "row_count": len(rows)
    }

    logger.info(f"Quality gate passed: {len(rows):,} rows, {len(checks)} checks")
    for c in checks:
        logger.debug(f"  {c['check']}: {c['detail']}")

    return summary
