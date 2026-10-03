"""
Brad's Signals Bot 2.0
Stage 8.2 - PostgreSQL metadata readback verifier

READ-ONLY DIAGNOSTIC:
- Connects to PostgreSQL
- SELECT only
- No INSERT / UPDATE / DELETE
- No Telegram
- No Bitget
- No OpenAI
- No trade
"""

import os
import psycopg2

PREFIX = "STAGE8_2 METADATA READBACK: "
EXPECTED_MODEL = "SIGNALS2_AI_INTEGRATED_V1"
EXPECTED_STRATEGY = "SIGNALS2_SCANNER_MEMORY_AI_V1"


def main():
    print(PREFIX + "START", flush=True)
    print(
        PREFIX + "READ ONLY; NO DB WRITE; NO TELEGRAM; NO BITGET; NO OPENAI; NO TRADE",
        flush=True,
    )

    database_url = os.environ.get("SIGNALS2_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("SIGNALS2_DATABASE_URL is missing")

    conn = None
    try:
        conn = psycopg2.connect(database_url)
        conn.set_session(readonly=True, autocommit=False)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    opportunity_id,
                    created_at,
                    model_version,
                    strategy_version
                FROM signals2_opportunities
                WHERE model_version = %s
                  AND strategy_version = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (EXPECTED_MODEL, EXPECTED_STRATEGY),
            )
            rows = cur.fetchall()

        if not rows:
            raise RuntimeError(
                "No PostgreSQL rows found with the expected Stage 8.2 metadata labels"
            )

        print(
            PREFIX
            + f"CHECK 1 PASS - found {len(rows)} recent row(s) with expected labels",
            flush=True,
        )

        for opportunity_id, created_at, model_version, strategy_version in rows:
            print(
                PREFIX
                + "ROW "
                + f"opportunity_id={opportunity_id}; "
                + f"created_at={created_at}; "
                + f"model_version={model_version}; "
                + f"strategy_version={strategy_version}",
                flush=True,
            )

        if any(row[2] != EXPECTED_MODEL for row in rows):
            raise RuntimeError("Unexpected model_version returned")
        if any(row[3] != EXPECTED_STRATEGY for row in rows):
            raise RuntimeError("Unexpected strategy_version returned")

        print(
            PREFIX + "CHECK 2 PASS - model_version readback verified",
            flush=True,
        )
        print(
            PREFIX + "CHECK 3 PASS - strategy_version readback verified",
            flush=True,
        )
        print(
            PREFIX + "PASS - Stage 8.2 PostgreSQL metadata readback verified",
            flush=True,
        )

    finally:
        if conn is not None:
            conn.rollback()
            conn.close()
        print(PREFIX + "CLEANUP PASS - read-only connection closed", flush=True)


if __name__ == "__main__":
    main()
