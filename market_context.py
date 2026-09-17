import math
from typing import Dict, List, Any, Optional


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# MARKET CONTEXT + REGIME ENGINE
#
# PURPOSE:
# Understand the wider crypto market before judging
# an individual coin.
#
# THIS FILE:
# - DOES NOT PLACE TRADES
# - DOES NOT SEND TELEGRAM MESSAGES
# - DOES NOT USE API KEYS
# - DOES NOT MODIFY THE OLD BOT
# ============================================================


# ============================================================
# HELPERS
# ============================================================


def safe_float(value, default=None):

    try:
        value = float(value)

        if not math.isfinite(value):
            return default

        return value

    except Exception:
        return default


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(maximum, value)
    )


def pct_change(old_value, new_value):

    old_value = safe_float(old_value)
    new_value = safe_float(new_value)

    if (
        old_value is None
        or new_value is None
        or old_value == 0
    ):
        return None

    return (
        (new_value - old_value)
        / abs(old_value)
    ) * 100.0


def average(values):

    values = [
        safe_float(v)
        for v in values
    ]

    values = [
        v
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


# ============================================================
# TREND TO NUMERIC SCORE
# ============================================================


def trend_score(trend):

    mapping = {
        "STRONG_BULLISH": 1.0,
        "BULLISH": 0.60,
        "NEUTRAL": 0.0,
        "MIXED": 0.0,
        "BEARISH": -0.60,
        "STRONG_BEARISH": -1.0,
        "UNKNOWN": 0.0,
    }

    return mapping.get(
        str(trend),
        0.0,
    )


# ============================================================
# EXTRACT TIMEFRAME DATA
# ============================================================


def get_timeframe_analysis(
    analysis: Dict[str, Any],
    timeframe: str,
) -> Dict[str, Any]:

    return (
        analysis
        .get("timeframes", {})
        .get(timeframe, {})
        or {}
    )


def get_timeframe_trend(
    analysis: Dict[str, Any],
    timeframe: str,
) -> str:

    tf = get_timeframe_analysis(
        analysis,
        timeframe,
    )

    return (
        tf
        .get("trend", {})
        .get("trend", "UNKNOWN")
    )


def get_timeframe_momentum(
    analysis: Dict[str, Any],
    timeframe: str,
    key: str = "3_candle_pct",
):

    tf = get_timeframe_analysis(
        analysis,
        timeframe,
    )

    return (
        tf
        .get("momentum", {})
        .get(key)
    )


# ============================================================
# BTC / ETH CONTEXT
# ============================================================


def analyze_major_context(
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Builds a combined BTC + ETH market view.

    BTC gets slightly more weight because it
    generally has the strongest market influence.
    """

    btc_alignment = safe_float(
        btc_analysis
        .get("multi_timeframe", {})
        .get("alignment_score"),
        0.0,
    )

    eth_alignment = safe_float(
        eth_analysis
        .get("multi_timeframe", {})
        .get("alignment_score"),
        0.0,
    )

    combined_alignment = (
        btc_alignment * 0.60
        + eth_alignment * 0.40
    )

    combined_alignment = clamp(
        combined_alignment,
        -1.0,
        1.0,
    )

    btc_1h = get_timeframe_momentum(
        btc_analysis,
        "1H",
        "1_candle_pct",
    )

    eth_1h = get_timeframe_momentum(
        eth_analysis,
        "1H",
        "1_candle_pct",
    )

    btc_4h = get_timeframe_momentum(
        btc_analysis,
        "4H",
        "1_candle_pct",
    )

    eth_4h = get_timeframe_momentum(
        eth_analysis,
        "4H",
        "1_candle_pct",
    )

    average_1h = average([
        btc_1h,
        eth_1h,
    ])

    average_4h = average([
        btc_4h,
        eth_4h,
    ])

    if combined_alignment >= 0.65:
        regime = "STRONG_RISK_ON"

    elif combined_alignment >= 0.25:
        regime = "RISK_ON"

    elif combined_alignment <= -0.65:
        regime = "STRONG_RISK_OFF"

    elif combined_alignment <= -0.25:
        regime = "RISK_OFF"

    else:
        regime = "NEUTRAL"

    return {
        "regime":
        regime,

        "combined_alignment":
        combined_alignment,

        "btc_alignment":
        btc_alignment,

        "eth_alignment":
        eth_alignment,

        "btc_1h_momentum":
        btc_1h,

        "eth_1h_momentum":
        eth_1h,

        "average_1h_momentum":
        average_1h,

        "btc_4h_momentum":
        btc_4h,

        "eth_4h_momentum":
        eth_4h,

        "average_4h_momentum":
        average_4h,

        "btc_1h_trend":
        get_timeframe_trend(
            btc_analysis,
            "1H",
        ),

        "btc_4h_trend":
        get_timeframe_trend(
            btc_analysis,
            "4H",
        ),

        "eth_1h_trend":
        get_timeframe_trend(
            eth_analysis,
            "1H",
        ),

        "eth_4h_trend":
        get_timeframe_trend(
            eth_analysis,
            "4H",
        ),
    }


# ============================================================
# MARKET BREADTH
# ============================================================


def analyze_market_breadth(
    symbol_analyses: List[Dict[str, Any]],
) -> Dict[str, Any]:

    """
    Measures how much of the market is bullish
    or bearish.

    This prevents the bot from looking only at BTC.
    """

    bullish = 0
    bearish = 0
    neutral = 0

    alignment_scores = []

    strong_bullish = 0
    strong_bearish = 0

    for analysis in symbol_analyses or []:

        mtf = analysis.get(
            "multi_timeframe",
            {},
        )

        overall = mtf.get(
            "overall",
            "MIXED",
        )

        score = safe_float(
            mtf.get(
                "alignment_score"
            )
        )

        if score is not None:
            alignment_scores.append(
                score
            )

        if overall in (
            "STRONG_BULLISH",
            "BULLISH",
        ):

            bullish += 1

            if overall == "STRONG_BULLISH":
                strong_bullish += 1

        elif overall in (
            "STRONG_BEARISH",
            "BEARISH",
        ):

            bearish += 1

            if overall == "STRONG_BEARISH":
                strong_bearish += 1

        else:
            neutral += 1

    total = (
        bullish
        + bearish
        + neutral
    )

    if total == 0:

        return {
            "total_symbols":
            0,

            "bullish_pct":
            None,

            "bearish_pct":
            None,

            "neutral_pct":
            None,

            "average_alignment":
            None,

            "breadth_regime":
            "UNKNOWN",
        }

    bullish_pct = (
        bullish / total
    ) * 100.0

    bearish_pct = (
        bearish / total
    ) * 100.0

    neutral_pct = (
        neutral / total
    ) * 100.0

    avg_alignment = average(
        alignment_scores
    )

    if bullish_pct >= 70:
        breadth_regime = (
            "BROAD_STRONG_BULLISH"
        )

    elif bullish_pct >= 55:
        breadth_regime = (
            "BROAD_BULLISH"
        )

    elif bearish_pct >= 70:
        breadth_regime = (
            "BROAD_STRONG_BEARISH"
        )

    elif bearish_pct >= 55:
        breadth_regime = (
            "BROAD_BEARISH"
        )

    else:
        breadth_regime = (
            "MIXED"
        )

    return {
        "total_symbols":
        total,

        "bullish_symbols":
        bullish,

        "bearish_symbols":
        bearish,

        "neutral_symbols":
        neutral,

        "strong_bullish_symbols":
        strong_bullish,

        "strong_bearish_symbols":
        strong_bearish,

        "bullish_pct":
        bullish_pct,

        "bearish_pct":
        bearish_pct,

        "neutral_pct":
        neutral_pct,

        "average_alignment":
        avg_alignment,

        "breadth_regime":
        breadth_regime,
    }


# ============================================================
# MARKET VOLATILITY
# ============================================================


def analyze_market_volatility(
    symbol_analyses: List[Dict[str, Any]],
) -> Dict[str, Any]:

    atr_values = []

    very_high = 0
    high = 0
    normal = 0
    low = 0
    very_low = 0

    for analysis in symbol_analyses or []:

        tf = get_timeframe_analysis(
            analysis,
            "1H",
        )

        if not tf.get("valid"):
            continue

        atr_pct = safe_float(
            tf.get(
                "atr_pct"
            )
        )

        if atr_pct is not None:
            atr_values.append(
                atr_pct
            )

        regime = (
            tf
            .get("volatility", {})
            .get("regime")
        )

        if regime == "VERY_HIGH":
            very_high += 1

        elif regime == "HIGH":
            high += 1

        elif regime == "NORMAL":
            normal += 1

        elif regime == "LOW":
            low += 1

        elif regime == "VERY_LOW":
            very_low += 1

    total = (
        very_high
        + high
        + normal
        + low
        + very_low
    )

    avg_atr_pct = average(
        atr_values
    )

    high_vol_pct = 0.0

    if total > 0:

        high_vol_pct = (
            (
                very_high
                + high
            )
            / total
        ) * 100.0

    if high_vol_pct >= 60:
        market_volatility = (
            "HIGH"
        )

    elif high_vol_pct >= 30:
        market_volatility = (
            "ELEVATED"
        )

    elif total == 0:
        market_volatility = (
            "UNKNOWN"
        )

    else:
        market_volatility = (
            "NORMAL"
        )

    return {
        "market_volatility":
        market_volatility,

        "average_1h_atr_pct":
        avg_atr_pct,

        "high_volatility_pct":
        high_vol_pct,

        "very_high_count":
        very_high,

        "high_count":
        high,

        "normal_count":
        normal,

        "low_count":
        low,

        "very_low_count":
        very_low,
    }


# ============================================================
# RELATIVE STRENGTH
# ============================================================


def relative_strength_vs_btc(
    coin_analysis: Dict[str, Any],
    btc_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Measures whether a coin is outperforming or
    underperforming BTC.

    This can become very useful for finding strong
    altcoins during bullish conditions and weak
    altcoins during bearish conditions.
    """

    coin_1h = get_timeframe_momentum(
        coin_analysis,
        "1H",
        "1_candle_pct",
    )

    btc_1h = get_timeframe_momentum(
        btc_analysis,
        "1H",
        "1_candle_pct",
    )

    coin_4h = get_timeframe_momentum(
        coin_analysis,
        "4H",
        "1_candle_pct",
    )

    btc_4h = get_timeframe_momentum(
        btc_analysis,
        "4H",
        "1_candle_pct",
    )

    relative_1h = None
    relative_4h = None

    if (
        coin_1h is not None
        and btc_1h is not None
    ):

        relative_1h = (
            coin_1h
            - btc_1h
        )

    if (
        coin_4h is not None
        and btc_4h is not None
    ):

        relative_4h = (
            coin_4h
            - btc_4h
        )

    combined = average([
        relative_1h,
        relative_4h,
    ])

    if combined is None:

        state = "UNKNOWN"

    elif combined >= 2.0:

        state = (
            "STRONGLY_OUTPERFORMING_BTC"
        )

    elif combined >= 0.50:

        state = (
            "OUTPERFORMING_BTC"
        )

    elif combined <= -2.0:

        state = (
            "STRONGLY_UNDERPERFORMING_BTC"
        )

    elif combined <= -0.50:

        state = (
            "UNDERPERFORMING_BTC"
        )

    else:

        state = (
            "TRACKING_BTC"
        )

    return {
        "relative_1h_pct":
        relative_1h,

        "relative_4h_pct":
        relative_4h,

        "combined_relative_strength":
        combined,

        "state":
        state,
    }


# ============================================================
# DIRECTION VS MARKET
# ============================================================


def direction_market_agreement(
    direction: str,
    market_context: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Checks whether a proposed LONG or SHORT agrees
    with the wider market.

    It does NOT approve or reject the signal.
    It only provides evidence for the confidence
    engine later.
    """

    direction = (
        str(direction)
        .upper()
        .strip()
    )

    major = market_context.get(
        "major_context",
        {},
    )

    breadth = market_context.get(
        "breadth",
        {},
    )

    major_alignment = safe_float(
        major.get(
            "combined_alignment"
        ),
        0.0,
    )

    breadth_alignment = safe_float(
        breadth.get(
            "average_alignment"
        ),
        0.0,
    )

    combined_market_score = (
        major_alignment * 0.65
        + breadth_alignment * 0.35
    )

    combined_market_score = clamp(
        combined_market_score,
        -1.0,
        1.0,
    )

    if direction == "LONG":

        agreement = (
            combined_market_score
        )

    elif direction == "SHORT":

        agreement = (
            -combined_market_score
        )

    else:

        agreement = 0.0

    if agreement >= 0.60:
        state = (
            "STRONG_AGREEMENT"
        )

    elif agreement >= 0.20:
        state = (
            "AGREEMENT"
        )

    elif agreement <= -0.60:
        state = (
            "STRONG_CONFLICT"
        )

    elif agreement <= -0.20:
        state = (
            "CONFLICT"
        )

    else:
        state = (
            "NEUTRAL"
        )

    return {
        "agreement_score":
        agreement,

        "state":
        state,

        "raw_market_direction":
        combined_market_score,
    }


# ============================================================
# DETECT EXTREME MARKET CONDITIONS
# ============================================================


def detect_market_stress(
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
    breadth: Dict[str, Any],
    volatility: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Identifies unusual or dangerous market states.

    We store these states in memory so the bot can
    later learn how signals behave during them.
    """

    reasons = []

    stress_score = 0.0

    btc_1h = get_timeframe_momentum(
        btc_analysis,
        "1H",
        "1_candle_pct",
    )

    eth_1h = get_timeframe_momentum(
        eth_analysis,
        "1H",
        "1_candle_pct",
    )

    if btc_1h is not None:

        if abs(btc_1h) >= 4.0:

            stress_score += 0.35

            reasons.append(
                "EXTREME_BTC_1H_MOVE"
            )

        elif abs(btc_1h) >= 2.0:

            stress_score += 0.20

            reasons.append(
                "LARGE_BTC_1H_MOVE"
            )

    if eth_1h is not None:

        if abs(eth_1h) >= 5.0:

            stress_score += 0.25

            reasons.append(
                "EXTREME_ETH_1H_MOVE"
            )

        elif abs(eth_1h) >= 2.5:

            stress_score += 0.15

            reasons.append(
                "LARGE_ETH_1H_MOVE"
            )

    bullish_pct = safe_float(
        breadth.get(
            "bullish_pct"
        ),
        0.0,
    )

    bearish_pct = safe_float(
        breadth.get(
            "bearish_pct"
        ),
        0.0,
    )

    if (
        bullish_pct >= 80
        or bearish_pct >= 80
    ):

        stress_score += 0.15

        reasons.append(
            "EXTREME_MARKET_BREADTH"
        )

    market_vol = volatility.get(
        "market_volatility"
    )

    if market_vol == "HIGH":

        stress_score += 0.25

        reasons.append(
            "HIGH_MARKET_VOLATILITY"
        )

    elif market_vol == "ELEVATED":

        stress_score += 0.10

        reasons.append(
            "ELEVATED_MARKET_VOLATILITY"
        )

    stress_score = clamp(
        stress_score,
        0.0,
        1.0,
    )

    if stress_score >= 0.70:

        state = "EXTREME"

    elif stress_score >= 0.40:

        state = "HIGH"

    elif stress_score >= 0.20:

        state = "ELEVATED"

    else:

        state = "NORMAL"

    return {
        "state":
        state,

        "stress_score":
        stress_score,

        "reasons":
        reasons,
    }


# ============================================================
# FULL MARKET CONTEXT
# ============================================================


def build_market_context(
    btc_analysis: Dict[str, Any],
    eth_analysis: Dict[str, Any],
    all_symbol_analyses: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    """
    Creates one complete market snapshot.

    This snapshot will later be stored with every
    opportunity considered by the bot.
    """

    major_context = (
        analyze_major_context(
            btc_analysis,
            eth_analysis,
        )
    )

    breadth = (
        analyze_market_breadth(
            all_symbol_analyses
        )
    )

    volatility = (
        analyze_market_volatility(
            all_symbol_analyses
        )
    )

    stress = (
        detect_market_stress(
            btc_analysis=btc_analysis,
            eth_analysis=eth_analysis,
            breadth=breadth,
            volatility=volatility,
        )
    )

    return {
        "major_context":
        major_context,

        "breadth":
        breadth,

        "volatility":
        volatility,

        "stress":
        stress,
    }


# ============================================================
# COIN-SPECIFIC CONTEXT
# ============================================================


def build_coin_market_context(
    coin_analysis: Dict[str, Any],
    btc_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    direction: Optional[str] = None,
) -> Dict[str, Any]:

    """
    Adds market context specifically for one coin.

    This will eventually feed:
    - memory
    - pattern matching
    - confidence scoring
    - AI analysis
    """

    relative_strength = (
        relative_strength_vs_btc(
            coin_analysis,
            btc_analysis,
        )
    )

    result = {
        "relative_strength_vs_btc":
        relative_strength,

        "major_market":
        market_context.get(
            "major_context"
        ),

        "breadth":
        market_context.get(
            "breadth"
        ),

        "market_volatility":
        market_context.get(
            "volatility"
        ),

        "market_stress":
        market_context.get(
            "stress"
        ),
    }

    if direction:

        result[
            "direction_market_agreement"
        ] = direction_market_agreement(
            direction,
            market_context,
        )

    return result


# ============================================================
# MEMORY FEATURE FLATTENER
# ============================================================


def build_context_features(
    coin_context: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Converts market context into standardized
    memory features.

    Later the pattern matcher can compare:
    "What happened historically when the market
    looked similar to this?"
    """

    major = coin_context.get(
        "major_market",
        {},
    ) or {}

    breadth = coin_context.get(
        "breadth",
        {},
    ) or {}

    volatility = coin_context.get(
        "market_volatility",
        {},
    ) or {}

    stress = coin_context.get(
        "market_stress",
        {},
    ) or {}

    relative = coin_context.get(
        "relative_strength_vs_btc",
        {},
    ) or {}

    agreement = coin_context.get(
        "direction_market_agreement",
        {},
    ) or {}

    return {
        "market_regime":
        major.get(
            "regime"
        ),

        "market_alignment":
        major.get(
            "combined_alignment"
        ),

        "btc_alignment":
        major.get(
            "btc_alignment"
        ),

        "eth_alignment":
        major.get(
            "eth_alignment"
        ),

        "btc_1h_momentum":
        major.get(
            "btc_1h_momentum"
        ),

        "eth_1h_momentum":
        major.get(
            "eth_1h_momentum"
        ),

        "market_bullish_pct":
        breadth.get(
            "bullish_pct"
        ),

        "market_bearish_pct":
        breadth.get(
            "bearish_pct"
        ),

        "market_breadth_regime":
        breadth.get(
            "breadth_regime"
        ),

        "market_average_alignment":
        breadth.get(
            "average_alignment"
        ),

        "market_volatility":
        volatility.get(
            "market_volatility"
        ),

        "market_average_atr_pct":
        volatility.get(
            "average_1h_atr_pct"
        ),

        "market_stress_state":
        stress.get(
            "state"
        ),

        "market_stress_score":
        stress.get(
            "stress_score"
        ),

        "relative_strength_btc":
        relative.get(
            "combined_relative_strength"
        ),

        "relative_strength_state":
        relative.get(
            "state"
        ),

        "market_agreement":
        agreement.get(
            "agreement_score"
        ),

        "market_agreement_state":
        agreement.get(
            "state"
        ),
    }


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- MARKET CONTEXT ENGINE",
        flush=True,
    )

    print(
        "BTC + ETH CONTEXT: READY",
        flush=True,
    )

    print(
        "MARKET BREADTH: READY",
        flush=True,
    )

    print(
        "RELATIVE STRENGTH: READY",
        flush=True,
    )

    print(
        "MARKET STRESS DETECTION: READY",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )
