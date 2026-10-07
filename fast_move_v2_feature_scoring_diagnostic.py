import os
import math
import statistics

import psycopg2
from psycopg2.extras import RealDictCursor


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# FAST-MOVE V2 — ACTUAL FEATURE SCORING DIAGNOSTIC
#
# READ ONLY:
# - no DB writes
# - no AI calls
# - no Telegram
# - no trades
# - no production changes
#
# PURPOSE:
# Score completed historical opportunities from the ACTUAL
# stored technical/market features using a candidate fast-move
# model, then check whether higher scores correspond to better
# 1m/5m/10m/30m outcomes.
#
# This is research, NOT a production strategy.
# ============================================================


DATABASE_URL = os.getenv(
    "SIGNALS2_DATABASE_URL",
    "",
).strip()


FAST_HORIZONS = (
    "1m",
    "5m",
    "10m",
    "30m",
)


TIMEFRAMES = (
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "1d",
)


# Lower timeframes dominate.
# Higher timeframes remain context only.

TF_WEIGHTS = {
    "5m": 1.50,
    "15m": 1.35,
    "30m": 1.10,
    "1h": 0.65,
    "4h": 0.30,
    "1d": 0.15,
}


# Candidate component weights.
# These are being TESTED.
# They are NOT production weights.

COMPONENT_WEIGHTS = {
    "trend": 0.22,
    "momentum": 0.24,
    "macd": 0.16,
    "breakout": 0.16,
    "rsi": 0.08,
    "volume": 0.07,
    "market": 0.07,
}


# ============================================================
# BASIC HELPERS
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


def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def first(
    data,
    keys,
):

    if not isinstance(
        data,
        dict,
    ):
        return None

    for key in keys:

        if (
            key in data
            and data.get(key) is not None
        ):

            return data.get(
                key
            )

    return None


def weighted(
    values,
    weights,
):

    pairs = [

        (
            value,
            weight,
        )

        for value, weight in zip(
            values,
            weights,
        )

        if (
            value is not None
            and weight > 0
        )
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
# TIMEFRAME HELPERS
# ============================================================


def timeframe_aliases(
    timeframe,
):

    if timeframe == "1h":

        return (
            "1h",
            "1H",
        )

    if timeframe == "4h":

        return (
            "4h",
            "4H",
        )

    if timeframe == "1d":

        return (
            "1d",
            "1D",
        )

    return (
        timeframe,
    )


def feature_value(
    features,
    timeframe,
    suffixes,
):

    if not isinstance(
        features,
        dict,
    ):
        return None

    for alias in timeframe_aliases(
        timeframe
    ):

        for suffix in suffixes:

            possible_keys = (

                f"{alias}_{suffix}",

                f"{suffix}_{alias}",

                f"{alias.lower()}_{suffix}",

                f"{suffix}_{alias.lower()}",
            )

            for key in possible_keys:

                if (
                    key in features
                    and features.get(key) is not None
                ):

                    return features.get(
                        key
                    )

    return None


# ============================================================
# TREND
# ============================================================


def trend_numeric(
    value,
):

    if value is None:
        return None

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):

        number = safe_float(
            value
        )

        if number is None:
            return None

        if abs(number) <= 1.5:

            return max(
                -1.0,
                min(
                    1.0,
                    number,
                ),
            )

        return max(
            -1.0,
            min(
                1.0,
                number / 100.0,
            ),
        )

    text = str(
        value
    ).upper()

    if "STRONG_BULL" in text:
        return 1.0

    if (
        "BULL" in text
        or text == "UP"
    ):
        return 0.65

    if "STRONG_BEAR" in text:
        return -1.0

    if (
        "BEAR" in text
        or text == "DOWN"
    ):
        return -0.65

    if (
        "NEUTRAL" in text
        or "MIXED" in text
        or "SIDE" in text
    ):
        return 0.0

    return None


def trend_score(
    features,
    direction,
):

    values = []
    weights = []

    direction_sign = (
        1.0
        if direction == "LONG"
        else -1.0
    )

    for timeframe, weight in (
        TF_WEIGHTS.items()
    ):

        raw = feature_value(
            features,
            timeframe,
            (
                "trend",
                "trend_score",
            ),
        )

        trend = trend_numeric(
            raw
        )

        if trend is None:
            continue

        score = clamp(
            50.0
            +
            (
                40.0
                * trend
                * direction_sign
            )
        )

        values.append(
            score
        )

        weights.append(
            weight
        )

    # MTF is deliberately kept light because it already
    # summarizes several of the same trend timeframes.

    mtf = safe_float(
        first(
            features,
            (
                "mtf_alignment",
                "alignment_score",
            ),
        )
    )

    if mtf is not None:

        if abs(mtf) > 1.5:
            mtf /= 100.0

        mtf = max(
            -1.0,
            min(
                1.0,
                mtf,
            ),
        )

        score = clamp(
            50.0
            +
            (
                20.0
                * mtf
                * direction_sign
            )
        )

        values.append(
            score
        )

        weights.append(
            0.35
        )

    return weighted(
        values,
        weights,
    )


# ============================================================
# SIGNED NUMERIC EVIDENCE
# ============================================================


def signed_score(
    raw,
    direction,
    scale,
):

    value = safe_float(
        raw
    )

    if value is None:
        return None

    direction_sign = (
        1.0
        if direction == "LONG"
        else -1.0
    )

    normalized = (
        value
        * direction_sign
    ) / max(
        scale,
        0.000000001,
    )

    normalized = max(
        -2.0,
        min(
            2.0,
            normalized,
        ),
    )

    return clamp(
        50.0
        +
        (
            25.0
            * normalized
        )
    )


# ============================================================
# MOMENTUM
# ============================================================


def momentum_score(
    features,
    direction,
):

    values = []
    weights = []

    for timeframe, timeframe_weight in (
        TF_WEIGHTS.items()
    ):

        settings = (

            (
                "momentum_3",
                1.0,
                0.50,
            ),

            (
                "momentum_6",
                0.8,
                0.80,
            ),

            (
                "momentum_acceleration",
                1.2,
                0.25,
            ),

            (
                "momentum",
                0.8,
                0.60,
            ),
        )

        for (
            suffix,
            local_weight,
            scale,
        ) in settings:

            raw = feature_value(
                features,
                timeframe,
                (
                    suffix,
                ),
            )

            score = signed_score(
                raw,
                direction,
                scale,
            )

            if score is None:
                continue

            values.append(
                score
            )

            weights.append(
                timeframe_weight
                * local_weight
            )

    return weighted(
        values,
        weights,
    )


# ============================================================
# MACD
# ============================================================


def macd_score(
    features,
    direction,
):

    values = []
    weights = []

    direction_sign = (
        1.0
        if direction == "LONG"
        else -1.0
    )

    for timeframe, timeframe_weight in (
        TF_WEIGHTS.items()
    ):

        histogram = feature_value(
            features,
            timeframe,
            (
                "macd_hist",
                "macd_histogram",
            ),
        )

        acceleration = feature_value(
            features,
            timeframe,
            (
                "macd_acceleration",
                "macd_histogram_acceleration",
            ),
        )

        for (
            raw,
            local_weight,
        ) in (

            (
                histogram,
                1.0,
            ),

            (
                acceleration,
                1.25,
            ),
        ):

            value = safe_float(
                raw
            )

            if value is None:
                continue

            if abs(value) < 0.000000000000001:

                score = 50.0

            elif (
                value
                * direction_sign
            ) > 0:

                score = 68.0

            else:

                score = 32.0

            values.append(
                score
            )

            weights.append(
                timeframe_weight
                * local_weight
            )

    return weighted(
        values,
        weights,
    )


# ============================================================
# BREAKOUT / BREAKDOWN
# ============================================================


def breakout_score(
    features,
    direction,
):

    values = []
    weights = []

    for timeframe, timeframe_weight in (
        TF_WEIGHTS.items()
    ):

        bullish = feature_value(
            features,
            timeframe,
            (
                "bull_breakout",
                "bullish_breakout",
            ),
        )

        bearish = feature_value(
            features,
            timeframe,
            (
                "bear_breakout",
                "bearish_breakout",
            ),
        )

        volume_confirmed = feature_value(
            features,
            timeframe,
            (
                "breakout_volume_confirmed",
                "volume_confirmation",
            ),
        )

        if (
            bullish is None
            and bearish is None
        ):
            continue

        if direction == "LONG":

            target = bullish
            opposite = bearish

        else:

            target = bearish
            opposite = bullish

        score = 50.0

        if bool(target):

            score = 78.0

            if bool(
                volume_confirmed
            ):

                score = 86.0

        elif bool(
            opposite
        ):

            score = 22.0

        values.append(
            score
        )

        weights.append(
            timeframe_weight
        )

    return weighted(
        values,
        weights,
    )


# ============================================================
# RSI
# ============================================================


def rsi_score(
    features,
    direction,
):

    values = []
    weights = []

    for timeframe, timeframe_weight in (
        TF_WEIGHTS.items()
    ):

        rsi = safe_float(
            feature_value(
                features,
                timeframe,
                (
                    "rsi",
                ),
            )
        )

        if rsi is None:
            continue

        if direction == "LONG":

            if (
                rsi >= 52
                and rsi <= 68
            ):

                score = 70.0

            elif rsi >= 78:

                score = 38.0

            elif rsi < 40:

                score = 35.0

            else:

                score = 52.0

        else:

            if (
                rsi >= 32
                and rsi <= 48
            ):

                score = 70.0

            elif rsi <= 22:

                score = 38.0

            elif rsi > 60:

                score = 35.0

            else:

                score = 52.0

        values.append(
            score
        )

        weights.append(
            timeframe_weight
        )

    return weighted(
        values,
        weights,
    )


# ============================================================
# VOLUME
# ============================================================


def volume_score(
    features,
):

    values = []
    weights = []

    for timeframe, timeframe_weight in (
        TF_WEIGHTS.items()
    ):

        ratio = safe_float(
            feature_value(
                features,
                timeframe,
                (
                    "volume_ratio",
                ),
            )
        )

        acceleration = safe_float(
            feature_value(
                features,
                timeframe,
                (
                    "volume_acceleration",
                ),
            )
        )

        local_scores = []

        if ratio is not None:

            local_scores.append(
                clamp(
                    50.0
                    +
                    (
                        ratio - 1.0
                    )
                    * 25.0
                )
            )

        if acceleration is not None:

            local_scores.append(
                clamp(
                    50.0
                    +
                    acceleration
                    * 20.0
                )
            )

        if local_scores:

            values.append(
                sum(
                    local_scores
                )
                / len(
                    local_scores
                )
            )

            weights.append(
                timeframe_weight
            )

    return weighted(
        values,
        weights,
    )


# ============================================================
# MARKET CONTEXT
# ============================================================


def market_score(
    market,
    direction,
):

    if not isinstance(
        market,
        dict,
    ):
        return None

    values = []
    weights = []

    direction_sign = (
        1.0
        if direction == "LONG"
        else -1.0
    )

    agreement = safe_float(
        first(
            market,
            (
                "direction_market_agreement",
                "market_agreement",
                "agreement_score",
                "combined_market_score",
            ),
        )
    )

    if agreement is not None:

        if abs(
            agreement
        ) > 1.5:

            agreement /= 100.0

        agreement = max(
            -1.0,
            min(
                1.0,
                agreement,
            ),
        )

        # Market context is intentionally lighter in V2.

        values.append(
            clamp(
                50.0
                +
                25.0
                * agreement
            )
        )

        weights.append(
            0.8
        )

    relative_strength = safe_float(
        first(
            market,
            (
                "relative_strength",
                "relative_strength_vs_btc",
                "coin_relative_strength",
            ),
        )
    )

    if relative_strength is not None:

        if abs(
            relative_strength
        ) > 5:

            relative_strength /= 100.0

        adjustment = (
            relative_strength
            * direction_sign
            * 10.0
        )

        adjustment = max(
            -20.0,
            min(
                20.0,
                adjustment,
            ),
        )

        values.append(
            clamp(
                50.0
                + adjustment
            )
        )

        weights.append(
            1.0
        )

    bullish = safe_float(
        first(
            market,
            (
                "market_bullish_pct",
                "bullish_pct",
            ),
        )
    )

    bearish = safe_float(
        first(
            market,
            (
                "market_bearish_pct",
                "bearish_pct",
            ),
        )
    )

    if (
        bullish is not None
        and bearish is not None
    ):

        if max(
            abs(bullish),
            abs(bearish),
        ) <= 1.0:

            bullish *= 100.0
            bearish *= 100.0

        difference = (
            bullish
            - bearish
        ) * direction_sign

        values.append(
            clamp(
                50.0
                +
                difference
                * 0.20
            )
        )

        weights.append(
            0.35
        )

    return weighted(
        values,
        weights,
    )


# ============================================================
# COMPLETE FAST-MOVE SCORE
# ============================================================


def fast_score(
    row,
):

    direction = row[
        "direction"
    ]

    technical = (
        row.get(
            "technical_features"
        )
        or {}
    )

    market = (
        row.get(
            "market_features"
        )
        or {}
    )

    components = {

        "trend":
        trend_score(
            technical,
            direction,
        ),

        "momentum":
        momentum_score(
            technical,
            direction,
        ),

        "macd":
        macd_score(
            technical,
            direction,
        ),

        "breakout":
        breakout_score(
            technical,
            direction,
        ),

        "rsi":
        rsi_score(
            technical,
            direction,
        ),

        "volume":
        volume_score(
            technical,
        ),

        "market":
        market_score(
            market,
            direction,
        ),
    }

    values = []
    weights = []

    coverage = 0.0

    for (
        name,
        component_weight,
    ) in COMPONENT_WEIGHTS.items():

        value = components.get(
            name
        )

        if value is None:
            continue

        values.append(
            value
        )

        weights.append(
            component_weight
        )

        coverage += (
            component_weight
        )

    score = weighted(
        values,
        weights,
    )

    return (
        score,
        coverage,
        components,
    )


# ============================================================
# DATABASE
# ============================================================


def fetch_rows(
    connection,
):

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

            o.technical_features,
            o.market_features,
            o.combined_features,

            r.return_1m_pct,
            r.return_5m_pct,
            r.return_10m_pct,
            r.return_30m_pct,

            r.direction_correct_1m,
            r.direction_correct_5m,
            r.direction_correct_10m,
            r.direction_correct_30m

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
            ) NOT LIKE
                'SIGNALS2%%TEST%%'

            AND COALESCE(
                o.strategy_version,
                ''
            ) NOT LIKE
                'STEP%%'

        ORDER BY
            o.created_at ASC
    """

    with connection.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:

        cursor.execute(
            sql
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


# ============================================================
# OUTCOME ANALYSIS
# ============================================================


def outcome_accuracy(
    rows,
):

    correct_values = []
    returns = []

    for row in rows:

        for horizon in FAST_HORIZONS:

            correct = row.get(
                f"direction_correct_{horizon}"
            )

            return_value = safe_float(
                row.get(
                    f"return_{horizon}_pct"
                )
            )

            if correct is not None:

                correct_values.append(
                    1.0
                    if bool(correct)
                    else 0.0
                )

            if return_value is not None:

                returns.append(
                    return_value
                )

    accuracy = (

        (
            sum(
                correct_values
            )
            /
            len(
                correct_values
            )
        )
        * 100.0

        if correct_values

        else None
    )

    average_return = (

        sum(
            returns
        )
        /
        len(
            returns
        )

        if returns

        else None
    )

    return (
        accuracy,
        average_return,
    )


def print_bucket(
    label,
    rows,
):

    accuracy, average_return = (
        outcome_accuracy(
            rows
        )
    )

    print(
        f"{label:<20} "
        f"N={len(rows):>5} "
        f"fast_acc={fmt(accuracy)}% "
        f"avg_dir_return={fmt(average_return, 4)}%",
        flush=True,
    )


# ============================================================
# MAIN
# ============================================================


def main():

    print(
        "=" * 78,
        flush=True,
    )

    print(
        "FAST-MOVE V2 ACTUAL FEATURE SCORING DIAGNOSTIC",
        flush=True,
    )

    print(
        "READ ONLY | NO AI | NO TELEGRAM | "
        "NO TRADES | NO PRODUCTION CHANGES",
        flush=True,
    )

    print(
        "=" * 78,
        flush=True,
    )

    if not DATABASE_URL:

        print(
            "FAIL: SIGNALS2_DATABASE_URL missing.",
            flush=True,
        )

        return

    connection = None

    try:

        connection = psycopg2.connect(
            DATABASE_URL
        )

        connection.set_session(
            readonly=True,
            autocommit=False,
        )

        rows = fetch_rows(
            connection
        )

        scored_rows = []

        for row in rows:

            (
                score,
                coverage,
                components,
            ) = fast_score(
                row
            )

            if score is None:
                continue

            row[
                "_fast_score"
            ] = score

            row[
                "_coverage"
            ] = coverage

            row[
                "_components"
            ] = components

            scored_rows.append(
                row
            )

        print(
            f"Completed rows read: "
            f"{len(rows)}",
            flush=True,
        )

        print(
            f"Rows with FAST-MOVE score: "
            f"{len(scored_rows)}",
            flush=True,
        )

        # ----------------------------------------------------
        # SCORE DISTRIBUTION
        # ----------------------------------------------------

        for direction in (
            "LONG",
            "SHORT",
        ):

            subset = [

                row

                for row in scored_rows

                if row[
                    "direction"
                ] == direction
            ]

            if not subset:
                continue

            scores = [

                row[
                    "_fast_score"
                ]

                for row in subset
            ]

            coverages = [

                row[
                    "_coverage"
                ]

                for row in subset
            ]

            print(
                f"{direction}: "
                f"n={len(subset)} "
                f"mean_score="
                f"{fmt(statistics.mean(scores))} "
                f"median="
                f"{fmt(statistics.median(scores))} "
                f"mean_coverage="
                f"{fmt(statistics.mean(coverages) * 100)}%",
                flush=True,
            )

        # ----------------------------------------------------
        # SCORE BUCKETS
        # ----------------------------------------------------

        print(
            "\nSCORE BUCKET OUTCOMES — ALL DATA",
            flush=True,
        )

        print(
            "-" * 78,
            flush=True,
        )

        buckets = (
            (
                0,
                50,
            ),
            (
                50,
                60,
            ),
            (
                60,
                65,
            ),
            (
                65,
                70,
            ),
            (
                70,
                80,
            ),
            (
                80,
                101,
            ),
        )

        for direction in (
            "LONG",
            "SHORT",
        ):

            print(
                f"\n{direction}",
                flush=True,
            )

            subset = [

                row

                for row in scored_rows

                if row[
                    "direction"
                ] == direction
            ]

            for (
                lower,
                upper,
            ) in buckets:

                bucket = [

                    row

                    for row in subset

                    if (
                        row[
                            "_fast_score"
                        ]
                        >= lower

                        and

                        row[
                            "_fast_score"
                        ]
                        < upper
                    )
                ]

                print_bucket(
                    (
                        f"score "
                        f"{lower}-"
                        f"{upper - 0.01:.2f}"
                    ),
                    bucket,
                )

        # ----------------------------------------------------
        # TOP SCORES
        # ----------------------------------------------------

        print(
            "\nTOP-SCORE COMPARISON — ALL DATA",
            flush=True,
        )

        print(
            "-" * 78,
            flush=True,
        )

        for direction in (
            "LONG",
            "SHORT",
        ):

            subset = sorted(

                [

                    row

                    for row in scored_rows

                    if row[
                        "direction"
                    ] == direction
                ],

                key=lambda row:
                    row[
                        "_fast_score"
                    ],

                reverse=True,
            )

            print(
                f"\n{direction}",
                flush=True,
            )

            for percentage in (
                10,
                20,
                30,
            ):

                number = max(
                    1,
                    int(
                        len(subset)
                        * percentage
                        / 100.0
                    ),
                )

                print_bucket(
                    f"top {percentage}%",
                    subset[
                        :number
                    ],
                )

        # ----------------------------------------------------
        # CHRONOLOGICAL HOLDOUT
        # ----------------------------------------------------

        ordered = sorted(

            scored_rows,

            key=lambda row:
                row[
                    "created_at"
                ],
        )

        cut = int(
            len(ordered)
            * 0.70
        )

        holdout = ordered[
            cut:
        ]

        print(
            "\nNEWEST 30% CHRONOLOGICAL HOLDOUT",
            flush=True,
        )

        print(
            "-" * 78,
            flush=True,
        )

        print(
            f"Holdout rows: "
            f"{len(holdout)}",
            flush=True,
        )

        for direction in (
            "LONG",
            "SHORT",
        ):

            subset = [

                row

                for row in holdout

                if row[
                    "direction"
                ] == direction
            ]

            print(
                f"\n{direction}",
                flush=True,
            )

            for threshold in (
                60,
                65,
                70,
                80,
            ):

                selected = [

                    row

                    for row in subset

                    if row[
                        "_fast_score"
                    ] >= threshold
                ]

                print_bucket(
                    f"score >= {threshold}",
                    selected,
                )

        # ----------------------------------------------------
        # FEATURE COVERAGE
        # ----------------------------------------------------

        print(
            "\nCOMPONENT COVERAGE",
            flush=True,
        )

        print(
            "-" * 78,
            flush=True,
        )

        for name in (
            COMPONENT_WEIGHTS
        ):

            available = sum(

                1

                for row in scored_rows

                if row[
                    "_components"
                ].get(
                    name
                ) is not None
            )

            percentage = (

                (
                    available
                    /
                    len(
                        scored_rows
                    )
                )
                * 100.0

                if scored_rows

                else 0.0
            )

            print(
                f"{name:<12} "
                f"{available:>6}/"
                f"{len(scored_rows):<6} "
                f"{percentage:>6.2f}%",
                flush=True,
            )

        # ----------------------------------------------------
        # SAFETY / INTERPRETATION
        # ----------------------------------------------------

        print(
            "\nIMPORTANT",
            flush=True,
        )

        print(
            "- This tests candidate scoring against "
            "stored historical features.",
            flush=True,
        )

        print(
            "- It does NOT model fees, slippage, funding, "
            "leverage, entries or exits.",
            flush=True,
        )

        print(
            "- Paired LONG/SHORT observations are not "
            "independent trades.",
            flush=True,
        )

        print(
            "- Do NOT deploy these weights from this "
            "diagnostic alone.",
            flush=True,
        )

        print(
            "\nPASS: FAST-MOVE V2 feature diagnostic "
            "completed read-only.",
            flush=True,
        )

    except Exception as error:

        print(
            f"FAIL: "
            f"{type(error).__name__}: "
            f"{error}",
            flush=True,
        )

    finally:

        if connection is not None:

            try:

                connection.rollback()
                connection.close()

            except Exception:

                pass


if __name__ == "__main__":
    main()
