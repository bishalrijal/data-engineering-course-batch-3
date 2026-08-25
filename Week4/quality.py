import logging

logger = logging.getLogger(__name__)

class DataQualityError(Exception):
    pass

def check_negative_fares(rows):
    bad_data = [ row for row in rows if row["fare_amount"] < 0 ]
    return {
        "check": "no_negative_fare",
        "passed": len(bad_data) == 0,
        "details": f"{len(bad_data)} rows with negative fare"
    }

def check_row_count(rows):
    count = len(rows)
    return{
        "check": "row_count",
        "passed": count > 0,
        "details": f"{count} rows"
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

def run_quality_check(rows):
    checks = [
        check_row_count(rows),
        check_completed_have_duration(rows),
        check_negative_fares(rows),
        check_no_null_driver_keys(rows),
        check_valid_status(rows)
    ]
    failed = [c for c in checks if not c["passed"]]

    if failed and len(failed) > 0:
        first = failed[0]
        # To do log every failed data 
        """
        ---------------------------
        checks | status | details
        -------------------------
        row_count| passed| 500 rows

        """
        raise DataQualityError(
            f"Quality check failed: {first['check']} - {first['details']}"
        )
    return True