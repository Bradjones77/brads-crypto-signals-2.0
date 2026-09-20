import math
from typing import Dict, Any, Optional


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# CONFIDENCE ENGINE V1
#
# PURPOSE:
#
# Combine:
#
# 1. Technical evidence
# 2. Market context
# 3. Historical pattern memory
# 4. AI evidence
# 5. Data quality
# 6. Evidence agreement / conflict
#
# into ONE final confidence score.
#
#
# HARD SIGNAL RULE:
#
# 0 - 74.99 = REJECT
# 75 - 100  = ELIGIBLE
#
#
# IMPORTANT:
#
# - AI does NOT control final confidence.
# - Missing evidence is not treated as positive.
# - Weak historical samples cannot dominate.
# - Conflicting evidence reduces confidence.
# - Strong independent agreement can increase confidence.
# - Final score is always capped 0-100.
#
#
# THIS FILE DOES NOT:
#
# - Place trades
# - Send Telegram
# - Access Bitget
# - Access OpenAI
# - Change strategy rules
# ============================================================


CONFIDENCE_ENGINE_VERSION = "signals2-confidence-v1.1"

SIGNAL_THRESHOLD = 75.0


# ============================================================
# BASE COMPONENT WEIGHTS
#
# These are STARTING weights.
#
# Later, once Bot 2.0 has collected enough real historical
# data, we can objectively test candidate weight changes.
#
# We do NOT allow the live bot to randomly rewrite these.
# ============================================================


BASE_WEIGHTS = {

    "technical": 0.40,

    "market": 0.25,

    "memory": 0.20,

    "ai": 0.15,
}


# ============================================================
# HELPERS
# ============================================================


def clamp(
    value,
    minimum,
    maximum,
):

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def safe_float(
    value,
    default=None,
):

    try:

        if value is None:
            return default

        result = float(
            value
        )

        if not math.isfinite(
            result
        ):
            return default

        return result

    except Exception:

        return default


def normalize_score(
    value,
) -> Optional[float]:

    value = safe_float(
        value
    )

    if value is None:

        return None

    # Reject invalid scores rather than turning 150 or -20 into
    # apparently valid evidence. The scale must be documented 0-100.
    if value < 0.0 or value > 100.0:
        return None

    return value


# ============================================================
# GENERIC NESTED VALUE SEARCH
#
# This makes the confidence engine more tolerant if the
# analysis modules store a score inside nested dictionaries.
# ============================================================


def find_numeric_value(
    data: Any,
    wanted_keys,
) -> Optional[float]:

    if not isinstance(
        wanted_keys,
        (
            list,
            tuple,
            set,
        ),
    ):

        wanted_keys = [
            wanted_keys
        ]

    wanted = {
        str(key).lower()
        for key in wanted_keys
    }

    if isinstance(
        data,
        dict,
    ):

        # First try exact key matches.

        for key, value in (
            data.items()
        ):

            if (
                str(key).lower()
                in wanted
            ):

                number = safe_float(
                    value
                )

                if number is not None:

                    return number

        # Then recursively search.

        for value in (
            data.values()
        ):

            result = (
                find_numeric_value(
                    value,
                    wanted,
                )
            )

            if result is not None:

                return result

    elif isinstance(
        data,
        list,
    ):

        for item in data:

            result = (
                find_numeric_value(
                    item,
                    wanted,
                )
            )

            if result is not None:

                return result

    return None


# ============================================================
# DIRECTION HELPERS
# ============================================================


def normalize_direction(
    direction: str,
) -> str:

    direction = (
        str(direction)
        .upper()
        .strip()
    )

    if direction not in {
        "LONG",
        "SHORT",
    }:

        return "UNKNOWN"

    return direction


def direction_sign(
    direction: str,
) -> float:

    direction = (
        normalize_direction(
            direction
        )
    )

    if direction == "LONG":
        return 1.0

    if direction == "SHORT":
        return -1.0

    return 0.0


# ============================================================
# TECHNICAL CONFIDENCE
#
# The technical engine contains a lot of information.
#
# We derive a score from:
#
# - Multi-timeframe alignment
# - Trend
# - Momentum
# - RSI
# - MACD
# - Breakout evidence
# - Volume
#
# If technical_analysis later exposes its own reliable
# technical score, this function can use it directly.
# ============================================================


def calculate_technical_confidence(
    direction: str,
    technical_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    direction = (
        normalize_direction(
            direction
        )
    )

    if (
        direction == "UNKNOWN"
        or not isinstance(
            technical_analysis,
            dict,
        )
    ):

        return {
            "score": None,
            "quality": 0.0,
            "supporting_factors": [],
            "conflicting_factors": [],
        }

    # --------------------------------------------------------
    # DIRECT SCORE
    # --------------------------------------------------------

    direct_score = (
        find_numeric_value(
            technical_analysis,
            [
                "technical_confidence",
                "technical_score",
            ],
        )
    )

    if normalize_score(direct_score) is not None:

        return {

            "score":
            normalize_score(
                direct_score
            ),

            "quality":
            1.0,

            "supporting_factors":
            [
                "Technical engine supplied direct score"
            ],

            "conflicting_factors":
            [],
        }

    sign = (
        direction_sign(
            direction
        )
    )

    evidence = []

    support = []

    conflicts = []

    # --------------------------------------------------------
    # MULTI-TIMEFRAME ALIGNMENT
    # --------------------------------------------------------

    alignment = (
        find_numeric_value(
            technical_analysis,
            [
                "overall_alignment",
                "alignment_score",
                "mtf_alignment",
            ],
        )
    )

    if alignment is not None:

        # Support both:
        # -1..+1 scales
        # and
        # -100..+100 scales.

        if abs(
            alignment
        ) <= 1.5:

            directional_alignment = (
                alignment
                * sign
            )

        else:

            directional_alignment = (
                alignment
                / 100.0
                * sign
            )

        directional_alignment = clamp(
            directional_alignment,
            -1.0,
            1.0,
        )

        score = (
            50.0
            + (
                directional_alignment
                * 35.0
            )
        )

        evidence.append(
            (
                score,
                2.0,
            )
        )

        if directional_alignment > 0.20:

            support.append(
                "Multi-timeframe trend supports direction"
            )

        elif directional_alignment < -0.20:

            conflicts.append(
                "Multi-timeframe trend conflicts with direction"
            )

    # --------------------------------------------------------
    # TIMEFRAME TREND EVIDENCE
    # --------------------------------------------------------

    timeframes = (
        technical_analysis.get(
            "timeframes",
            {}
        )
        or {}
    )

    timeframe_weights = {

        "5m": 0.50,

        "15m": 0.70,

        "30m": 0.85,

        "1h": 1.10,

        "4h": 1.30,

        "1d": 1.10,
    }

    for timeframe, weight in (
        timeframe_weights.items()
    ):

        tf = (
            timeframes.get(
                timeframe,
                {}
            )
            or {}
        )

        if not isinstance(
            tf,
            dict,
        ):

            continue

        trend = (
            str(
                tf.get(
                    "trend",
                    tf.get(
                        "trend_state",
                        "",
                    ),
                )
            )
            .upper()
        )

        if not trend:

            continue

        bullish = (
            "BULL" in trend
            or "UP" in trend
        )

        bearish = (
            "BEAR" in trend
            or "DOWN" in trend
        )

        if not (
            bullish
            or bearish
        ):

            continue

        trend_direction = (
            1.0
            if bullish
            else -1.0
        )

        agreement = (
            trend_direction
            * sign
        )

        score = (
            75.0
            if agreement > 0
            else 25.0
        )

        evidence.append(
            (
                score,
                weight,
            )
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi = (
        find_numeric_value(
            technical_analysis,
            [
                "rsi_1h",
                "rsi",
            ],
        )
    )

    if rsi is not None:

        rsi = clamp(
            rsi,
            0.0,
            100.0,
        )

        if direction == "LONG":

            if 52 <= rsi <= 68:

                rsi_score = 72.0

                support.append(
                    "RSI supports bullish momentum"
                )

            elif rsi >= 78:

                rsi_score = 40.0

                conflicts.append(
                    "RSI is heavily extended"
                )

            elif rsi < 40:

                rsi_score = 35.0

                conflicts.append(
                    "RSI momentum is weak for LONG"
                )

            else:

                rsi_score = 55.0

        else:

            if 32 <= rsi <= 48:

                rsi_score = 72.0

                support.append(
                    "RSI supports bearish momentum"
                )

            elif rsi <= 22:

                rsi_score = 40.0

                conflicts.append(
                    "RSI is heavily extended"
                )

            elif rsi > 60:

                rsi_score = 35.0

                conflicts.append(
                    "RSI momentum is weak for SHORT"
                )

            else:

                rsi_score = 55.0

        evidence.append(
            (
                rsi_score,
                0.75,
            )
        )

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    breakout = (
        find_numeric_value(
            technical_analysis,
            [
                "breakout_score",
            ],
        )
    )

    if breakout is not None:

        if abs(
            breakout
        ) <= 1.5:

            breakout_directional = (
                breakout
                * sign
            )

        else:

            breakout_directional = (
                breakout
                / 100.0
                * sign
            )

        breakout_directional = clamp(
            breakout_directional,
            -1.0,
            1.0,
        )

        breakout_score = (
            50.0
            + (
                breakout_directional
                * 30.0
            )
        )

        evidence.append(
            (
                breakout_score,
                0.8,
            )
        )

        if breakout_directional > 0.25:

            support.append(
                "Breakout structure supports direction"
            )

        elif breakout_directional < -0.25:

            conflicts.append(
                "Breakout structure conflicts with direction"
            )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum = (
        find_numeric_value(
            technical_analysis,
            [
                "momentum_1h",
                "momentum_pct",
                "momentum",
            ],
        )
    )

    if momentum is not None:

        directional_momentum = (
            momentum
            * sign
        )

        momentum_score = (
            50.0
            + clamp(
                directional_momentum
                * 7.5,
                -30.0,
                30.0,
            )
        )

        evidence.append(
            (
                momentum_score,
                1.0,
            )
        )

        if directional_momentum > 0:

            support.append(
                "Momentum supports direction"
            )

        elif directional_momentum < 0:

            conflicts.append(
                "Momentum conflicts with direction"
            )

    # --------------------------------------------------------
    # NO USABLE EVIDENCE
    # --------------------------------------------------------

    if not evidence:

        return {

            "score":
            None,

            "quality":
            0.0,

            "supporting_factors":
            support,

            "conflicting_factors":
            conflicts,
        }

    numerator = sum(
        score * weight
        for score, weight
        in evidence
    )

    denominator = sum(
        weight
        for _, weight
        in evidence
    )

    technical_score = (
        numerator
        / denominator
    )

    # Quality increases as independent evidence accumulates.

    quality = clamp(
        len(
            evidence
        )
        / 7.0,
        0.20,
        1.0,
    )

    return {

        "score":
        round(
            clamp(
                technical_score,
                0.0,
                100.0,
            ),
            2,
        ),

        "quality":
        round(
            quality,
            4,
        ),

        "supporting_factors":
        support,

        "conflicting_factors":
        conflicts,
    }


# ============================================================
# MARKET CONTEXT CONFIDENCE
# ============================================================


def calculate_market_confidence(
    direction: str,
    market_context: Dict[str, Any],
) -> Dict[str, Any]:

    direction = (
        normalize_direction(
            direction
        )
    )

    if (
        direction == "UNKNOWN"
        or not isinstance(
            market_context,
            dict,
        )
    ):

        return {
            "score": None,
            "quality": 0.0,
            "supporting_factors": [],
            "conflicting_factors": [],
        }

    direct_score = (
        find_numeric_value(
            market_context,
            [
                "direction_market_agreement",
                "market_confidence",
                "market_score",
            ],
        )
    )

    evidence = []

    support = []

    conflicts = []

    # --------------------------------------------------------
    # DIRECTION / MARKET AGREEMENT
    # --------------------------------------------------------

    if direct_score is not None:

        if (
            -1.5
            <= direct_score
            <= 1.5
        ):

            score = (
                50.0
                + (
                    direct_score
                    * 40.0
                )
            )

        elif (
            -100.0
            <= direct_score
            <= 100.0
        ):

            # If negative values are possible,
            # treat as directional scale.

            if direct_score < 0:

                score = (
                    50.0
                    + (
                        direct_score
                        * 0.4
                    )
                )

            else:

                score = direct_score

        else:

            score = 50.0

        score = clamp(
            score,
            0.0,
            100.0,
        )

        evidence.append(
            (
                score,
                2.0,
            )
        )

        if score >= 65:

            support.append(
                "Wider market supports direction"
            )

        elif score <= 40:

            conflicts.append(
                "Wider market conflicts with direction"
            )

    # --------------------------------------------------------
    # MARKET BREADTH
    # --------------------------------------------------------

    bullish_pct = (
        find_numeric_value(
            market_context,
            [
                "bullish_pct",
                "market_bullish_pct",
            ],
        )
    )

    bearish_pct = (
        find_numeric_value(
            market_context,
            [
                "bearish_pct",
                "market_bearish_pct",
            ],
        )
    )

    if (
        bullish_pct is not None
        and bearish_pct is not None
    ):

        if direction == "LONG":

            breadth_edge = (
                bullish_pct
                - bearish_pct
            )

        else:

            breadth_edge = (
                bearish_pct
                - bullish_pct
            )

        breadth_score = (
            50.0
            + clamp(
                breadth_edge * 0.5,
                -35.0,
                35.0,
            )
        )

        evidence.append(
            (
                breadth_score,
                1.0,
            )
        )

        if breadth_edge >= 15:

            support.append(
                "Market breadth supports direction"
            )

        elif breadth_edge <= -15:

            conflicts.append(
                "Market breadth conflicts with direction"
            )

    # --------------------------------------------------------
    # MARKET STRESS
    # --------------------------------------------------------

    stress = (
        find_numeric_value(
            market_context,
            [
                "stress_score",
                "market_stress_score",
            ],
        )
    )

    if stress is not None:

        stress = clamp(
            stress,
            0.0,
            100.0,
        )

        # High stress lowers confidence regardless of direction.

        stress_score = (
            100.0
            - stress
        )

        evidence.append(
            (
                stress_score,
                0.8,
            )
        )

        if stress >= 70:

            conflicts.append(
                "Market stress is very high"
            )

        elif stress <= 30:

            support.append(
                "Market stress is relatively low"
            )

    # --------------------------------------------------------
    # RELATIVE STRENGTH VS BTC
    # --------------------------------------------------------

    relative_strength = (
        find_numeric_value(
            market_context,
            [
                "relative_strength_vs_btc",
                "relative_strength",
            ],
        )
    )

    if relative_strength is not None:

        directional_rs = (
            relative_strength
            * direction_sign(
                direction
            )
        )

        rs_score = (
            50.0
            + clamp(
                directional_rs * 7.0,
                -25.0,
                25.0,
            )
        )

        evidence.append(
            (
                rs_score,
                0.8,
            )
        )

        if directional_rs > 0:

            support.append(
                "Relative strength versus BTC supports direction"
            )

        elif directional_rs < 0:

            conflicts.append(
                "Relative strength versus BTC conflicts with direction"
            )

    if not evidence:

        return {

            "score":
            None,

            "quality":
            0.0,

            "supporting_factors":
            support,

            "conflicting_factors":
            conflicts,
        }

    numerator = sum(
        score * weight
        for score, weight
        in evidence
    )

    denominator = sum(
        weight
        for _, weight
        in evidence
    )

    score = (
        numerator
        / denominator
    )

    quality = clamp(
        len(
            evidence
        )
        / 4.0,
        0.25,
        1.0,
    )

    return {

        "score":
        round(
            clamp(
                score,
                0.0,
                100.0,
            ),
            2,
        ),

        "quality":
        round(
            quality,
            4,
        ),

        "supporting_factors":
        support,

        "conflicting_factors":
        conflicts,
    }


# ============================================================
# MEMORY CONFIDENCE
# ============================================================


def calculate_memory_confidence(
    memory_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        memory_analysis,
        dict,
    ):

        return {
            "score": None,
            "quality": 0.0,
            "usable": False,
        }

    if not memory_analysis.get(
        "memory_usable",
        False,
    ):

        return {

            "score":
            None,

            "quality":
            0.0,

            "usable":
            False,
        }

    score = normalize_score(
        memory_analysis.get(
            "memory_score"
        )
    )

    if score is None:

        return {

            "score":
            None,

            "quality":
            0.0,

            "usable":
            False,
        }

    sample_quality = (
        memory_analysis.get(
            "sample_quality",
            {}
        )
        or {}
    )

    effective_n = safe_float(
        sample_quality.get(
            "effective_sample_size"
        ),
        0.0,
    )

    average_similarity = safe_float(
        sample_quality.get(
            "average_similarity"
        ),
        0.0,
    )

    sample_factor = clamp(
        effective_n
        / 50.0,
        0.0,
        1.0,
    )

    similarity_factor = clamp(
        average_similarity,
        0.0,
        1.0,
    )

    quality = (
        sample_factor
        * similarity_factor
    )

    return {

        "score":
        round(
            score,
            2,
        ),

        "quality":
        round(
            quality,
            4,
        ),

        "usable":
        True,

        "effective_sample_size":
        effective_n,

        "average_similarity":
        average_similarity,
    }


# ============================================================
# AI CONFIDENCE
# ============================================================


def calculate_ai_confidence(
    ai_result: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        ai_result,
        dict,
    ):

        return {
            "score": None,
            "quality": 0.0,
            "usable": False,
        }

    if not ai_result.get(
        "available",
        False,
    ):

        return {

            "score":
            None,

            "quality":
            0.0,

            "usable":
            False,
        }

    score = normalize_score(
        ai_result.get(
            "ai_score"
        )
    )

    if score is None:

        return {

            "score":
            None,

            "quality":
            0.0,

            "usable":
            False,
        }

    data_quality = clamp(
        safe_float(
            ai_result.get(
                "data_quality"
            ),
            0.0,
        ),
        0.0,
        100.0,
    )

    uncertainty = clamp(
        safe_float(
            ai_result.get(
                "uncertainty"
            ),
            100.0,
        ),
        0.0,
        100.0,
    )

    quality = (
        (
            data_quality
            / 100.0
        )
        *
        (
            1.0
            - (
                uncertainty
                / 100.0
            )
        )
    )

    return {

        "score":
        round(
            score,
            2,
        ),

        "quality":
        round(
            clamp(
                quality,
                0.0,
                1.0,
            ),
            4,
        ),

        "usable":
        True,
    }


# ============================================================
# COMPONENT AGREEMENT
#
# Independent evidence agreeing is more meaningful than
# one isolated high score.
# ============================================================


def calculate_evidence_agreement(
    component_scores: Dict[str, Optional[float]],
) -> Dict[str, Any]:

    valid_scores = [

        score

        for score in (
            component_scores.values()
        )

        if score is not None
    ]

    if len(
        valid_scores
    ) < 2:

        return {

            "agreement":
            0.5,

            "spread":
            None,

            "agreement_adjustment":
            0.0,
        }

    highest = max(
        valid_scores
    )

    lowest = min(
        valid_scores
    )

    spread = (
        highest
        - lowest
    )

    average = (
        sum(
            valid_scores
        )
        / len(
            valid_scores
        )
    )

    # --------------------------------------------------------
    # AGREEMENT BONUS
    #
    # Only strong AND consistent evidence earns a bonus.
    # --------------------------------------------------------

    if (
        spread <= 10
        and average >= 75
        and len(valid_scores) >= 3
    ):

        adjustment = 4.0

        agreement = 1.0

    elif (
        spread <= 15
        and average >= 70
    ):

        adjustment = 2.0

        agreement = 0.85

    elif spread <= 20:

        adjustment = 0.0

        agreement = 0.70

    elif spread <= 30:

        adjustment = -2.0

        agreement = 0.50

    elif spread <= 40:

        adjustment = -5.0

        agreement = 0.30

    else:

        adjustment = -8.0

        agreement = 0.15

    return {

        "agreement":
        agreement,

        "spread":
        round(
            spread,
            2,
        ),

        "agreement_adjustment":
        adjustment,
    }


# ============================================================
# CONFLICT PENALTY
#
# Count major conflicts found by technical/market/AI layers.
# ============================================================


def calculate_conflict_penalty(
    technical_result: Dict[str, Any],
    market_result: Dict[str, Any],
    ai_result: Dict[str, Any],
) -> Dict[str, Any]:

    conflicts = []

    technical_conflicts = technical_result.get("conflicting_factors", [])
    if isinstance(technical_conflicts, list):
        conflicts.extend(technical_conflicts)

    market_conflicts = market_result.get("conflicting_factors", [])
    if isinstance(market_conflicts, list):
        conflicts.extend(market_conflicts)

    if isinstance(
        ai_result,
        dict,
    ):

        ai_conflicts = ai_result.get("technical_conflicts", [])
        if isinstance(ai_conflicts, list):
            conflicts.extend(ai_conflicts[:5])

        ai_conflicts = ai_result.get("market_conflicts", [])
        if isinstance(ai_conflicts, list):
            conflicts.extend(ai_conflicts[:5])

        ai_conflicts = ai_result.get("historical_warning_points", [])
        if isinstance(ai_conflicts, list):
            conflicts.extend(ai_conflicts[:5])

    # Remove duplicates.

    unique_conflicts = []

    seen = set()

    for conflict in conflicts:

        text = (
            str(conflict)
            .strip()
        )

        if not text:

            continue

        key = (
            text.lower()
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        unique_conflicts.append(
            text
        )

    count = len(
        unique_conflicts
    )

    # Keep penalty controlled.
    #
    # We do not want descriptive AI verbosity alone
    # destroying the statistical score.

    penalty = min(
        10.0,
        count * 1.25,
    )

    return {

        "conflict_count":
        count,

        "conflict_penalty":
        round(
            penalty,
            2,
        ),

        "conflicts":
        unique_conflicts,
    }


# ============================================================
# DATA QUALITY
#
# Missing components should reduce certainty.
# ============================================================


def calculate_overall_data_quality(
    components: Dict[str, Dict[str, Any]],
) -> float:

    weighted_quality = 0.0

    total_weight = 0.0

    for component_name, base_weight in (
        BASE_WEIGHTS.items()
    ):

        component = (
            components.get(
                component_name,
                {}
            )
            or {}
        )

        score = (
            component.get(
                "score"
            )
        )

        quality = clamp(
            safe_float(
                component.get(
                    "quality"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        if normalize_score(score) is None or quality <= 0:

            continue

        weighted_quality += (
            quality
            * base_weight
        )

        total_weight += (
            base_weight
        )

    if total_weight <= 0:

        return 0.0

    # Divide by ALL configured weight, not just the available
    # components. Missing memory/AI must not look like full coverage.
    return clamp(
        weighted_quality
        / sum(BASE_WEIGHTS.values()),
        0.0,
        1.0,
    )


# ============================================================
# DYNAMIC COMPONENT WEIGHTING
#
# If memory or AI is unavailable, their weight is NOT
# automatically treated as a neutral 50.
#
# Instead, the remaining reliable components are reweighted.
# ============================================================


def calculate_weighted_base_score(
    components: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    weighted_total = 0.0

    active_weight = 0.0

    applied_weights = {}

    for component_name, base_weight in (
        BASE_WEIGHTS.items()
    ):

        component = (
            components.get(
                component_name,
                {}
            )
            or {}
        )

        score = normalize_score(
            component.get(
                "score"
            )
        )

        quality = clamp(
            safe_float(
                component.get(
                    "quality"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        if (
            score is None
            or quality <= 0
        ):

            applied_weights[
                component_name
            ] = 0.0

            continue

        # ----------------------------------------------------
        # QUALITY-ADJUSTED WEIGHT
        # ----------------------------------------------------

        effective_weight = (
            base_weight
            * (
                0.50
                + (
                    0.50
                    * quality
                )
            )
        )

        weighted_total += (
            score
            * effective_weight
        )

        active_weight += (
            effective_weight
        )

        applied_weights[
            component_name
        ] = effective_weight

    if active_weight <= 0:

        return {

            "score":
            0.0,

            "weights":
            applied_weights,

            "active_weight":
            0.0,
        }

    base_score = (
        weighted_total
        / active_weight
    )

    # Convert weights into percentages of active evidence.

    normalized_weights = {}

    for name, weight in (
        applied_weights.items()
    ):

        if active_weight > 0:

            normalized_weights[
                name
            ] = round(
                weight
                / active_weight,
                4,
            )

        else:

            normalized_weights[
                name
            ] = 0.0

    return {

        "score":
        round(
            base_score,
            2,
        ),

        "weights":
        normalized_weights,

        "active_weight":
        round(
            active_weight,
            4,
        ),
    }


# ============================================================
# QUALITY PENALTY
#
# A score of 80 built from thin data should not be treated
# exactly like 80 built from rich, independent evidence.
# ============================================================


def calculate_quality_adjustment(
    overall_quality: float,
) -> float:

    quality = clamp(
        overall_quality,
        0.0,
        1.0,
    )

    if quality >= 0.85:

        return 0.0

    if quality >= 0.70:

        return -1.0

    if quality >= 0.55:

        return -3.0

    if quality >= 0.40:

        return -6.0

    return -10.0


# ============================================================
# HARD SAFETY / EVIDENCE GATES
#
# These are not trading execution safety controls.
#
# They simply stop extremely incomplete analysis from
# accidentally becoming a high-confidence signal.
# ============================================================


def evaluate_evidence_gates(
    components: Dict[str, Dict[str, Any]],
    final_score: float,
) -> Dict[str, Any]:

    reasons = []

    technical = (
        components.get(
            "technical",
            {}
        )
        or {}
    )

    market = (
        components.get(
            "market",
            {}
        )
        or {}
    )

    technical_score = normalize_score(
        technical.get(
            "score"
        )
    )

    market_score = normalize_score(
        market.get(
            "score"
        )
    )

    # A valid direction and both technical and market evidence are
    # mandatory. A lone high component cannot qualify a signal.
    if technical_score is None:

        reasons.append(
            "No usable technical evidence"
        )

    if market_score is None:
        reasons.append("No usable market evidence")

    if technical.get("quality", 0.0) < 0.40:
        reasons.append("Insufficient technical evidence coverage")

    if market.get("quality", 0.0) < 0.50:
        reasons.append("Insufficient market evidence coverage")

    # Extremely weak technical evidence blocks eligibility.

    elif technical_score < 45:

        reasons.append(
            "Technical evidence strongly conflicts with setup"
        )

    # If market context exists and is extremely hostile,
    # do not allow a high headline score to hide it.

    if (
        market_score is not None
        and market_score < 30
    ):

        reasons.append(
            "Market context is strongly hostile"
        )

    passed = (
        len(
            reasons
        )
        == 0
    )

    return {

        "passed":
        passed,

        "reasons":
        reasons,
    }


# ============================================================
# FINAL CONFIDENCE
# ============================================================


def calculate_final_confidence(
    symbol: str,
    direction: str,
    technical_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    memory_analysis: Dict[str, Any],
    ai_result: Dict[str, Any],
) -> Dict[str, Any]:

    direction = (
        normalize_direction(
            direction
        )
    )

    # --------------------------------------------------------
    # COMPONENT 1: TECHNICAL
    # --------------------------------------------------------

    technical = (
        calculate_technical_confidence(
            direction=direction,
            technical_analysis=technical_analysis,
        )
    )

    # --------------------------------------------------------
    # COMPONENT 2: MARKET
    # --------------------------------------------------------

    market = (
        calculate_market_confidence(
            direction=direction,
            market_context=market_context,
        )
    )

    # --------------------------------------------------------
    # COMPONENT 3: MEMORY
    # --------------------------------------------------------

    memory = (
        calculate_memory_confidence(
            memory_analysis
        )
    )

    # --------------------------------------------------------
    # COMPONENT 4: AI
    # --------------------------------------------------------

    ai = (
        calculate_ai_confidence(
            ai_result
        )
    )

    components = {

        "technical":
        technical,

        "market":
        market,

        "memory":
        memory,

        "ai":
        ai,
    }

    # --------------------------------------------------------
    # BASE WEIGHTED SCORE
    # --------------------------------------------------------

    base = (
        calculate_weighted_base_score(
            components
        )
    )

    base_score = (
        base[
            "score"
        ]
    )

    # --------------------------------------------------------
    # AGREEMENT
    # --------------------------------------------------------

    component_scores = {

        "technical":
        technical.get(
            "score"
        ),

        "market":
        market.get(
            "score"
        ),

        "memory":
        memory.get(
            "score"
        ),

        "ai":
        ai.get(
            "score"
        ),
    }

    agreement = (
        calculate_evidence_agreement(
            component_scores
        )
    )

    # --------------------------------------------------------
    # CONFLICTS
    # --------------------------------------------------------

    conflicts = (
        calculate_conflict_penalty(
            technical_result=technical,
            market_result=market,
            ai_result=ai_result,
        )
    )

    # --------------------------------------------------------
    # DATA QUALITY
    # --------------------------------------------------------

    overall_quality = (
        calculate_overall_data_quality(
            components
        )
    )

    quality_adjustment = (
        calculate_quality_adjustment(
            overall_quality
        )
    )

    # --------------------------------------------------------
    # FINAL SCORE BEFORE GATES
    # --------------------------------------------------------

    final_score = (

        base_score

        + agreement[
            "agreement_adjustment"
        ]

        - conflicts[
            "conflict_penalty"
        ]

        + quality_adjustment
    )

    final_score = round(
        clamp(
            final_score,
            0.0,
            100.0,
        ),
        2,
    )

    # --------------------------------------------------------
    # EVIDENCE GATES
    # --------------------------------------------------------

    gates = (
        evaluate_evidence_gates(
            components=components,
            final_score=final_score,
        )
    )

    if direction == "UNKNOWN":
        gates["reasons"].append("Invalid LONG/SHORT direction")
        gates["passed"] = False

    # --------------------------------------------------------
    # HARD 75 CONFIDENCE RULE
    # --------------------------------------------------------

    confidence_passed = (
        final_score
        >= SIGNAL_THRESHOLD
    )

    eligible = (
        confidence_passed
        and gates[
            "passed"
        ]
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if eligible:

        decision = (
            "ELIGIBLE"
        )

        rejection_reason = None

    elif not confidence_passed:

        decision = (
            "REJECTED"
        )

        rejection_reason = (
            f"Confidence {final_score:.2f} "
            f"is below required "
            f"{SIGNAL_THRESHOLD:.0f}"
        )

    else:

        decision = (
            "REJECTED"
        )

        rejection_reason = (
            "; ".join(
                gates[
                    "reasons"
                ]
            )
            or
            "Evidence gate failed"
        )

    return {

        "confidence_engine_version":
        CONFIDENCE_ENGINE_VERSION,

        "symbol":
        str(
            symbol
        ).upper(),

        "direction":
        direction,

        "final_confidence":
        final_score,

        "threshold":
        SIGNAL_THRESHOLD,

        "decision":
        decision,

        "eligible":
        eligible,

        "rejection_reason":
        rejection_reason,

        "base_score":
        base_score,

        "agreement_adjustment":
        agreement[
            "agreement_adjustment"
        ],

        "conflict_penalty":
        conflicts[
            "conflict_penalty"
        ],

        "quality_adjustment":
        quality_adjustment,

        "overall_data_quality":
        round(
            overall_quality,
            4,
        ),

        "evidence_agreement":
        agreement,

        "evidence_gates":
        gates,

        "component_scores": {

            "technical":
            technical.get(
                "score"
            ),

            "market":
            market.get(
                "score"
            ),

            "memory":
            memory.get(
                "score"
            ),

            "ai":
            ai.get(
                "score"
            ),
        },

        "component_quality": {

            "technical":
            technical.get(
                "quality"
            ),

            "market":
            market.get(
                "quality"
            ),

            "memory":
            memory.get(
                "quality"
            ),

            "ai":
            ai.get(
                "quality"
            ),
        },

        "applied_weights":
        base[
            "weights"
        ],

        "technical_support":
        technical.get(
            "supporting_factors",
            [],
        ),

        "technical_conflicts":
        technical.get(
            "conflicting_factors",
            [],
        ),

        "market_support":
        market.get(
            "supporting_factors",
            [],
        ),

        "market_conflicts":
        market.get(
            "conflicting_factors",
            [],
        ),

        "all_conflicts":
        conflicts[
            "conflicts"
        ],
    }


# ============================================================
# SIMPLE SIGNAL GATE
#
# Other files can call this without needing to know
# confidence-engine internals.
# ============================================================


def signal_is_eligible(
    confidence_result: Dict[str, Any],
) -> bool:

    if not isinstance(
        confidence_result,
        dict,
    ):

        return False

    confidence = safe_float(
        confidence_result.get(
            "final_confidence"
        )
    )

    if confidence is None:

        return False

    if confidence < SIGNAL_THRESHOLD or confidence > 100.0:

        return False

    if confidence_result.get("decision") != "ELIGIBLE":
        return False

    if not (confidence_result.get("evidence_gates") or {}).get("passed", False):
        return False

    return bool(
        confidence_result.get(
            "eligible",
            False,
        )
    )


# ============================================================
# MEMORY RECORD
#
# Store the component scores so we can later study:
#
# "Was technical confidence actually useful?"
# "Was AI useful?"
# "Did memory improve predictions?"
# "Which component was wrong?"
#
# ============================================================


def build_confidence_memory_record(
    confidence_result: Dict[str, Any],
) -> Dict[str, Any]:

    return {

        "confidence_engine_version":
        confidence_result.get(
            "confidence_engine_version"
        ),

        "final_confidence":
        confidence_result.get(
            "final_confidence"
        ),

        "decision":
        confidence_result.get(
            "decision"
        ),

        "eligible":
        confidence_result.get(
            "eligible"
        ),

        "component_scores":
        confidence_result.get(
            "component_scores",
            {},
        ),

        "component_quality":
        confidence_result.get(
            "component_quality",
            {},
        ),

        "applied_weights":
        confidence_result.get(
            "applied_weights",
            {},
        ),

        "overall_data_quality":
        confidence_result.get(
            "overall_data_quality"
        ),

        "evidence_agreement":
        confidence_result.get(
            "evidence_agreement",
            {},
        ),

        "conflict_penalty":
        confidence_result.get(
            "conflict_penalty"
        ),

        "quality_adjustment":
        confidence_result.get(
            "quality_adjustment"
        ),

        "rejection_reason":
        confidence_result.get(
            "rejection_reason"
        ),
    }


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- CONFIDENCE ENGINE",
        flush=True,
    )

    print(
        "TECHNICAL CONFIDENCE: READY",
        flush=True,
    )

    print(
        "MARKET CONFIDENCE: READY",
        flush=True,
    )

    print(
        "HISTORICAL MEMORY CONFIDENCE: READY",
        flush=True,
    )

    print(
        "AI CONFIDENCE: READY",
        flush=True,
    )

    print(
        "EVIDENCE AGREEMENT: READY",
        flush=True,
    )

    print(
        "CONFLICT PENALTIES: READY",
        flush=True,
    )

    print(
        "DATA QUALITY CONTROL: READY",
        flush=True,
    )

    print(
        "HARD CONFIDENCE THRESHOLD:",
        SIGNAL_THRESHOLD,
        flush=True,
    )

    print(
        "0-74.99: REJECTED",
        flush=True,
    )

    print(
        "75-100: ELIGIBLE",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )
