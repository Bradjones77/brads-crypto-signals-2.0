import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

from psycopg2.extras import RealDictCursor


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# HISTORICAL PATTERN MEMORY ENGINE
#
# PURPOSE:
#
# Compare a NEW opportunity with historical opportunities
# stored by memory_engine.py.
#
# It asks:
#
# "When the market looked similar to this before,
#  what happened afterwards?"
#
#
# IMPORTANT DESIGN RULES:
#
# - Uses completed historical outcomes only
# - Never uses future information from the current setup
# - Can compare same symbol AND other symbols
# - Gives more weight to highly similar setups
# - Gives more weight to recent evidence
# - Requires meaningful sample sizes
# - Measures uncertainty
# - Does NOT blindly assume recent wins = future wins
# - Does NOT place trades
# - Does NOT send Telegram
#
# ============================================================


PATTERN_ENGINE_VERSION = "2.0"


# ============================================================
# SETTINGS
# ============================================================


DEFAULT_LOOKBACK_DAYS = 180

DEFAULT_MAX_CANDIDATES = 5000

DEFAULT_TOP_MATCHES = 100

MIN_MATCHES_FOR_MEMORY_SCORE = 8

STRONG_SAMPLE_SIZE = 30

VERY_STRONG_SAMPLE_SIZE = 75


# Minimum similarity required for a historical setup
# to contribute to the final pattern analysis.

MIN_SIMILARITY = 0.45

# Require actual overlap; two coincidental indicators are not evidence.
MIN_MATCHED_FEATURES = 5
MIN_FEATURE_COVERAGE = 0.15


# ============================================================
# OUTCOME IMPORTANCE
#
# The bot is not only trying to predict the next minute.
#
# We therefore evaluate several future horizons.
#
# ============================================================


OUTCOME_WEIGHTS = {

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
# FEATURE IMPORTANCE
#
# These are starting weights.
#
# Later we can statistically test whether these weights
# should be changed.
#
# We do NOT allow the live bot to randomly rewrite them.
#
# ============================================================


FEATURE_WEIGHTS = {

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    "mtf_alignment": 2.0,

    "trend_score_5m": 0.8,

    "trend_score_15m": 1.0,

    "trend_score_30m": 1.1,

    "trend_score_1h": 1.4,

    "trend_score_4h": 1.6,

    "trend_score_1d": 1.3,

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    "rsi_5m": 0.6,

    "rsi_15m": 0.8,

    "rsi_30m": 0.9,

    "rsi_1h": 1.0,

    "rsi_4h": 1.1,

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    "macd_histogram_5m": 0.7,

    "macd_histogram_15m": 0.9,

    "macd_histogram_30m": 1.0,

    "macd_histogram_1h": 1.2,

    "macd_histogram_4h": 1.3,

    # --------------------------------------------------------
    # VOLATILITY
    # --------------------------------------------------------

    "atr_pct_5m": 0.6,

    "atr_pct_15m": 0.7,

    "atr_pct_30m": 0.8,

    "atr_pct_1h": 1.0,

    "atr_pct_4h": 1.0,

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    "momentum_5m": 0.9,

    "momentum_15m": 1.0,

    "momentum_30m": 1.1,

    "momentum_1h": 1.3,

    "momentum_4h": 1.3,

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    "volume_ratio_5m": 0.7,

    "volume_ratio_15m": 0.8,

    "volume_ratio_30m": 0.9,

    "volume_ratio_1h": 1.0,

    # --------------------------------------------------------
    # BREAKOUT / STRUCTURE
    # --------------------------------------------------------

    "breakout_score_5m": 0.8,

    "breakout_score_15m": 1.0,

    "breakout_score_30m": 1.1,

    "breakout_score_1h": 1.2,

    # --------------------------------------------------------
    # MARKET CONTEXT
    # --------------------------------------------------------

    "btc_alignment": 1.8,

    "eth_alignment": 1.2,

    # Broad market direction/alignment.
    "market_alignment": 1.6,

    "market_average_alignment": 1.3,

    "market_bullish_pct": 1.2,

    "market_bearish_pct": 1.2,

    # Broad volatility/stress conditions.
    "market_average_atr_pct": 1.0,

    "market_stress_score": 1.4,

    # These names intentionally match build_context_features()
    # in market_context.py.  The previous aliases did not match
    # the stored flattened feature names, so they were silently
    # excluded from pattern similarity.
    "market_agreement": 1.8,

    "relative_strength_btc": 1.4,
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

        number = float(
            value
        )

        if not math.isfinite(
            number
        ):

            return default

        return number

    except Exception:

        return default


def utc_now():

    return datetime.now(
        timezone.utc
    )


def ensure_datetime(
    value,
) -> Optional[datetime]:

    if value is None:

        return None

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:

            value = value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(
        value,
        str,
    ):

        try:

            result = (
                datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )

            if result.tzinfo is None:

                result = result.replace(
                    tzinfo=timezone.utc
                )

            return result

        except Exception:

            return None

    return None


# ============================================================
# FLATTEN NESTED FEATURES
# ============================================================


def flatten_dict(
    data: Dict[str, Any],
    prefix: str = "",
) -> Dict[str, Any]:

    result = {}

    if not isinstance(
        data,
        dict,
    ):

        return result

    for key, value in (
        data.items()
    ):

        key = str(
            key
        )

        new_key = (
            f"{prefix}_{key}"
            if prefix
            else key
        )

        if isinstance(
            value,
            dict,
        ):

            result.update(
                flatten_dict(
                    value,
                    new_key,
                )
            )

        else:

            result[
                new_key
            ] = value

    return result


# ============================================================
# FEATURE NAME NORMALIZATION
#
# Different analysis modules may use slightly different
# nested structures.
#
# This helper allows the matcher to find useful features
# without tightly coupling itself to one exact dictionary
# shape.
# ============================================================


def find_feature(
    features: Dict[str, Any],
    wanted_name: str,
):

    if wanted_name in features:

        return features[
            wanted_name
        ]

    wanted_lower = (
        wanted_name.lower()
    )

    for key, value in (
        features.items()
    ):

        key_lower = (
            str(key).lower()
        )

        if key_lower == wanted_lower:

            return value

        if key_lower.endswith(
            "_" + wanted_lower
        ):

            return value

    return None


# ============================================================
# NORMALIZE FEATURE VALUE
#
# We need different scales for RSI, ATR, momentum etc.
#
# The goal is:
#
# similarity = 1.0
#     nearly identical
#
# similarity = 0.0
#     very different
#
# ============================================================


def feature_scale(
    feature_name: str,
    a: float,
    b: float,
) -> float:

    name = (
        feature_name.lower()
    )

    if "rsi" in name:

        return 25.0

    if "alignment" in name:

        return 2.0

    if "trend_score" in name:

        return 2.0

    if "stress_score" in name:

        return 50.0

    if (
        "bullish_pct" in name
        or "bearish_pct" in name
    ):

        return 35.0

    if "volume_ratio" in name:

        return 1.5

    if "atr_pct" in name:

        return max(
            1.0,
            abs(a),
            abs(b),
        )

    if "momentum" in name:

        return max(
            2.0,
            abs(a) * 2.0,
            abs(b) * 2.0,
        )

    if "macd" in name:

        return max(
            0.000001,
            abs(a) * 2.0,
            abs(b) * 2.0,
        )

    if "breakout" in name:

        return 2.0

    if "relative_strength" in name:

        return max(
            2.0,
            abs(a) * 2.0,
            abs(b) * 2.0,
        )

    return max(
        1.0,
        abs(a),
        abs(b),
    )


# ============================================================
# NUMERIC FEATURE SIMILARITY
# ============================================================


def numeric_similarity(
    feature_name: str,
    current_value,
    historical_value,
) -> Optional[float]:

    a = safe_float(
        current_value
    )

    b = safe_float(
        historical_value
    )

    if (
        a is None
        or b is None
    ):

        return None

    scale = feature_scale(
        feature_name,
        a,
        b,
    )

    difference = (
        abs(
            a - b
        )
        / scale
    )

    similarity = (
        1.0
        - difference
    )

    return clamp(
        similarity,
        0.0,
        1.0,
    )


# ============================================================
# CATEGORICAL SIMILARITY
# ============================================================


def categorical_similarity(
    current_value,
    historical_value,
) -> Optional[float]:

    if (
        current_value is None
        or historical_value is None
    ):

        return None

    current = (
        str(current_value)
        .upper()
        .strip()
    )

    historical = (
        str(historical_value)
        .upper()
        .strip()
    )

    if not current or not historical:

        return None

    if current == historical:

        return 1.0

    return 0.0


# ============================================================
# BUILD COMPARISON FEATURES
# ============================================================


def prepare_features(
    technical_features: Dict[str, Any],
    market_features: Dict[str, Any],
) -> Dict[str, Any]:

    combined = {}

    technical_flat = (
        flatten_dict(
            technical_features or {}
        )
    )

    market_flat = (
        flatten_dict(
            market_features or {}
        )
    )

    combined.update(
        technical_flat
    )

    combined.update(
        market_flat
    )

    return combined


# ============================================================
# PATTERN SIMILARITY
# ============================================================


def calculate_pattern_similarity(
    current_features: Dict[str, Any],
    historical_features: Dict[str, Any],
) -> Dict[str, Any]:

    weighted_similarity = 0.0

    available_weight = 0.0

    matched_features = 0

    feature_details = {}

    for feature_name, weight in (
        FEATURE_WEIGHTS.items()
    ):

        current_value = (
            find_feature(
                current_features,
                feature_name,
            )
        )

        historical_value = (
            find_feature(
                historical_features,
                feature_name,
            )
        )

        similarity = (
            numeric_similarity(
                feature_name,
                current_value,
                historical_value,
            )
        )

        if similarity is None:

            continue

        weighted_similarity += (
            similarity
            * weight
        )

        available_weight += (
            weight
        )

        matched_features += 1

        feature_details[
            feature_name
        ] = round(
            similarity,
            4,
        )

    if available_weight <= 0:

        return {
            "similarity": 0.0,
            "matched_features": 0,
            "feature_coverage": 0.0,
            "feature_details": {},
        }

    raw_similarity = (
        weighted_similarity
        / available_weight
    )

    total_possible_features = (
        len(
            FEATURE_WEIGHTS
        )
    )

    coverage = (
        matched_features
        / total_possible_features
    )

    # --------------------------------------------------------
    # COVERAGE PENALTY
    #
    # A 95% match based on only two available indicators
    # should NOT be treated like a 95% match based on
    # thirty indicators.
    # --------------------------------------------------------

    coverage_factor = (
        0.50
        + (
            0.50
            * coverage
        )
    )

    adjusted_similarity = (
        raw_similarity
        * coverage_factor
    )

    return {

        "similarity":
        clamp(
            adjusted_similarity,
            0.0,
            1.0,
        ),

        "raw_similarity":
        clamp(
            raw_similarity,
            0.0,
            1.0,
        ),

        "matched_features":
        matched_features,

        "feature_coverage":
        coverage,

        "feature_details":
        feature_details,
    }


# ============================================================
# DIRECTION COMPATIBILITY
# ============================================================


def direction_compatibility(
    current_direction: str,
    historical_direction: str,
) -> float:

    current = (
        str(current_direction)
        .upper()
        .strip()
    )

    historical = (
        str(historical_direction)
        .upper()
        .strip()
    )

    if current == historical and current in ("LONG", "SHORT"):

        return 1.0

    # Returns are direction-adjusted for the HISTORICAL trade.
    # Mixing opposite directions without transforming their outcomes
    # would falsely turn an opposite-direction win into supporting evidence.
    return 0.0


# ============================================================
# SYMBOL COMPATIBILITY
# ============================================================


def symbol_compatibility(
    current_symbol: str,
    historical_symbol: str,
) -> float:

    current = (
        str(current_symbol)
        .upper()
        .strip()
    )

    historical = (
        str(historical_symbol)
        .upper()
        .strip()
    )

    if current == historical:

        return 1.0

    # Cross-symbol memory is useful.
    #
    # Example:
    # a SOL setup can resemble an ETH or AVAX setup.
    #
    # But same-symbol history receives slightly more weight.

    return 0.85


# ============================================================
# RECENCY WEIGHT
# ============================================================


def recency_weight(
    historical_time,
    current_time=None,
    half_life_days: float = 60.0,
) -> float:

    historical = (
        ensure_datetime(
            historical_time
        )
    )

    current = (
        ensure_datetime(
            current_time
        )
        if current_time is not None
        else utc_now()
    )

    if (
        historical is None
        or current is None
    ):

        return 0.5

    age_seconds = (
        current
        - historical
    ).total_seconds()

    if age_seconds < 0:

        # Future data must NEVER receive weight.

        return 0.0

    age_days = (
        age_seconds
        / 86400.0
    )

    if half_life_days <= 0:

        return 1.0

    weight = math.pow(
        0.5,
        age_days
        / half_life_days,
    )

    return clamp(
        weight,
        0.10,
        1.0,
    )


# ============================================================
# FETCH HISTORICAL CANDIDATES
#
# IMPORTANT:
#
# before_timestamp prevents look-ahead bias.
#
# The matcher is only allowed to see opportunities that
# occurred BEFORE the opportunity currently being analysed.
# ============================================================


def fetch_historical_candidates(
    conn,
    before_timestamp,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    limit: int = DEFAULT_MAX_CANDIDATES,
) -> List[Dict[str, Any]]:

    before_time = (
        ensure_datetime(
            before_timestamp
        )
    )

    if before_time is None:

        # Invalid timestamps must not silently turn a historical
        # backtest into a query against the current database.
        return []

    start_time = (
        before_time
        - timedelta(
            days=max(
                1,
                int(
                    lookback_days
                ),
            )
        )
    )

    safe_limit = max(
        1,
        min(
            int(limit),
            20000,
        ),
    )

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    cur.execute(
        """
        SELECT

            o.opportunity_id,
            o.created_at,
            o.symbol,
            o.direction,
            o.entry_price,

            o.final_confidence,

            o.technical_features,
            o.market_features,
            o.combined_features,

            o.decision,
            o.signal_sent,

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
            r.direction_correct_24h,

            r.max_favorable_excursion_pct,
            r.max_adverse_excursion_pct,

            r.early_reversal,
            r.early_continuation,

            r.outcome_complete

        FROM signals2_opportunities o

        INNER JOIN signals2_outcomes r

        ON
            o.opportunity_id
            =
            r.opportunity_id

        WHERE

            r.outcome_complete = TRUE

            AND o.created_at < %s

            AND o.created_at >= %s

            -- A 24h outcome must already have existed at the
            -- evaluation timestamp, not merely exist today.
            AND r.opportunity_time + INTERVAL '24 hours' <= %s
            AND r.last_updated <= %s

        ORDER BY
            o.created_at DESC

        LIMIT %s
        """,

        (
            before_time,
            start_time,
            before_time,
            before_time,
            safe_limit,
        ),
    )

    return [
        dict(row)
        for row in cur.fetchall()
    ]


# ============================================================
# BUILD HISTORICAL FEATURE SET
# ============================================================


def historical_feature_set(
    historical: Dict[str, Any],
) -> Dict[str, Any]:

    combined = (
        historical.get(
            "combined_features"
        )
    )

    if isinstance(
        combined,
        dict,
    ) and combined:

        return flatten_dict(
            combined
        )

    return prepare_features(

        historical.get(
            "technical_features",
            {},
        )
        or {},

        historical.get(
            "market_features",
            {},
        )
        or {},
    )


# ============================================================
# SCORE ONE HISTORICAL MATCH
# ============================================================


def score_historical_match(
    current_symbol: str,
    current_direction: str,
    current_features: Dict[str, Any],
    current_time,
    historical: Dict[str, Any],
) -> Optional[Dict[str, Any]]:

    historical_features = (
        historical_feature_set(
            historical
        )
    )

    similarity_result = (
        calculate_pattern_similarity(
            current_features,
            historical_features,
        )
    )

    similarity = (
        similarity_result[
            "similarity"
        ]
    )

    if (
        similarity < MIN_SIMILARITY
        or similarity_result["matched_features"] < MIN_MATCHED_FEATURES
        or similarity_result["feature_coverage"] < MIN_FEATURE_COVERAGE
    ):

        return None

    direction_factor = (
        direction_compatibility(
            current_direction,
            historical.get(
                "direction",
                "",
            ),
        )
    )

    symbol_factor = (
        symbol_compatibility(
            current_symbol,
            historical.get(
                "symbol",
                "",
            ),
        )
    )

    recent_factor = (
        recency_weight(
            historical.get(
                "created_at"
            ),
            current_time=current_time,
        )
    )

    final_match_weight = (
        similarity
        * direction_factor
        * symbol_factor
        * recent_factor
    )

    if final_match_weight <= 0:

        return None

    result = dict(
        historical
    )

    result[
        "pattern_similarity"
    ] = similarity

    result[
        "raw_pattern_similarity"
    ] = (
        similarity_result[
            "raw_similarity"
        ]
    )

    result[
        "feature_coverage"
    ] = (
        similarity_result[
            "feature_coverage"
        ]
    )

    result[
        "matched_features"
    ] = (
        similarity_result[
            "matched_features"
        ]
    )

    result[
        "recency_weight"
    ] = recent_factor

    result[
        "symbol_factor"
    ] = symbol_factor

    result[
        "direction_factor"
    ] = direction_factor

    result[
        "match_weight"
    ] = final_match_weight

    return result


# ============================================================
# FIND SIMILAR HISTORICAL PATTERNS
# ============================================================


def find_similar_patterns(
    conn,
    symbol: str,
    direction: str,
    technical_features: Dict[str, Any],
    market_features: Dict[str, Any],
    opportunity_time=None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    top_matches: int = DEFAULT_TOP_MATCHES,
) -> List[Dict[str, Any]]:

    if opportunity_time is None:

        opportunity_time = (
            utc_now()
        )

    current_features = (
        prepare_features(
            technical_features,
            market_features,
        )
    )

    candidates = (
        fetch_historical_candidates(
            conn=conn,
            before_timestamp=opportunity_time,
            lookback_days=lookback_days,
            limit=DEFAULT_MAX_CANDIDATES,
        )
    )

    matches = []

    for historical in candidates:

        match = (
            score_historical_match(
                current_symbol=symbol,
                current_direction=direction,
                current_features=current_features,
                current_time=opportunity_time,
                historical=historical,
            )
        )

        if match is not None:

            matches.append(
                match
            )

    matches.sort(
        key=lambda item:
        item.get(
            "match_weight",
            0.0,
        ),
        reverse=True,
    )

    safe_top = max(
        1,
        min(
            int(top_matches),
            500,
        ),
    )

    return matches[
        :safe_top
    ]


# ============================================================
# WEIGHTED AVERAGE
# ============================================================


def weighted_average(
    values: List[
        Tuple[
            float,
            float,
        ]
    ],
) -> Optional[float]:

    numerator = 0.0

    denominator = 0.0

    for value, weight in values:

        value = safe_float(
            value
        )

        weight = safe_float(
            weight
        )

        if (
            value is None
            or weight is None
            or weight <= 0
        ):

            continue

        numerator += (
            value
            * weight
        )

        denominator += weight

    if denominator <= 0:

        return None

    return (
        numerator
        / denominator
    )


# ============================================================
# EFFECTIVE SAMPLE SIZE
#
# If one historical match dominates all others,
# "20 matches" should not be treated like 20 equally useful
# independent observations.
# ============================================================


def effective_sample_size(
    weights: List[float],
) -> float:

    valid = [

        float(weight)

        for weight in weights

        if (
            safe_float(
                weight
            )
            is not None

            and float(
                weight
            ) > 0
        )
    ]

    if not valid:

        return 0.0

    total = sum(
        valid
    )

    squared = sum(
        weight * weight
        for weight in valid
    )

    if squared <= 0:

        return 0.0

    return (
        total * total
    ) / squared


# ============================================================
# HORIZON STATISTICS
# ============================================================


def analyze_horizon(
    matches: List[Dict[str, Any]],
    horizon: str,
) -> Dict[str, Any]:

    return_field = (
        f"return_{horizon}_pct"
    )

    correct_field = (
        f"direction_correct_{horizon}"
    )

    weighted_returns = []

    weighted_correct = []

    raw_returns = []

    weights = []

    for match in matches:

        outcome = safe_float(
            match.get(
                return_field
            )
        )

        weight = safe_float(
            match.get(
                "match_weight"
            ),
            0.0,
        )

        if (
            outcome is None
            or weight is None
            or weight <= 0
        ):

            continue

        weighted_returns.append(
            (
                outcome,
                weight,
            )
        )

        raw_returns.append(
            outcome
        )

        weights.append(
            weight
        )

        correct = (
            match.get(
                correct_field
            )
        )

        if correct is not None:

            weighted_correct.append(
                (
                    1.0
                    if bool(correct)
                    else 0.0,

                    weight,
                )
            )

    average_return = (
        weighted_average(
            weighted_returns
        )
    )

    win_rate = (
        weighted_average(
            weighted_correct
        )
    )

    effective_n = (
        effective_sample_size(
            weights
        )
    )

    if raw_returns:

        positive = sum(
            1
            for value in raw_returns
            if value > 0
        )

        negative = sum(
            1
            for value in raw_returns
            if value < 0
        )

    else:

        positive = 0
        negative = 0

    return {

        "horizon":
        horizon,

        "sample_size":
        len(
            raw_returns
        ),

        "effective_sample_size":
        round(
            effective_n,
            2,
        ),

        "weighted_average_return_pct":
        round(
            average_return,
            4,
        )
        if average_return is not None
        else None,

        "weighted_direction_accuracy":
        round(
            win_rate,
            4,
        )
        if win_rate is not None
        else None,

        "positive_examples":
        positive,

        "negative_examples":
        negative,
    }


# ============================================================
# MFE / MAE ANALYSIS
# ============================================================


def analyze_excursions(
    matches: List[Dict[str, Any]],
) -> Dict[str, Any]:

    mfe_values = []

    mae_values = []

    for match in matches:

        weight = safe_float(
            match.get(
                "match_weight"
            ),
            0.0,
        )

        if (
            weight is None
            or weight <= 0
        ):

            continue

        mfe = safe_float(
            match.get(
                "max_favorable_excursion_pct"
            )
        )

        mae = safe_float(
            match.get(
                "max_adverse_excursion_pct"
            )
        )

        if mfe is not None:

            mfe_values.append(
                (
                    mfe,
                    weight,
                )
            )

        if mae is not None:

            mae_values.append(
                (
                    mae,
                    weight,
                )
            )

    weighted_mfe = (
        weighted_average(
            mfe_values
        )
    )

    weighted_mae = (
        weighted_average(
            mae_values
        )
    )

    reward_risk = None

    if (
        weighted_mfe is not None
        and weighted_mae is not None
    ):

        if weighted_mae > 0:

            reward_risk = (
                weighted_mfe
                / weighted_mae
            )

        elif weighted_mfe > 0:

            reward_risk = 99.0

    return {

        "weighted_mfe_pct":
        round(
            weighted_mfe,
            4,
        )
        if weighted_mfe is not None
        else None,

        "weighted_mae_pct":
        round(
            weighted_mae,
            4,
        )
        if weighted_mae is not None
        else None,

        "historical_mfe_mae_ratio":
        round(
            reward_risk,
            4,
        )
        if reward_risk is not None
        else None,
    }


# ============================================================
# SAMPLE QUALITY
# ============================================================


def sample_quality(
    matches: List[Dict[str, Any]],
) -> Dict[str, Any]:

    count = len(
        matches
    )

    weights = [

        safe_float(
            match.get(
                "match_weight"
            ),
            0.0,
        )

        for match in matches
    ]

    effective_n = (
        effective_sample_size(
            weights
        )
    )

    average_similarity = (
        weighted_average(
            [

                (
                    safe_float(
                        match.get(
                            "pattern_similarity"
                        ),
                        0.0,
                    ),

                    max(
                        safe_float(
                            match.get(
                                "match_weight"
                            ),
                            0.0,
                        ),
                        0.000001,
                    ),
                )

                for match in matches
            ]
        )
    )

    if effective_n >= VERY_STRONG_SAMPLE_SIZE:

        quality = "VERY_STRONG"

    elif effective_n >= STRONG_SAMPLE_SIZE:

        quality = "STRONG"

    elif effective_n >= MIN_MATCHES_FOR_MEMORY_SCORE:

        quality = "USABLE"

    else:

        quality = "INSUFFICIENT"

    return {

        "raw_match_count":
        count,

        "effective_sample_size":
        round(
            effective_n,
            2,
        ),

        "average_similarity":
        round(
            average_similarity,
            4,
        )
        if average_similarity is not None
        else 0.0,

        "quality":
        quality,

        "memory_usable":
        (
            effective_n
            >= MIN_MATCHES_FOR_MEMORY_SCORE
        ),
    }


# ============================================================
# EARLY BEHAVIOUR STATISTICS
# ============================================================


def early_behaviour_statistics(
    matches: List[Dict[str, Any]],
) -> Dict[str, Any]:

    reversal_values = []

    continuation_values = []

    for match in matches:

        weight = safe_float(
            match.get(
                "match_weight"
            ),
            0.0,
        )

        if (
            weight is None
            or weight <= 0
        ):

            continue

        reversal = (
            match.get(
                "early_reversal"
            )
        )

        continuation = (
            match.get(
                "early_continuation"
            )
        )

        if reversal is not None:

            reversal_values.append(
                (
                    1.0
                    if bool(reversal)
                    else 0.0,

                    weight,
                )
            )

        if continuation is not None:

            continuation_values.append(
                (
                    1.0
                    if bool(continuation)
                    else 0.0,

                    weight,
                )
            )

    reversal_rate = (
        weighted_average(
            reversal_values
        )
    )

    continuation_rate = (
        weighted_average(
            continuation_values
        )
    )

    return {

        "historical_early_reversal_rate":
        round(
            reversal_rate,
            4,
        )
        if reversal_rate is not None
        else None,

        "historical_early_continuation_rate":
        round(
            continuation_rate,
            4,
        )
        if continuation_rate is not None
        else None,
    }


# ============================================================
# MEMORY EVIDENCE SCORE
#
# IMPORTANT:
#
# This is NOT the final bot confidence.
#
# It is simply a 0-100 description of what similar
# historical patterns suggest.
#
# The later confidence engine will combine:
#
# - technical analysis
# - market context
# - historical memory
# - AI analysis
# - uncertainty
#
# ============================================================


def calculate_memory_evidence_score(
    horizon_analysis: Dict[str, Dict[str, Any]],
    quality: Dict[str, Any],
) -> Optional[float]:

    if not quality.get(
        "memory_usable"
    ):

        return None

    weighted_score = 0.0

    total_weight = 0.0

    for horizon, importance in (
        OUTCOME_WEIGHTS.items()
    ):

        stats = (
            horizon_analysis.get(
                horizon,
                {}
            )
        )

        accuracy = safe_float(
            stats.get(
                "weighted_direction_accuracy"
            )
        )

        average_return = safe_float(
            stats.get(
                "weighted_average_return_pct"
            )
        )

        effective_n = safe_float(
            stats.get(
                "effective_sample_size"
            ),
            0.0,
        )

        if (
            accuracy is None
            or effective_n < MIN_MATCHES_FOR_MEMORY_SCORE
        ):

            continue

        # ----------------------------------------------------
        # ACCURACY COMPONENT
        # ----------------------------------------------------

        accuracy_score = (
            accuracy
            * 100.0
        )

        # ----------------------------------------------------
        # RETURN COMPONENT
        #
        # We only let return magnitude make a modest
        # adjustment. This prevents one huge historical move
        # from dominating the memory score.
        # ----------------------------------------------------

        return_adjustment = 0.0

        if average_return is not None:

            return_adjustment = clamp(
                average_return * 5.0,
                -10.0,
                10.0,
            )

        horizon_score = (
            accuracy_score
            + return_adjustment
        )

        horizon_score = clamp(
            horizon_score,
            0.0,
            100.0,
        )

        # ----------------------------------------------------
        # SAMPLE CONFIDENCE
        # ----------------------------------------------------

        sample_factor = clamp(
            effective_n
            / STRONG_SAMPLE_SIZE,
            0.25,
            1.0,
        )

        adjusted_importance = (
            importance
            * sample_factor
        )

        weighted_score += (
            horizon_score
            * adjusted_importance
        )

        total_weight += (
            adjusted_importance
        )

    if total_weight <= 0:

        return None

    score = (
        weighted_score
        / total_weight
    )

    # --------------------------------------------------------
    # SHRINK TOWARD NEUTRAL WHEN EVIDENCE IS LIMITED
    #
    # This is important.
    #
    # Example:
    # 8 similar historical examples all winning should NOT
    # immediately become "100 confidence".
    # --------------------------------------------------------

    effective_n = safe_float(
        quality.get(
            "effective_sample_size"
        ),
        0.0,
    )

    evidence_strength = clamp(
        effective_n
        / VERY_STRONG_SAMPLE_SIZE,
        0.10,
        1.0,
    )

    shrunk_score = (
        50.0
        + (
            (
                score
                - 50.0
            )
            * evidence_strength
        )
    )

    return round(
        clamp(
            shrunk_score,
            0.0,
            100.0,
        ),
        2,
    )


# ============================================================
# COMPLETE PATTERN MEMORY ANALYSIS
# ============================================================


def analyze_pattern_memory(
    conn,
    symbol: str,
    direction: str,
    technical_features: Dict[str, Any],
    market_features: Dict[str, Any],
    opportunity_time=None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    top_matches: int = DEFAULT_TOP_MATCHES,
) -> Dict[str, Any]:

    if opportunity_time is None:

        opportunity_time = (
            utc_now()
        )

    matches = (
        find_similar_patterns(
            conn=conn,
            symbol=symbol,
            direction=direction,
            technical_features=technical_features,
            market_features=market_features,
            opportunity_time=opportunity_time,
            lookback_days=lookback_days,
            top_matches=top_matches,
        )
    )

    quality = (
        sample_quality(
            matches
        )
    )

    horizon_analysis = {}

    for horizon in (
        OUTCOME_WEIGHTS.keys()
    ):

        horizon_analysis[
            horizon
        ] = analyze_horizon(
            matches,
            horizon,
        )

    excursions = (
        analyze_excursions(
            matches
        )
    )

    early_behaviour = (
        early_behaviour_statistics(
            matches
        )
    )

    memory_score = (
        calculate_memory_evidence_score(
            horizon_analysis,
            quality,
        )
    )

    # --------------------------------------------------------
    # SAME-SYMBOL / CROSS-SYMBOL INFORMATION
    # --------------------------------------------------------

    same_symbol_matches = sum(

        1

        for match in matches

        if (
            str(
                match.get(
                    "symbol",
                    "",
                )
            ).upper()

            ==

            str(
                symbol
            ).upper()
        )
    )

    same_direction_matches = sum(

        1

        for match in matches

        if (
            str(
                match.get(
                    "direction",
                    "",
                )
            ).upper()

            ==

            str(
                direction
            ).upper()
        )
    )

    # --------------------------------------------------------
    # TOP MATCH SUMMARY
    #
    # Keep the best examples available for the future AI
    # analyst so AI can see real historical evidence.
    # --------------------------------------------------------

    top_match_summary = []

    for match in matches[:10]:

        top_match_summary.append(
            {

                "opportunity_id":
                match.get(
                    "opportunity_id"
                ),

                "symbol":
                match.get(
                    "symbol"
                ),

                "direction":
                match.get(
                    "direction"
                ),

                "created_at":
                str(
                    match.get(
                        "created_at"
                    )
                ),

                "similarity":
                round(
                    safe_float(
                        match.get(
                            "pattern_similarity"
                        ),
                        0.0,
                    ),
                    4,
                ),

                "match_weight":
                round(
                    safe_float(
                        match.get(
                            "match_weight"
                        ),
                        0.0,
                    ),
                    4,
                ),

                "return_1m_pct":
                match.get(
                    "return_1m_pct"
                ),

                "return_5m_pct":
                match.get(
                    "return_5m_pct"
                ),

                "return_30m_pct":
                match.get(
                    "return_30m_pct"
                ),

                "return_1h_pct":
                match.get(
                    "return_1h_pct"
                ),

                "return_4h_pct":
                match.get(
                    "return_4h_pct"
                ),

                "return_24h_pct":
                match.get(
                    "return_24h_pct"
                ),

                "mfe_pct":
                match.get(
                    "max_favorable_excursion_pct"
                ),

                "mae_pct":
                match.get(
                    "max_adverse_excursion_pct"
                ),
            }
        )

    return {

        "pattern_engine_version":
        PATTERN_ENGINE_VERSION,

        "symbol":
        str(
            symbol
        ).upper(),

        "direction":
        str(
            direction
        ).upper(),

        "memory_score":
        memory_score,

        "memory_usable":
        quality.get(
            "memory_usable",
            False,
        ),

        "sample_quality":
        quality,

        "same_symbol_matches":
        same_symbol_matches,

        "cross_symbol_matches":
        max(
            0,
            len(matches)
            - same_symbol_matches,
        ),

        "same_direction_matches":
        same_direction_matches,

        "horizons":
        horizon_analysis,

        "excursions":
        excursions,

        "early_behaviour":
        early_behaviour,

        "top_historical_matches":
        top_match_summary,
    }


# ============================================================
# AI-FRIENDLY MEMORY SUMMARY
#
# Later the AI analyst can receive this compact summary
# instead of thousands of raw database rows.
# ============================================================


def build_ai_memory_summary(
    memory_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    if not memory_analysis:

        return {
            "memory_available":
            False,
        }

    quality = (
        memory_analysis.get(
            "sample_quality",
            {}
        )
        or {}
    )

    horizons = (
        memory_analysis.get(
            "horizons",
            {}
        )
        or {}
    )

    excursions = (
        memory_analysis.get(
            "excursions",
            {}
        )
        or {}
    )

    behaviour = (
        memory_analysis.get(
            "early_behaviour",
            {}
        )
        or {}
    )

    return {

        "memory_available":
        bool(
            memory_analysis.get(
                "memory_usable"
            )
        ),

        "memory_score":
        memory_analysis.get(
            "memory_score"
        ),

        "sample_quality":
        quality.get(
            "quality"
        ),

        "effective_sample_size":
        quality.get(
            "effective_sample_size"
        ),

        "average_pattern_similarity":
        quality.get(
            "average_similarity"
        ),

        "same_symbol_matches":
        memory_analysis.get(
            "same_symbol_matches"
        ),

        "cross_symbol_matches":
        memory_analysis.get(
            "cross_symbol_matches"
        ),

        "historical_1m":
        horizons.get(
            "1m"
        ),

        "historical_5m":
        horizons.get(
            "5m"
        ),

        "historical_10m":
        horizons.get(
            "10m"
        ),

        "historical_30m":
        horizons.get(
            "30m"
        ),

        "historical_1h":
        horizons.get(
            "1h"
        ),

        "historical_4h":
        horizons.get(
            "4h"
        ),

        "historical_12h":
        horizons.get(
            "12h"
        ),

        "historical_24h":
        horizons.get(
            "24h"
        ),

        "historical_mfe_pct":
        excursions.get(
            "weighted_mfe_pct"
        ),

        "historical_mae_pct":
        excursions.get(
            "weighted_mae_pct"
        ),

        "historical_mfe_mae_ratio":
        excursions.get(
            "historical_mfe_mae_ratio"
        ),

        "early_reversal_rate":
        behaviour.get(
            "historical_early_reversal_rate"
        ),

        "early_continuation_rate":
        behaviour.get(
            "historical_early_continuation_rate"
        ),

        "top_examples":
        memory_analysis.get(
            "top_historical_matches",
            [],
        ),
    }


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- HISTORICAL PATTERN MEMORY",
        flush=True,
    )

    print(
        "MULTI-FACTOR PATTERN MATCHING: READY",
        flush=True,
    )

    print(
        "SAME-SYMBOL MEMORY: READY",
        flush=True,
    )

    print(
        "CROSS-SYMBOL MEMORY: READY",
        flush=True,
    )

    print(
        "30S / 1M / 5M / 10M MEMORY: READY",
        flush=True,
    )

    print(
        "30M / 1H / 4H / 12H / 24H MEMORY: READY",
        flush=True,
    )

    print(
        "RECENCY WEIGHTING: READY",
        flush=True,
    )

    print(
        "SIMILARITY WEIGHTING: READY",
        flush=True,
    )

    print(
        "EFFECTIVE SAMPLE SIZE: READY",
        flush=True,
    )

    print(
        "UNCERTAINTY SHRINKAGE: READY",
        flush=True,
    )

    print(
        "LOOK-AHEAD PROTECTION: READY",
        flush=True,
    )

    print(
        "MFE / MAE PATTERN LEARNING: READY",
        flush=True,
    )

    print(
        "AI MEMORY SUMMARY: READY",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )
