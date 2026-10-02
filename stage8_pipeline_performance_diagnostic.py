import os
import json
from datetime import datetime, timezone

# ============================================================
# BRAD'S SIGNALS BOT 2.0
# STAGE 8 — READ-ONLY PIPELINE / PERFORMANCE DIAGNOSTIC
#
# PURPOSE:
# - Inspect stored Bot 2.0 opportunities and outcomes.
# - Verify database state consistency.
# - Summarise AI coverage and confidence distribution.
# - Summarise completed historical outcomes descriptively.
#
# SAFETY:
# - READ ONLY database session.
# - NO Telegram sends.
# - NO Bitget orders.
# - NO database writes.
# - NO model/strategy changes.
# ============================================================

MINIMUM_SIGNAL_CONFIDENCE = 80.0
LOOKBACK_HOURS = 24
RECENT_LIMIT = 10000


def pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 2)


def safe_number(value):
    if value is None:
        return None
    try:
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None
        return number
    except Exception:
        return None


def main():
    prefix = "STAGE 8 PIPELINE DIAGNOSTIC: "
    print(prefix + "START (read only; no sends; no trades)", flush=True)

    database_url = os.environ.get("SIGNALS2_DATABASE_URL", "").strip()
    if not database_url:
        print(prefix + "FAIL (SIGNALS2_DATABASE_URL missing)", flush=True)
        return 1

    connection = None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        connection = psycopg2.connect(database_url, connect_timeout=8)
        connection.set_session(readonly=True, autocommit=False)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # Core counts and state-integrity checks.
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE created_at >= NOW() - INTERVAL '24 hours'
                    ) AS last_24h,
                    COUNT(*) FILTER (
                        WHERE final_confidence IS NULL
                           OR final_confidence < 0
                           OR final_confidence > 100
                    ) AS invalid_confidence,
                    COUNT(*) FILTER (
                        WHERE direction NOT IN ('LONG','SHORT')
                    ) AS invalid_direction,
                    COUNT(*) FILTER (
                        WHERE entry_price IS NULL OR entry_price <= 0
                    ) AS invalid_entry,
                    COUNT(*) FILTER (
                        WHERE decision = 'SELECTED_NOT_SENT'
                          AND final_confidence < %s
                    ) AS selected_below_threshold,
                    COUNT(*) FILTER (
                        WHERE signal_sent = TRUE
                          AND decision <> 'SENT'
                    ) AS sent_state_mismatch_a,
                    COUNT(*) FILTER (
                        WHERE decision = 'SENT'
                          AND signal_sent = FALSE
                    ) AS sent_state_mismatch_b,
                    COUNT(*) FILTER (
                        WHERE decision = 'SELECTED_NOT_SENT'
                    ) AS selected_not_sent,
                    COUNT(*) FILTER (
                        WHERE decision = 'SENT'
                    ) AS sent,
                    COUNT(*) FILTER (
                        WHERE decision = 'REJECTED'
                    ) AS rejected
                FROM signals2_opportunities
            """, (MINIMUM_SIGNAL_CONFIDENCE,))
            core = dict(cursor.fetchone())

            cursor.execute("""
                SELECT COUNT(*) AS duplicate_groups
                FROM (
                    SELECT opportunity_id
                    FROM signals2_opportunities
                    GROUP BY opportunity_id
                    HAVING COUNT(*) > 1
                ) d
            """)
            duplicate_groups = int(cursor.fetchone()["duplicate_groups"])

            cursor.execute("""
                SELECT
                    COUNT(*) AS opportunity_count,
                    COUNT(r.opportunity_id) AS outcome_rows,
                    COUNT(*) FILTER (
                        WHERE r.opportunity_id IS NULL
                    ) AS missing_outcomes
                FROM signals2_opportunities o
                LEFT JOIN signals2_outcomes r
                  ON r.opportunity_id = o.opportunity_id
            """)
            linkage = dict(cursor.fetchone())

            # Recent AI + confidence coverage.
            cursor.execute("""
                SELECT
                    COUNT(*) AS recent_rows,
                    COUNT(*) FILTER (
                        WHERE LOWER(COALESCE(ai_analysis->>'available', '')) = 'true'
                    ) AS ai_available_rows,
                    COUNT(*) FILTER (
                        WHERE ai_confidence IS NOT NULL
                    ) AS ai_confidence_rows,
                    COUNT(*) FILTER (
                        WHERE final_confidence >= %s
                    ) AS at_or_above_threshold,
                    AVG(final_confidence) AS avg_confidence,
                    MIN(final_confidence) AS min_confidence,
                    MAX(final_confidence) AS max_confidence
                FROM signals2_opportunities
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                  AND symbol NOT LIKE 'SIGNALS2%%'
            """, (MINIMUM_SIGNAL_CONFIDENCE,))
            recent = dict(cursor.fetchone())

            # Model/strategy labels currently being stored.
            cursor.execute("""
                SELECT
                    COALESCE(model_version, '<NULL>') AS model_version,
                    COALESCE(strategy_version, '<NULL>') AS strategy_version,
                    COUNT(*) AS rows
                FROM signals2_opportunities
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                  AND symbol NOT LIKE 'SIGNALS2%%'
                GROUP BY model_version, strategy_version
                ORDER BY rows DESC
                LIMIT 10
            """)
            versions = [dict(row) for row in cursor.fetchall()]

            # Completed-outcome descriptive summary. This is historical database
            # evidence only; it is NOT a prediction of future performance.
            cursor.execute("""
                SELECT
                    COUNT(*) AS completed,
                    COUNT(*) FILTER (WHERE direction_correct_24h = TRUE) AS correct_24h,
                    COUNT(*) FILTER (WHERE direction_correct_24h = FALSE) AS incorrect_24h,
                    AVG(return_24h_pct) AS avg_return_24h_pct,
                    AVG(max_favorable_excursion_pct) AS avg_mfe_pct,
                    AVG(max_adverse_excursion_pct) AS avg_mae_pct
                FROM signals2_outcomes
                WHERE outcome_complete = TRUE
                  AND symbol NOT LIKE 'SIGNALS2%%'
            """)
            outcomes = dict(cursor.fetchone())

            # Confidence bands on completed historical observations.
            cursor.execute("""
                SELECT
                    CASE
                        WHEN o.final_confidence < 50 THEN '0-49.99'
                        WHEN o.final_confidence < 65 THEN '50-64.99'
                        WHEN o.final_confidence < 80 THEN '65-79.99'
                        ELSE '80-100'
                    END AS confidence_band,
                    COUNT(*) AS completed,
                    COUNT(*) FILTER (
                        WHERE r.direction_correct_24h = TRUE
                    ) AS correct_24h,
                    AVG(r.return_24h_pct) AS avg_return_24h_pct
                FROM signals2_opportunities o
                JOIN signals2_outcomes r
                  ON r.opportunity_id = o.opportunity_id
                WHERE r.outcome_complete = TRUE
                  AND o.symbol NOT LIKE 'SIGNALS2%%'
                  AND o.final_confidence IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """)
            bands = [dict(row) for row in cursor.fetchall()]

        total = int(core["total"] or 0)
        mismatches = int(core["sent_state_mismatch_a"] or 0) + int(core["sent_state_mismatch_b"] or 0)

        print(prefix + "CORE " + json.dumps({
            "total": total,
            "last_24h": int(core["last_24h"] or 0),
            "duplicate_opportunity_groups": duplicate_groups,
            "invalid_confidence": int(core["invalid_confidence"] or 0),
            "invalid_direction": int(core["invalid_direction"] or 0),
            "invalid_entry": int(core["invalid_entry"] or 0),
            "selected_below_80": int(core["selected_below_threshold"] or 0),
            "sent_state_mismatches": mismatches,
            "selected_not_sent": int(core["selected_not_sent"] or 0),
            "sent": int(core["sent"] or 0),
            "rejected": int(core["rejected"] or 0),
        }), flush=True)

        print(prefix + "LINKAGE " + json.dumps({
            "opportunities": int(linkage["opportunity_count"] or 0),
            "outcome_rows": int(linkage["outcome_rows"] or 0),
            "missing_outcomes": int(linkage["missing_outcomes"] or 0),
        }), flush=True)

        recent_rows = int(recent["recent_rows"] or 0)
        ai_available = int(recent["ai_available_rows"] or 0)
        print(prefix + "RECENT_24H " + json.dumps({
            "rows": recent_rows,
            "ai_available_rows": ai_available,
            "ai_available_pct": pct(ai_available, recent_rows),
            "ai_confidence_rows": int(recent["ai_confidence_rows"] or 0),
            "at_or_above_80": int(recent["at_or_above_threshold"] or 0),
            "avg_confidence": safe_number(recent["avg_confidence"]),
            "min_confidence": safe_number(recent["min_confidence"]),
            "max_confidence": safe_number(recent["max_confidence"]),
        }), flush=True)

        print(prefix + "VERSIONS " + json.dumps(versions, default=str), flush=True)

        completed = int(outcomes["completed"] or 0)
        correct = int(outcomes["correct_24h"] or 0)
        print(prefix + "HISTORICAL_COMPLETED " + json.dumps({
            "completed": completed,
            "correct_24h": correct,
            "incorrect_24h": int(outcomes["incorrect_24h"] or 0),
            "direction_correct_24h_pct": pct(correct, completed),
            "avg_return_24h_pct": safe_number(outcomes["avg_return_24h_pct"]),
            "avg_mfe_pct": safe_number(outcomes["avg_mfe_pct"]),
            "avg_mae_pct": safe_number(outcomes["avg_mae_pct"]),
            "note": "descriptive historical observations; not a future win-rate claim"
        }), flush=True)

        printable_bands = []
        for row in bands:
            count = int(row["completed"] or 0)
            correct_band = int(row["correct_24h"] or 0)
            printable_bands.append({
                "band": row["confidence_band"],
                "completed": count,
                "correct_24h": correct_band,
                "correct_24h_pct": pct(correct_band, count),
                "avg_return_24h_pct": safe_number(row["avg_return_24h_pct"]),
            })
        print(prefix + "CONFIDENCE_BANDS " + json.dumps(printable_bands), flush=True)

        failures = []
        if duplicate_groups:
            failures.append("duplicate opportunity IDs")
        if int(core["invalid_confidence"] or 0):
            failures.append("invalid confidence rows")
        if int(core["invalid_direction"] or 0):
            failures.append("invalid direction rows")
        if int(core["invalid_entry"] or 0):
            failures.append("invalid entry rows")
        if int(core["selected_below_threshold"] or 0):
            failures.append("selected rows below 80")
        if mismatches:
            failures.append("sent-state mismatches")
        if int(linkage["missing_outcomes"] or 0):
            failures.append("opportunities missing outcome rows")

        if failures:
            print(prefix + "INTEGRITY: FAIL (" + "; ".join(failures) + ")", flush=True)
            return 2

        print(prefix + "INTEGRITY: PASS", flush=True)
        print(prefix + "COMPLETE (read only; no writes; no sends; no trades)", flush=True)
        return 0

    except Exception as exc:
        # Avoid printing exception details because database/network errors may
        # contain infrastructure information.
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return 1
    finally:
        if connection is not None:
            try:
                connection.rollback()
                connection.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
