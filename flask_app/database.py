import sqlite3
import pandas as pd
import sys
import os

# Always find the DB relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "grc.db")

SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "..", "sample_data")


def get_db():
    """Return a DB connection. Call this from Flask routes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    return conn


def init_db():
    """Create tables and load CSV data into SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Main exceptions table ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exceptions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            exception_id     TEXT UNIQUE,
            type             TEXT,
            requester        TEXT,
            approver         TEXT,
            business_unit    TEXT,
            justification    TEXT,
            start_date       TEXT,
            end_date         TEXT,
            status           TEXT,
            risk_level       TEXT,
            risk_score       REAL DEFAULT 0,
            predicted_anomaly INTEGER DEFAULT 0,
            predicted_type   TEXT DEFAULT 'NONE',
            predicted_severity TEXT DEFAULT 'NONE'
        )
    """)

    # ── Labels table (ground truth for evaluation) ─────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exception_labels (
            exception_id  TEXT PRIMARY KEY,
            is_anomaly    INTEGER,
            anomaly_type  TEXT,
            severity      TEXT,
            explanation   TEXT
        )
    """)

    conn.commit()

    # ── Load CSVs if tables are empty ─────────────────────────────
    count = cur.execute("SELECT COUNT(*) FROM exceptions").fetchone()[0]
    if count == 0:
        print("Loading CSV data into SQLite...")

        scored_path = os.path.join(SAMPLE_DATA_DIR, "scored_exceptions.csv")
        registry_path = os.path.join(SAMPLE_DATA_DIR, "exception_registry.csv")
        labels_path = os.path.join(SAMPLE_DATA_DIR, "exception_labels.csv")

        # Use scored_exceptions if available, else plain registry
        if os.path.exists(scored_path):
            df = pd.read_csv(scored_path)
        else:
            df = pd.read_csv(registry_path)
            df["risk_score"] = 0
            df["predicted_anomaly"] = False
            df["predicted_type"] = "NONE"
            df["predicted_severity"] = "NONE"

        # Keep only the columns our table expects
        keep = ["exception_id","type","requester","approver","business_unit",
                "justification","start_date","end_date","status","risk_level",
                "risk_score","predicted_anomaly","predicted_type","predicted_severity"]

        # business_unit may be missing in some CSVs
        if "business_unit" not in df.columns:
            df["business_unit"] = "Unknown"

        df = df[keep].copy()
        df["predicted_anomaly"] = df["predicted_anomaly"].astype(int)
        df.to_sql("exceptions", conn, if_exists="append", index=False)
        print(f"  Loaded {len(df)} exception records")

        # Load labels
        if os.path.exists(labels_path):
            df_lbl = pd.read_csv(labels_path)
            df_lbl["is_anomaly"] = df_lbl["is_anomaly"].astype(int)
            df_lbl.to_sql("exception_labels", conn, if_exists="append", index=False)
            print(f"  Loaded {len(df_lbl)} label records")

        conn.commit()
        print("Database ready.")
    else:
        print(f"Database already has {count} records — skipping CSV load.")

    conn.close()


if __name__ == "__main__":
    init_db()
    # Quick sanity check
    conn = get_db()
    rows = conn.execute("SELECT COUNT(*) as cnt FROM exceptions").fetchone()
    print(f"Total exceptions in DB : {rows['cnt']}")
    rows = conn.execute("SELECT status, COUNT(*) as cnt FROM exceptions GROUP BY status").fetchall()
    for r in rows:
        print(f"  {r['status']:10s} : {r['cnt']}")
    conn.close()