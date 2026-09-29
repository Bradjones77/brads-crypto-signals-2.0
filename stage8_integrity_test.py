"""BRAD'S SIGNALS BOT 2.0 - Stage 8 database/integrity diagnostic.

Read-only checks only.
No Telegram sends. No database writes. No trade execution.
"""
import sys
import memory_engine

PREFIX = "STAGE 8 INTEGRITY: "

def scalar(cursor, query, params=()):
    cursor.execute(query, params)
    row = cursor.fetchone()
    return int(row[0] or 0)

def main():
    print(PREFIX + "START", flush=True)
    print(PREFIX + "DATABASE WRITES: NONE", flush=True)
    print(PREFIX + "TELEGRAM SENDS: NONE", flush=True)
    print(PREFIX + "TRADE EXECUTION: NONE", flush=True)

    conn = None
    try:
        conn = memory_engine.connect()
        with conn.cursor() as cur:
            total = scalar(cur, "SELECT COUNT(*) FROM signals2_opportunities")

            duplicate_ids = scalar(
                cur,
                """
                SELECT COUNT(*) FROM (
                    SELECT opportunity_id
                    FROM signals2_opportunities
                    GROUP BY opportunity_id
                    HAVING COUNT(*) > 1
                ) d
                """
            )

            bad_confidence = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM signals2_opportunities
                WHERE final_confidence IS NULL
                   OR final_confidence < 0
                   OR final_confidence > 100
                """
            )

            sent_state_mismatch = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM signals2_opportunities
                WHERE (signal_sent = TRUE AND decision <> 'SENT')
                   OR (decision = 'SENT' AND signal_sent <> TRUE)
                """
            )

            sendable_below_threshold = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM signals2_opportunities
                WHERE decision = 'SELECTED_NOT_SENT'
                  AND final_confidence < 80
                """
            )

            recent = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM signals2_opportunities
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                """
            )

        print(PREFIX + f"ROWS TOTAL: {total}", flush=True)
        print(PREFIX + f"ROWS LAST 24H: {recent}", flush=True)
        print(PREFIX + f"DUPLICATE OPPORTUNITY IDS: {duplicate_ids}", flush=True)
        print(PREFIX + f"INVALID CONFIDENCE ROWS: {bad_confidence}", flush=True)
        print(PREFIX + f"SENT-STATE MISMATCHES: {sent_state_mismatch}", flush=True)
        print(PREFIX + f"SELECTED BELOW 80: {sendable_below_threshold}", flush=True)

        failures = (
            duplicate_ids
            + bad_confidence
            + sent_state_mismatch
            + sendable_below_threshold
        )
        if failures:
            print(PREFIX + "FAIL", flush=True)
            sys.exit(1)

        print(PREFIX + "PASS", flush=True)

    except Exception as exc:
        print(PREFIX + "ERROR: " + type(exc).__name__ + ": " + str(exc), flush=True)
        sys.exit(1)
    finally:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
