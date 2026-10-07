import os
import math
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# FAST-MOVE V2 — READ-ONLY HISTORICAL RESEARCH DIAGNOSTIC
#
# PURPOSE
# - Compare the current long-horizon memory objective with
#   candidate FAST-MOVE objectives.
# - Report LONG and SHORT separately.
# - Use only completed historical outcomes.
# - Make NO database writes.
# - Make NO Telegram sends.
# - Make NO AI calls.
# - Place NO trades.
# - Change NO production files/settings.
#
# IMPORTANT
# This diagnostic compares OUTCOME OBJECTIVES. It does not claim
# that a new production scoring model is already validated.
# ============================================================


DATABASE_URL = os.getenv(
    "SIGNALS2_DATABASE_URL",
    "",
).strip()


HORIZONS = (
    "30s",
    "1m",
    "5m",
    "10m",
    "30m",
    "1h",
    "4h",
    "12h",
    "24h",
)


# ============================================================
# CURRENT V1 MEMORY PROFILE
# ============================================================

CURRENT_V1 = {
    "30s": 0.03,
    "1m": 0.05,
    "5m": 0.10,
    "10m": 0.12,
    "30m": 0.15,
    "1h": 0.18,
    "4h": 0.17,
    "12h": 0.10,
    "24h": 0.10,
}


# ============================================================
# FAST-MOVE CANDIDATE PROFILES
#
# We are TESTING these.
# We are not assuming any one of them is correct.
# ============================================================

FAST_BALANCED = {
    "30s": 0.04,
    "1m": 0.08,
    "5m": 0.20,
    "10m": 0.24,
    "30m": 0.24,
    "1h": 0.12,
    "4h": 0.05,
    "12h": 0.02,
    "24h": 0.01,
}


FAST_5_30 = {
    "30s": 0.02,
    "1m": 0.05,
    "5m": 0.22,
    "10m": 0.28,
    "30m": 0.28,
    "1h": 0.10,
    "4h": 0.03,
    "12h": 0.01,
    "24h": 0.01,
}


FAST_1_10 = {
    "30s": 0.05,
    "1m": 0.15,
    "5m": 0.35,
    "10m": 0.30,
    "30m": 0.10,
    "1h": 0.03,
    "4h": 0.01,
    "12h": 0.005,
    "24h": 0.005,
}


PROFILES = {
    "CURRENT_V1": CURRENT_V1,
    "FAST_BALANCED": FAST_BALANCED,
    "FAST_5_30": FAST_5_30,
    "FAST_1_10": FAST_1_10,
}


MIN_ROWS_PER_DIRECTION = 30


# ============================================================
# HELPERS
# ============================================================


def safe_float(value):

    try:

        if value is None:
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except Exception:

        return None


def weighted_mean(
    values,
    weights,
):

    pairs = [
        (value, weight)
        for value, weight in zip(
            values,
            weights,
        )
        if value is not None
        and weight > 0
    ]

    if not pairs:
        return None

    denominator = sum(
        weight
        for _, weight in pairs
    )

    if not denominator:
        return None

    return (
        sum(
            value * weight
            for value, weight in pairs
        )
        / denominator
    )


def fmt(
    value,
    digits=2,
):

    if value is None:
        return "N/A"

    return f"{value:.{digits}f}"


# ============================================================
# DATABASE
# ============================================================


def fetch_rows(conn):

    # Restrict this to real integrated observations
    # with completed outcomes.
    #
    # Synthetic diagnostic/test strategies are excluded.

    sql = """
        SELECT

            o.opportunity_id,
            o.created_at,
            o.symbol,

            UPPER(
                o.direction
            ) AS direction,

            o.final_confidence,
            o.technical_confidence,
            o.market_confidence,
            o.memory_confidence,

            r.return_30s_pct,
            r.return_1m_pct,
            r.return_5m_pct,
            r.return_10m_pct,
            r.return_30m_pct,
            r.return_1h_pct,
            r.return_4h_pct,
            r.return_12h_pct,
            r.return_24h_pct,

            r.direction_correct_30s,
            r.direction_correct_1m,
            r.direction_correct_5m,
            r.direction_correct_10m,
            r.direction_correct_30m,
            r.direction_correct_1h,
            r.direction_correct_4h,
            r.direction_correct_12h,
            r.direction_correct_24h

        FROM
            signals2_opportunities o

        INNER JOIN
            signals2_outcomes r

        ON
            r.opportunity_id
            =
            o.opportunity_id

        WHERE

            r.outcome_complete = TRUE

            AND UPPER(
                o.direction
            ) IN (
                'LONG',
                'SHORT'
            )

            AND COALESCE(
                o.strategy_version,
                ''
            ) NOT LIKE 'SIGNALS2%%TEST%%'

            AND COALESCE(
                o.strategy_version,
                ''
            ) NOT LIKE 'STEP%%'

        ORDER BY
            o.created_at ASC
    """

    with conn.cursor(
        cursor_factory=RealDictCursor
    ) as cur:

        cur.execute(
            sql
        )

        return [
            dict(row)
            for row in cur.fetchall()
        ]


# ============================================================
# PROFILE SCORING
# ============================================================


def row_profile_score(
    row,
    weights,
):

    scores = []
    used_weights = []

    for horizon, weight in (
        weights.items()
    ):

        correct = row.get(
            f"direction_correct_{horizon}"
        )

        return_value = safe_float(
            row.get(
                f"return_{horizon}_pct"
            )
        )

        if correct is None:
            continue

        # Directional correctness dominates.
        #
        # Return magnitude provides only a small
        # capped adjustment.
        #
        # This follows the basic philosophy already
        # used by the existing memory engine.

        score = (
            100.0
            if bool(correct)
            else 0.0
        )

        if return_value is not None:

            score += max(
                -10.0,
                min(
                    10.0,
                    return_value * 5.0,
                ),
            )

        score = max(
            0.0,
            min(
                100.0,
                score,
            ),
        )

        scores.append(
            score
        )

        used_weights.append(
            weight
        )

    return weighted_mean(
        scores,
        used_weights,
    )


def direction_accuracy(
    row,
    horizons,
):

    values = []

    for horizon in horizons:

        result = row.get(
            f"direction_correct_{horizon}"
        )

        if result is not None:

            values.append(
                1.0
                if bool(result)
                else 0.0
            )

    if not values:
        return None

    return (
        sum(values)
        / len(values)
    )


# ============================================================
# HORIZON REPORT
# ============================================================


def print_horizon_table(
    rows,
    direction,
):

    subset = [
        row
        for row in rows
        if row["direction"] == direction
    ]

    print(
        f"\n{direction} HORIZON RESULTS",
        flush=True,
    )

    print(
        "-" * 76,
        flush=True,
    )

    print(
        f"{'HORIZON':<8} "
        f"{'N':>7} "
        f"{'ACCURACY':>12} "
        f"{'AVG RETURN %':>16}",
        flush=True,
    )

    for horizon in HORIZONS:

        correct = []
        returns = []

        for row in subset:

            result = row.get(
                f"direction_correct_{horizon}"
            )

            return_value = safe_float(
                row.get(
                    f"return_{horizon}_pct"
                )
            )

            if result is not None:

                correct.append(
                    1.0
                    if bool(result)
                    else 0.0
                )

            if return_value is not None:

                returns.append(
                    return_value
                )

        accuracy = (
            (
                sum(correct)
                / len(correct)
            )
            * 100.0
            if correct
            else None
        )

        average_return = (
            sum(returns)
            / len(returns)
            if returns
            else None
        )

        print(
            f"{horizon:<8} "
            f"{len(correct):>7} "
            f"{fmt(accuracy):>11}% "
            f"{fmt(average_return, 4):>16}",
            flush=True,
        )


# ============================================================
# PROFILE SUMMARY
# ============================================================


def profile_summary(
    rows,
    direction,
    profile_name,
    weights,
):

    subset = [
        row
        for row in rows
        if row["direction"] == direction
    ]

    scores = [
        row_profile_score(
            row,
            weights,
        )
        for row in subset
    ]

    scores = [
        score
        for score in scores
        if score is not None
    ]

    short_horizon_accuracy = [

        direction_accuracy(
            row,
            (
                "1m",
                "5m",
                "10m",
                "30m",
            ),
        )

        for row in subset
    ]

    short_horizon_accuracy = [
        value
        for value in short_horizon_accuracy
        if value is not None
    ]

    if scores:

        sorted_scores = sorted(
            scores
        )

        median_score = (
            sorted_scores[
                len(sorted_scores) // 2
            ]
        )

    else:

        median_score = None

    return {

        "n":
        len(scores),

        "mean_score":
        (
            sum(scores)
            / len(scores)
        )
        if scores
        else None,

        "median_score":
        median_score,

        "score_ge_65":
        sum(
            1
            for score in scores
            if score >= 65.0
        ),

        "score_ge_80":
        sum(
            1
            for score in scores
            if score >= 80.0
        ),

        "fast_accuracy":
        (
            (
                sum(
                    short_horizon_accuracy
                )
                / len(
                    short_horizon_accuracy
                )
            )
            * 100.0
        )
        if short_horizon_accuracy
        else None,
    }


# ============================================================
# CHRONOLOGICAL HOLDOUT
# ============================================================


def chronological_holdout(
    rows,
):

    # Oldest 70% versus newest 30%.
    #
    # This is a descriptive sanity check.
    #
    # It is NOT a full strategy backtest because
    # the candidate profile itself is not yet the
    # production scoring logic.

    ordered = sorted(
        rows,
        key=lambda row: row["created_at"],
    )

    cut = int(
        len(ordered)
        * 0.70
    )

    return (
        ordered[:cut],
        ordered[cut:],
    )


# ============================================================
# MAIN
# ============================================================


def main():

    print(
        "=" * 76,
        flush=True,
    )

    print(
        "FAST-MOVE V2 HISTORICAL RESEARCH DIAGNOSTIC",
        flush=True,
    )

    print(
        "READ ONLY | NO AI | NO TELEGRAM | "
        "NO TRADES | NO PRODUCTION CHANGES",
        flush=True,
    )

    print(
        "=" * 76,
        flush=True,
    )

    if not DATABASE_URL:

        print(
            "FAIL: SIGNALS2_DATABASE_URL is missing.",
            flush=True,
        )

        return

    conn = None

    try:

        conn = psycopg2.connect(
            DATABASE_URL
        )

        conn.set_session(
            readonly=True,
            autocommit=False,
        )

        rows = fetch_rows(
            conn
        )

        print(
            f"Completed real rows read: "
            f"{len(rows)}",
            flush=True,
        )

        counts = defaultdict(
            int
        )

        for row in rows:

            counts[
                row["direction"]
            ] += 1

        print(
            f"LONG rows: "
            f"{counts['LONG']} "
            f"| SHORT rows: "
            f"{counts['SHORT']}",
            flush=True,
        )

        if (
            counts["LONG"]
            < MIN_ROWS_PER_DIRECTION
            or
            counts["SHORT"]
            < MIN_ROWS_PER_DIRECTION
        ):

            print(
                "STOP: not enough completed "
                "LONG/SHORT rows for useful comparison.",
                flush=True,
            )

            return

        # ----------------------------------------------------
        # RAW HORIZON RESULTS
        # ----------------------------------------------------

        print_horizon_table(
            rows,
            "LONG",
        )

        print_horizon_table(
            rows,
            "SHORT",
        )

        # ----------------------------------------------------
        # ALL DATA PROFILE COMPARISON
        # ----------------------------------------------------

        print(
            "\nPROFILE COMPARISON — "
            "ALL COMPLETED DATA",
            flush=True,
        )

        print(
            "-" * 104,
            flush=True,
        )

        print(
            f"{'PROFILE':<18} "
            f"{'DIR':<6} "
            f"{'N':>7} "
            f"{'MEAN':>9} "
            f"{'MEDIAN':>9} "
            f"{'>=65':>8} "
            f"{'>=80':>8} "
            f"{'1m-30m ACC':>13}",
            flush=True,
        )

        for name, weights in (
            PROFILES.items()
        ):

            for direction in (
                "LONG",
                "SHORT",
            ):

                summary = (
                    profile_summary(
                        rows,
                        direction,
                        name,
                        weights,
                    )
                )

                print(
                    f"{name:<18} "
                    f"{direction:<6} "
                    f"{summary['n']:>7} "
                    f"{fmt(summary['mean_score']):>9} "
                    f"{fmt(summary['median_score']):>9} "
                    f"{summary['score_ge_65']:>8} "
                    f"{summary['score_ge_80']:>8} "
                    f"{fmt(summary['fast_accuracy']):>12}%",
                    flush=True,
                )

        # ----------------------------------------------------
        # CHRONOLOGICAL HOLDOUT
        # ----------------------------------------------------

        train, holdout = (
            chronological_holdout(
                rows
            )
        )

        print(
            "\nNEWEST 30% CHRONOLOGICAL "
            "HOLDOUT — DESCRIPTIVE CHECK",
            flush=True,
        )

        print(
            "-" * 94,
            flush=True,
        )

        print(
            f"Older 70% rows: "
            f"{len(train)} "
            f"| Newest 30% rows: "
            f"{len(holdout)}",
            flush=True,
        )

        print(
            f"{'PROFILE':<18} "
            f"{'DIR':<6} "
            f"{'N':>7} "
            f"{'MEAN':>9} "
            f"{'>=65':>8} "
            f"{'>=80':>8}",
            flush=True,
        )

        for name, weights in (
            PROFILES.items()
        ):

            for direction in (
                "LONG",
                "SHORT",
            ):

                summary = (
                    profile_summary(
                        holdout,
                        direction,
                        name,
                        weights,
                    )
                )

                print(
                    f"{name:<18} "
                    f"{direction:<6} "
                    f"{summary['n']:>7} "
                    f"{fmt(summary['mean_score']):>9} "
                    f"{summary['score_ge_65']:>8} "
                    f"{summary['score_ge_80']:>8}",
                    flush=True,
                )

        # ----------------------------------------------------
        # IMPORTANT INTERPRETATION NOTES
        # ----------------------------------------------------

        print(
            "\nINTERPRETATION RULES",
            flush=True,
        )

        print(
            "- Do NOT pick a profile merely because "
            "it creates more >=65 or >=80 rows.",
            flush=True,
        )

        print(
            "- Look for LONG/SHORT balance plus "
            "stronger 1m-30m outcomes.",
            flush=True,
        )

        print(
            "- This compares historical outcome "
            "objectives, not live profitability.",
            flush=True,
        )

        print(
            "- Fees, slippage, funding, entries/exits "
            "and leverage are NOT modeled here.",
            flush=True,
        )

        print(
            "- No production strategy should be "
            "changed from this diagnostic alone.",
            flush=True,
        )

        print(
            "\nPASS: diagnostic completed read-only.",
            flush=True,
        )

    except Exception as exc:

        print(
            f"FAIL: {type(exc).__name__}",
            flush=True,
        )

    finally:

        if conn is not None:

            try:

                conn.rollback()
                conn.close()

            except Exception:

                pass


if __name__ == "__main__":
    main()
