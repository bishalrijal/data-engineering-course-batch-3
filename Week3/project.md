# Python CSV Loading Project 

## Part A — Basic Load

1. Create a Python script that connects to the database and loads data from the Week 1 CSV file.
2. Truncate the *original* `rides` table (not the normalized version) before loading.
3. Read the CSV file using `csv` or `pandas`.
4. Insert the rows into the `rides` table.

This part is a good opportunity to practice file handling, database connectivity, and data insertion in Python.

## Part B — Incremental Daily Loading

Extend the script so it can run every day against a `data/` folder that accumulates one new file per day, named like `rides_20260812.csv`, `rides_20260813.csv`, etc.

### Requirements

- The script should **only process files it hasn't already loaded**, even if run multiple times or if old files are still sitting in the folder.
- It should **not truncate** the table anymore in this mode — new files should be *appended*, not replace existing data.
- It should handle the case where multiple new files appear since the last run (e.g., someone missed a day).

### Hints on how to approach it

1. **Track processed files, not just dates.** Create a small tracking table:

   ```sql
   CREATE TABLE processed_files (
       filename TEXT PRIMARY KEY,
       processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       row_count INTEGER
   );
   ```

   Before loading a file, check if its name already exists in this table — if so, skip it.

2. **Extract the timestamp from the filename** using a regex (e.g., `re.match(r"rides_(\d{8})\.csv", filename)`) so you can sort files chronologically and log which date each batch corresponds to.

3. **List and filter files with `pathlib` or `glob`:**

   ```python
   from pathlib import Path
   files = sorted(Path("data").glob("rides_*.csv"))
   ```

4. **Wrap each file's load in a transaction.** Insert the rows and the `processed_files` record in the same transaction so a crash mid-load doesn't leave a file "half loaded but marked as done."

5. **Make it idempotent-safe.** Even with tracking, consider a unique constraint (e.g., ride ID) on `rides` so a re-run can't double-insert if something goes wrong.

6. **Design for automation.** Since this "arrives daily," structure the script so it can be triggered by a cron job / scheduler with no manual input needed — no truncation, no hardcoded filename.