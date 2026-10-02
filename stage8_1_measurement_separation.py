"""
BRAD'S SIGNALS BOT 2.0
Stage 8.1 - Measurement Separation Diagnostic

READ ONLY.
Separates:
1) all completed observations
2) signal candidates (ELIGIBLE/SELECTED/SENT decision states where present)
3) selected/sent records
4) rejected observations

No writes. No Telegram. No trades.
"""

import json
import os
import psycopg2

DB = os.environ.get("SIGNALS2_DATABASE_URL", "").strip()

def emit(label, value):
    print(
        "STAGE 8.1 MEASUREMENT: " + label + " " +
        json.dumps(value, default=str, separators=(",", ":")),
        flush=True,
    )

def fetch(cur, sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def one(cur, sql):
    data = fetch(cur, sql)
    return data[0] if data else {}

def main():
    print(
        "STAGE 8.1 MEASUREMENT: START "
        "(read only; no writes; no sends; no trades)",
        flush=True,
    )

    if not DB:
        raise RuntimeError("SIGNALS2_DATABASE_URL is not configured")

    conn = psycopg2.connect(DB)
    conn.autocommit = False

    try:
        cur = conn.cursor()
        cur.execute("SET TRANSACTION READ ONLY")

        common = """
        FROM signals2_opportunities o
        LEFT JOIN signals2_outcomes x
          ON x.opportunity_id = o.opportunity_id
        WHERE o.symbol NOT LIKE 'SIGNALS2%%'
        """

        # Exact decision/state inventory first. This prevents us from
        # assuming historical rows use only today's labels.
        emit("DECISION_INVENTORY", fetch(cur, f"""
            SELECT
                COALESCE(o.decision, 'NULL') AS decision,
                o.signal_sent,
                COUNT(*) AS rows,
                COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE) AS completed
            {common}
            GROUP BY o.decision, o.signal_sent
            ORDER BY COUNT(*) DESC
        """))

        # All observations: useful for memory/research, NOT signal win rate.
        emit("OBSERVATIONS", one(cur, f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE) AS completed,
                COUNT(*) FILTER (
                    WHERE x.outcome_complete IS TRUE
                      AND x.direction_correct_24h IS TRUE
                ) AS completed_correct_24h,
                AVG(x.return_24h_pct) FILTER (
                    WHERE x.outcome_complete IS TRUE
                ) AS completed_avg_return_24h_pct
            {common}
        """))

        # Rejected population.
        emit("REJECTED", one(cur, f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE) AS completed,
                COUNT(*) FILTER (
                    WHERE x.outcome_complete IS TRUE
                      AND x.direction_correct_24h IS TRUE
                ) AS completed_correct_24h,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE x.outcome_complete IS TRUE
                          AND x.direction_correct_24h IS TRUE
                    )
                    / NULLIF(
                        COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE),
                        0
                    ),
                    2
                ) AS completed_correct_24h_pct,
                AVG(x.return_24h_pct) FILTER (
                    WHERE x.outcome_complete IS TRUE
                ) AS completed_avg_return_24h_pct
            {common}
              AND UPPER(COALESCE(o.decision,'')) = 'REJECTED'
        """))

        # Candidate population: any row the stored decision says was
        # eligible/selected/sent. This is descriptive and does not invent
        # a state that is absent from the DB.
        emit("SIGNAL_CANDIDATES", one(cur, f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE) AS completed,
                COUNT(*) FILTER (
                    WHERE x.outcome_complete IS TRUE
                      AND x.direction_correct_24h IS TRUE
                ) AS completed_correct_24h,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE x.outcome_complete IS TRUE
                          AND x.direction_correct_24h IS TRUE
                    )
                    / NULLIF(
                        COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE),
                        0
                    ),
                    2
                ) AS completed_correct_24h_pct,
                AVG(o.final_confidence) AS avg_confidence,
                AVG(x.return_24h_pct) FILTER (
                    WHERE x.outcome_complete IS TRUE
                ) AS completed_avg_return_24h_pct
            {common}
              AND UPPER(COALESCE(o.decision,'')) IN
                  ('ELIGIBLE','SELECTED','SELECTED_NOT_SENT','SENT')
        """))

        # Durable sent flag is the strongest current evidence of an
        # actually sent Telegram signal.
        emit("SENT_SIGNALS", one(cur, f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE) AS completed,
                COUNT(*) FILTER (
                    WHERE x.outcome_complete IS TRUE
                      AND x.direction_correct_24h IS TRUE
                ) AS completed_correct_24h,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE x.outcome_complete IS TRUE
                          AND x.direction_correct_24h IS TRUE
                    )
                    / NULLIF(
                        COUNT(*) FILTER (WHERE x.outcome_complete IS TRUE),
                        0
                    ),
                    2
                ) AS completed_correct_24h_pct,
                AVG(o.final_confidence) AS avg_confidence,
                AVG(x.return_24h_pct) FILTER (
                    WHERE x.outcome_complete IS TRUE
                ) AS completed_avg_return_24h_pct
            {common}
              AND o.signal_sent IS TRUE
        """))

        # Confidence distribution for all observations versus candidates.
        emit("CONFIDENCE_POPULATIONS", fetch(cur, f"""
            SELECT population, band, COUNT(*) AS rows
            FROM (
                SELECT
                    'ALL_OBSERVATIONS' AS population,
                    CASE
                        WHEN o.final_confidence IS NULL THEN 'NULL'
                        WHEN o.final_confidence < 50 THEN '00-49.99'
                        WHEN o.final_confidence < 65 THEN '50-64.99'
                        WHEN o.final_confidence < 80 THEN '65-79.99'
                        ELSE '80-100'
                    END AS band
                {common}

                UNION ALL

                SELECT
                    'SIGNAL_CANDIDATES' AS population,
                    CASE
                        WHEN o.final_confidence IS NULL THEN 'NULL'
                        WHEN o.final_confidence < 50 THEN '00-49.99'
                        WHEN o.final_confidence < 65 THEN '50-64.99'
                        WHEN o.final_confidence < 80 THEN '65-79.99'
                        ELSE '80-100'
                    END AS band
                {common}
                  AND UPPER(COALESCE(o.decision,'')) IN
                      ('ELIGIBLE','SELECTED','SELECTED_NOT_SENT','SENT')
            ) q
            GROUP BY population, band
            ORDER BY population, band
        """))

        # Paired observation diagnostic. Same symbol + timestamp with both
        # directions indicates research observations, not two independent signals.
        emit("PAIRED_OBSERVATIONS", one(cur, """
            SELECT
                COUNT(*) AS symbol_time_groups,
                COUNT(*) FILTER (
                    WHERE has_long AND has_short
                ) AS paired_long_short_groups
            FROM (
                SELECT
                    symbol,
                    created_at,
                    BOOL_OR(direction='LONG') AS has_long,
                    BOOL_OR(direction='SHORT') AS has_short
                FROM signals2_opportunities
                WHERE symbol NOT LIKE 'SIGNALS2%'
                GROUP BY symbol, created_at
            ) p
        """))

        # Current >=80 population regardless of decision, useful to verify
        # whether threshold-qualified rows exist at all.
        emit("GE80_AUDIT", one(cur, f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE o.final_confidence >= 80
                ) AS ge80_rows,
                COUNT(*) FILTER (
                    WHERE o.final_confidence >= 80
                      AND UPPER(COALESCE(o.decision,'')) IN
                          ('ELIGIBLE','SELECTED','SELECTED_NOT_SENT','SENT')
                ) AS ge80_candidate_rows,
                COUNT(*) FILTER (
                    WHERE o.final_confidence >= 80
                      AND o.signal_sent IS TRUE
                ) AS ge80_sent_rows,
                COUNT(*) FILTER (
                    WHERE o.final_confidence >= 80
                      AND x.outcome_complete IS TRUE
                ) AS ge80_completed_rows
            {common}
        """))

        conn.rollback()

        print(
            "STAGE 8.1 MEASUREMENT: COMPLETE "
            "(read only; no writes; no sends; no trades)",
            flush=True,
        )

    finally:
        conn.close()

if __name__ == "__main__":
    main()
