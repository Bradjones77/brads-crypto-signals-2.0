import math
from typing import Dict, List, Optional, Any

import numpy as np


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# TECHNICAL ANALYSIS ENGINE
#
# PURPOSE:
# Turn raw Bitget candles into structured market intelligence.
#
# THIS FILE:
# - DOES NOT PLACE TRADES
# - DOES NOT SEND TELEGRAM MESSAGES
# - DOES NOT USE API KEYS
# - DOES NOT MODIFY THE OLD BOT
# ============================================================


# ============================================================
# BASIC HELPERS
# ============================================================


def safe_float(value, default=None):
    try:
        value = float(value)

        if not math.isfinite(value):
            return default

        return value

    except Exception:
        return default


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def pct_change(
    old_value: float,
    new_value: float,
) -> Optional[float]:

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


def mean(values: List[float]) -> Optional[float]:

    clean = [
        safe_float(x)
        for x in values
    ]

    clean = [
        x for x in clean
        if x is not None
    ]

    if not clean:
        return None

    return float(
        np.mean(clean)
    )


def stddev(values: List[float]) -> Optional[float]:

    clean = [
        safe_float(x)
        for x in values
    ]

    clean = [
        x for x in clean
        if x is not None
    ]

    if len(clean) < 2:
        return None

    return float(
        np.std(clean)
    )


# ============================================================
# CANDLE NORMALIZATION
# ============================================================


def normalize_candles(
    candles: List[Dict[str, Any]],
) -> List[Dict[str, float]]:
    """
    Cleans and sorts candles oldest -> newest.
    """

    cleaned = []

    for candle in candles or []:

        try:
            timestamp = int(
                candle["timestamp"]
            )

            open_price = float(
                candle["open"]
            )

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            close = float(
                candle["close"]
            )

            volume_base = safe_float(
                candle.get(
                    "volume_base"
                ),
                0.0,
            )

            volume_quote = safe_float(
                candle.get(
                    "volume_quote"
                ),
                0.0,
            )

            if (
                open_price <= 0
                or high <= 0
                or low <= 0
                or close <= 0
            ):
                continue

            if high < low:
                continue

            cleaned.append(
                {
                    "timestamp":
                    timestamp,

                    "open":
                    open_price,

                    "high":
                    high,

                    "low":
                    low,

                    "close":
                    close,

                    "volume_base":
                    volume_base,

                    "volume_quote":
                    volume_quote,
                }
            )

        except Exception:
            continue

    cleaned.sort(
        key=lambda x:
        x["timestamp"]
    )

    return cleaned


def candle_arrays(
    candles: List[Dict[str, Any]],
):

    candles = normalize_candles(
        candles
    )

    opens = [
        c["open"]
        for c in candles
    ]

    highs = [
        c["high"]
        for c in candles
    ]

    lows = [
        c["low"]
        for c in candles
    ]

    closes = [
        c["close"]
        for c in candles
    ]

    volumes = [
        c["volume_quote"]
        if c["volume_quote"] > 0
        else c["volume_base"]
        for c in candles
    ]

    return (
        candles,
        opens,
        highs,
        lows,
        closes,
        volumes,
    )


# ============================================================
# SMA / EMA
# ============================================================


def sma(
    values: List[float],
    period: int,
) -> Optional[float]:

    if (
        not values
        or len(values) < period
        or period <= 0
    ):
        return None

    return float(
        np.mean(
            values[-period:]
        )
    )


def ema_series(
    values: List[float],
    period: int,
) -> List[float]:

    if (
        not values
        or period <= 0
    ):
        return []

    values = [
        float(x)
        for x in values
    ]

    multiplier = (
        2.0
        / (period + 1.0)
    )

    result = [
        values[0]
    ]

    for value in values[1:]:

        next_ema = (
            value
            * multiplier
            + result[-1]
            * (1.0 - multiplier)
        )

        result.append(
            next_ema
        )

    return result


def ema(
    values: List[float],
    period: int,
) -> Optional[float]:

    if (
        not values
        or len(values) < period
    ):
        return None

    series = ema_series(
        values,
        period,
    )

    if not series:
        return None

    return float(
        series[-1]
    )


# ============================================================
# RSI
# ============================================================


def rsi(
    closes: List[float],
    period: int = 14,
) -> Optional[float]:

    if len(closes) < (
        period + 1
    ):
        return None

    changes = np.diff(
        np.array(
            closes,
            dtype=float,
        )
    )

    gains = np.where(
        changes > 0,
        changes,
        0.0,
    )

    losses = np.where(
        changes < 0,
        -changes,
        0.0,
    )

    avg_gain = float(
        np.mean(
            gains[-period:]
        )
    )

    avg_loss = float(
        np.mean(
            losses[-period:]
        )
    )

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = (
        avg_gain
        / avg_loss
    )

    value = (
        100.0
        - (
            100.0
            / (1.0 + rs)
        )
    )

    return float(
        clamp(
            value,
            0.0,
            100.0,
        )
    )


# ============================================================
# MACD
# ============================================================


def macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Dict[str, Optional[float]]:

    if len(closes) < (
        slow + signal_period
    ):

        return {
            "macd":
            None,

            "signal":
            None,

            "histogram":
            None,

            "histogram_previous":
            None,

            "histogram_acceleration":
            None,
        }

    fast_series = ema_series(
        closes,
        fast,
    )

    slow_series = ema_series(
        closes,
        slow,
    )

    start = slow - 1

    macd_values = []

    for i in range(
        start,
        len(closes),
    ):

        macd_values.append(
            fast_series[i]
            - slow_series[i]
        )

    signal_values = ema_series(
        macd_values,
        signal_period,
    )

    if not signal_values:
        return {
            "macd": None,
            "signal": None,
            "histogram": None,
            "histogram_previous": None,
            "histogram_acceleration": None,
        }

    current_macd = (
        macd_values[-1]
    )

    current_signal = (
        signal_values[-1]
    )

    current_histogram = (
        current_macd
        - current_signal
    )

    previous_histogram = None

    histogram_acceleration = None

    if (
        len(macd_values) >= 2
        and len(signal_values) >= 2
    ):

        previous_histogram = (
            macd_values[-2]
            - signal_values[-2]
        )

        histogram_acceleration = (
            current_histogram
            - previous_histogram
        )

    return {
        "macd":
        float(current_macd),

        "signal":
        float(current_signal),

        "histogram":
        float(current_histogram),

        "histogram_previous":
        (
            float(previous_histogram)
            if previous_histogram
            is not None
            else None
        ),

        "histogram_acceleration":
        (
            float(histogram_acceleration)
            if histogram_acceleration
            is not None
            else None
        ),
    }


# ============================================================
# ATR
# ============================================================


def atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Optional[float]:

    if (
        len(highs) < period + 1
        or len(lows) < period + 1
        or len(closes) < period + 1
    ):
        return None

    true_ranges = []

    for i in range(
        1,
        len(closes),
    ):

        true_range = max(
            highs[i]
            - lows[i],

            abs(
                highs[i]
                - closes[i - 1]
            ),

            abs(
                lows[i]
                - closes[i - 1]
            ),
        )

        true_ranges.append(
            true_range
        )

    if len(true_ranges) < period:
        return None

    return float(
        np.mean(
            true_ranges[-period:]
        )
    )


def atr_percentage(
    atr_value: Optional[float],
    price: Optional[float],
) -> Optional[float]:

    if (
        atr_value is None
        or price is None
        or price <= 0
    ):
        return None

    return (
        atr_value
        / price
    ) * 100.0


# ============================================================
# MOMENTUM
# ============================================================


def momentum_percent(
    closes: List[float],
    periods_back: int,
) -> Optional[float]:

    if len(closes) <= periods_back:
        return None

    return pct_change(
        closes[
            -(periods_back + 1)
        ],
        closes[-1],
    )


def momentum_acceleration(
    closes: List[float],
    short_window: int = 3,
    long_window: int = 6,
) -> Optional[float]:

    if len(closes) <= long_window:
        return None

    short_move = (
        momentum_percent(
            closes,
            short_window,
        )
    )

    long_move = (
        momentum_percent(
            closes,
            long_window,
        )
    )

    if (
        short_move is None
        or long_move is None
    ):
        return None

    long_per_candle = (
        long_move
        / long_window
    )

    short_per_candle = (
        short_move
        / short_window
    )

    return (
        short_per_candle
        - long_per_candle
    )


# ============================================================
# VOLUME ANALYSIS
# ============================================================


def volume_analysis(
    volumes: List[float],
) -> Dict[str, Optional[float]]:

    if len(volumes) < 21:

        return {
            "current":
            None,

            "average_20":
            None,

            "ratio":
            None,

            "change_pct":
            None,

            "acceleration":
            None,
        }

    current = (
        volumes[-1]
    )

    average_20 = float(
        np.mean(
            volumes[-21:-1]
        )
    )

    ratio = None

    if average_20 > 0:
        ratio = (
            current
            / average_20
        )

    change = None

    if volumes[-2] > 0:
        change = (
            (
                current
                - volumes[-2]
            )
            / volumes[-2]
        ) * 100.0

    recent_3 = float(
        np.mean(
            volumes[-3:]
        )
    )

    previous_3 = float(
        np.mean(
            volumes[-6:-3]
        )
    )

    acceleration = None

    if previous_3 > 0:
        acceleration = (
            (
                recent_3
                - previous_3
            )
            / previous_3
        ) * 100.0

    return {
        "current":
        current,

        "average_20":
        average_20,

        "ratio":
        ratio,

        "change_pct":
        change,

        "acceleration":
        acceleration,
    }


# ============================================================
# CANDLE STRUCTURE
# ============================================================


def candle_structure(
    candle: Dict[str, float],
) -> Dict[str, Optional[float]]:

    open_price = candle["open"]
    high = candle["high"]
    low = candle["low"]
    close = candle["close"]

    candle_range = (
        high - low
    )

    body = abs(
        close - open_price
    )

    upper_wick = (
        high
        - max(
            open_price,
            close,
        )
    )

    lower_wick = (
        min(
            open_price,
            close,
        )
        - low
    )

    if candle_range <= 0:

        return {
            "body_ratio":
            0.0,

            "upper_wick_ratio":
            0.0,

            "lower_wick_ratio":
            0.0,

            "bullish":
            close > open_price,

            "bearish":
            close < open_price,
        }

    return {
        "body_ratio":
        body / candle_range,

        "upper_wick_ratio":
        upper_wick / candle_range,

        "lower_wick_ratio":
        lower_wick / candle_range,

        "bullish":
        close > open_price,

        "bearish":
        close < open_price,
    }


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================


def support_resistance(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = 50,
) -> Dict[str, Optional[float]]:

    if (
        not highs
        or not lows
        or not closes
    ):

        return {
            "support":
            None,

            "resistance":
            None,

            "distance_to_support_pct":
            None,

            "distance_to_resistance_pct":
            None,
        }

    lookback = min(
        lookback,
        len(closes),
    )

    recent_highs = (
        highs[-lookback:]
    )

    recent_lows = (
        lows[-lookback:]
    )

    current_price = (
        closes[-1]
    )

    support_candidates = [
        x
        for x in recent_lows
        if x <= current_price
    ]

    resistance_candidates = [
        x
        for x in recent_highs
        if x >= current_price
    ]

    support = (
        max(support_candidates)
        if support_candidates
        else min(recent_lows)
    )

    resistance = (
        min(resistance_candidates)
        if resistance_candidates
        else max(recent_highs)
    )

    support_distance = (
        (
            current_price
            - support
        )
        / current_price
        * 100.0
        if current_price > 0
        else None
    )

    resistance_distance = (
        (
            resistance
            - current_price
        )
        / current_price
        * 100.0
        if current_price > 0
        else None
    )

    return {
        "support":
        support,

        "resistance":
        resistance,

        "distance_to_support_pct":
        support_distance,

        "distance_to_resistance_pct":
        resistance_distance,
    }


# ============================================================
# BREAKOUT ANALYSIS
# ============================================================


def breakout_analysis(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    lookback: int = 20,
) -> Dict[str, Any]:

    if len(closes) < (
        lookback + 2
    ):

        return {
            "bullish_breakout":
            False,

            "bearish_breakout":
            False,

            "breakout_strength_pct":
            None,

            "volume_confirmation":
            False,
        }

    current_price = (
        closes[-1]
    )

    previous_high = max(
        highs[
            -(lookback + 1):-1
        ]
    )

    previous_low = min(
        lows[
            -(lookback + 1):-1
        ]
    )

    bullish = (
        current_price
        > previous_high
    )

    bearish = (
        current_price
        < previous_low
    )

    strength = None

    if bullish:
        strength = (
            (
                current_price
                - previous_high
            )
            / previous_high
        ) * 100.0

    elif bearish:
        strength = (
            (
                previous_low
                - current_price
            )
            / previous_low
        ) * 100.0

    volume_info = (
        volume_analysis(
            volumes
        )
    )

    volume_ratio = (
        volume_info.get(
            "ratio"
        )
    )

    volume_confirmation = (
        volume_ratio is not None
        and volume_ratio >= 1.20
    )

    return {
        "bullish_breakout":
        bullish,

        "bearish_breakout":
        bearish,

        "breakout_strength_pct":
        strength,

        "volume_confirmation":
        volume_confirmation,
    }


# ============================================================
# VOLATILITY REGIME
# ============================================================


def volatility_regime(
    closes: List[float],
    atr_pct: Optional[float],
) -> Dict[str, Any]:

    if len(closes) < 31:

        return {
            "regime":
            "UNKNOWN",

            "realized_volatility":
            None,
        }

    returns = []

    for i in range(
        1,
        len(closes),
    ):

        if closes[i - 1] <= 0:
            continue

        returns.append(
            (
                closes[i]
                - closes[i - 1]
            )
            / closes[i - 1]
        )

    if len(returns) < 20:

        return {
            "regime":
            "UNKNOWN",

            "realized_volatility":
            None,
        }

    recent_vol = float(
        np.std(
            returns[-10:]
        )
    )

    baseline_vol = float(
        np.std(
            returns[-30:]
        )
    )

    if baseline_vol <= 0:

        ratio = 1.0

    else:

        ratio = (
            recent_vol
            / baseline_vol
        )

    if ratio >= 1.5:
        regime = "VERY_HIGH"

    elif ratio >= 1.15:
        regime = "HIGH"

    elif ratio <= 0.65:
        regime = "VERY_LOW"

    elif ratio <= 0.85:
        regime = "LOW"

    else:
        regime = "NORMAL"

    return {
        "regime":
        regime,

        "recent_vs_baseline_ratio":
        ratio,

        "realized_volatility":
        recent_vol,

        "atr_pct":
        atr_pct,
    }


# ============================================================
# TREND ANALYSIS
# ============================================================


def trend_analysis(
    closes: List[float],
) -> Dict[str, Any]:

    if len(closes) < 55:

        return {
            "trend":
            "UNKNOWN",

            "strength":
            0.0,
        }

    price = (
        closes[-1]
    )

    ema9 = ema(
        closes,
        9,
    )

    ema20 = ema(
        closes,
        20,
    )

    ema50 = ema(
        closes,
        50,
    )

    if (
        ema9 is None
        or ema20 is None
        or ema50 is None
    ):

        return {
            "trend":
            "UNKNOWN",

            "strength":
            0.0,
        }

    bullish_points = 0
    bearish_points = 0

    if price > ema9:
        bullish_points += 1
    elif price < ema9:
        bearish_points += 1

    if ema9 > ema20:
        bullish_points += 1
    elif ema9 < ema20:
        bearish_points += 1

    if ema20 > ema50:
        bullish_points += 1
    elif ema20 < ema50:
        bearish_points += 1

    if price > ema50:
        bullish_points += 1
    elif price < ema50:
        bearish_points += 1

    if bullish_points >= 4:
        trend = "STRONG_BULLISH"

    elif bullish_points == 3:
        trend = "BULLISH"

    elif bearish_points >= 4:
        trend = "STRONG_BEARISH"

    elif bearish_points == 3:
        trend = "BEARISH"

    else:
        trend = "NEUTRAL"

    separation = (
        abs(
            ema9 - ema50
        )
        / price
        * 100.0
        if price > 0
        else 0.0
    )

    direction_strength = (
        max(
            bullish_points,
            bearish_points,
        )
        / 4.0
    )

    strength = (
        direction_strength
        * min(
            1.0,
            separation / 2.0,
        )
    )

    return {
        "trend":
        trend,

        "strength":
        float(
            clamp(
                strength,
                0.0,
                1.0,
            )
        ),

        "ema9":
        ema9,

        "ema20":
        ema20,

        "ema50":
        ema50,

        "price_vs_ema20_pct":
        pct_change(
            ema20,
            price,
        ),

        "ema9_vs_ema20_pct":
        pct_change(
            ema20,
            ema9,
        ),

        "ema20_vs_ema50_pct":
        pct_change(
            ema50,
            ema20,
        ),
    }


# ============================================================
# RSI INTERPRETATION
# ============================================================


def rsi_state(
    value: Optional[float],
) -> str:

    if value is None:
        return "UNKNOWN"

    if value >= 80:
        return "EXTREME_OVERBOUGHT"

    if value >= 70:
        return "OVERBOUGHT"

    if value >= 60:
        return "BULLISH"

    if value <= 20:
        return "EXTREME_OVERSOLD"

    if value <= 30:
        return "OVERSOLD"

    if value <= 40:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# SINGLE TIMEFRAME ANALYSIS
# ============================================================


def analyze_timeframe(
    candles: List[Dict[str, Any]],
    timeframe: str,
) -> Dict[str, Any]:
    """
    Produces a rich snapshot of one timeframe.

    This snapshot is designed to be stored
    in memory later so the bot can compare
    future setups with historical ones.
    """

    (
        candles,
        opens,
        highs,
        lows,
        closes,
        volumes,
    ) = candle_arrays(
        candles
    )

    if len(candles) < 55:

        return {
            "timeframe":
            timeframe,

            "valid":
            False,

            "reason":
            "Not enough candle history",

            "candle_count":
            len(candles),
        }

    current_price = (
        closes[-1]
    )

    current_rsi = rsi(
        closes,
        14,
    )

    current_macd = macd(
        closes
    )

    current_atr = atr(
        highs,
        lows,
        closes,
        14,
    )

    current_atr_pct = (
        atr_percentage(
            current_atr,
            current_price,
        )
    )

    trend = trend_analysis(
        closes
    )

    volume = volume_analysis(
        volumes
    )

    support_res = (
        support_resistance(
            highs,
            lows,
            closes,
            lookback=50,
        )
    )

    breakout = (
        breakout_analysis(
            highs,
            lows,
            closes,
            volumes,
            lookback=20,
        )
    )

    volatility = (
        volatility_regime(
            closes,
            current_atr_pct,
        )
    )

    latest_candle = (
        candle_structure(
            candles[-1]
        )
    )

    momentum_1 = (
        momentum_percent(
            closes,
            1,
        )
    )

    momentum_3 = (
        momentum_percent(
            closes,
            3,
        )
    )

    momentum_6 = (
        momentum_percent(
            closes,
            6,
        )
    )

    momentum_12 = (
        momentum_percent(
            closes,
            12,
        )
    )

    acceleration = (
        momentum_acceleration(
            closes,
            short_window=3,
            long_window=6,
        )
    )

    return {
        "timeframe":
        timeframe,

        "valid":
        True,

        "candle_count":
        len(candles),

        "timestamp":
        candles[-1]["timestamp"],

        "price":
        current_price,

        "trend":
        trend,

        "rsi":
        current_rsi,

        "rsi_state":
        rsi_state(
            current_rsi
        ),

        "macd":
        current_macd,

        "atr":
        current_atr,

        "atr_pct":
        current_atr_pct,

        "volatility":
        volatility,

        "volume":
        volume,

        "momentum":
        {
            "1_candle_pct":
            momentum_1,

            "3_candle_pct":
            momentum_3,

            "6_candle_pct":
            momentum_6,

            "12_candle_pct":
            momentum_12,

            "acceleration":
            acceleration,
        },

        "support_resistance":
        support_res,

        "breakout":
        breakout,

        "latest_candle":
        latest_candle,
    }


# ============================================================
# MULTI-TIMEFRAME AGREEMENT
# ============================================================


def multi_timeframe_alignment(
    analyses: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    bullish = 0
    bearish = 0
    neutral = 0
    valid_count = 0

    weighted_direction = 0.0
    total_weight = 0.0

    weights = {
        "5m": 0.50,
        "15m": 0.75,
        "30m": 1.00,
        "1H": 1.25,
        "4H": 1.50,
        "1D": 1.75,
    }

    details = {}

    for timeframe, analysis in (
        analyses.items()
    ):

        if not analysis.get(
            "valid"
        ):
            continue

        valid_count += 1

        trend = (
            analysis
            .get("trend", {})
            .get("trend", "UNKNOWN")
        )

        strength = safe_float(
            analysis
            .get("trend", {})
            .get("strength"),
            0.0,
        )

        weight = weights.get(
            timeframe,
            1.0,
        )

        score = 0.0

        if trend == "STRONG_BULLISH":
            bullish += 1
            score = 1.0

        elif trend == "BULLISH":
            bullish += 1
            score = 0.65

        elif trend == "STRONG_BEARISH":
            bearish += 1
            score = -1.0

        elif trend == "BEARISH":
            bearish += 1
            score = -0.65

        else:
            neutral += 1

        weighted_direction += (
            score
            * weight
            * max(
                0.25,
                strength,
            )
        )

        total_weight += (
            weight
        )

        details[timeframe] = {
            "trend":
            trend,

            "strength":
            strength,

            "weight":
            weight,
        }

    alignment_score = 0.0

    if total_weight > 0:

        alignment_score = (
            weighted_direction
            / total_weight
        )

    alignment_score = clamp(
        alignment_score,
        -1.0,
        1.0,
    )

    if alignment_score >= 0.60:
        overall = "STRONG_BULLISH"

    elif alignment_score >= 0.25:
        overall = "BULLISH"

    elif alignment_score <= -0.60:
        overall = "STRONG_BEARISH"

    elif alignment_score <= -0.25:
        overall = "BEARISH"

    else:
        overall = "MIXED"

    return {
        "overall":
        overall,

        "alignment_score":
        alignment_score,

        "bullish_timeframes":
        bullish,

        "bearish_timeframes":
        bearish,

        "neutral_timeframes":
        neutral,

        "valid_timeframes":
        valid_count,

        "details":
        details,
    }


# ============================================================
# SYMBOL ANALYSIS
# ============================================================


def analyze_symbol(
    symbol: str,
    multi_timeframe_candles: Dict[
        str,
        List[Dict[str, Any]]
    ],
) -> Dict[str, Any]:
    """
    Full technical snapshot for one symbol.

    IMPORTANT:
    This returns evidence.

    It deliberately does NOT decide:
    - whether to send a signal
    - final confidence
    - whether LONG or SHORT is definitely correct

    Those decisions are made later by the
    scoring + memory + AI engines.
    """

    timeframe_analyses = {}

    for timeframe, candles in (
        multi_timeframe_candles.items()
    ):

        timeframe_analyses[
            timeframe
        ] = analyze_timeframe(
            candles=candles,
            timeframe=timeframe,
        )

    alignment = (
        multi_timeframe_alignment(
            timeframe_analyses
        )
    )

    latest_price = None
    latest_timestamp = None

    preferred_order = [
        "5m",
        "15m",
        "30m",
        "1H",
        "4H",
        "1D",
    ]

    for timeframe in preferred_order:

        analysis = (
            timeframe_analyses.get(
                timeframe
            )
        )

        if (
            analysis
            and analysis.get("valid")
        ):

            latest_price = (
                analysis.get(
                    "price"
                )
            )

            latest_timestamp = (
                analysis.get(
                    "timestamp"
                )
            )

            break

    return {
        "symbol":
        symbol.upper(),

        "price":
        latest_price,

        "timestamp":
        latest_timestamp,

        "timeframes":
        timeframe_analyses,

        "multi_timeframe":
        alignment,
    }


# ============================================================
# FEATURE FLATTENER
# ============================================================


def build_feature_vector(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Converts the rich nested analysis into
    a flatter feature set.

    THIS IS VERY IMPORTANT FOR MEMORY.

    Later, Signals Bot 2.0 can compare a new
    setup against thousands of old snapshots
    using these standardized features.
    """

    features = {
        "symbol":
        analysis.get(
            "symbol"
        ),

        "price":
        analysis.get(
            "price"
        ),

        "timestamp":
        analysis.get(
            "timestamp"
        ),
    }

    mtf = analysis.get(
        "multi_timeframe",
        {},
    )

    features[
        "mtf_alignment"
    ] = mtf.get(
        "alignment_score"
    )

    features[
        "mtf_overall"
    ] = mtf.get(
        "overall"
    )

    for timeframe, data in (
        analysis.get(
            "timeframes",
            {}
        ).items()
    ):

        if not data.get(
            "valid"
        ):
            continue

        prefix = (
            timeframe
            .replace(
                "H",
                "h",
            )
            .replace(
                "D",
                "d",
            )
        )

        trend = data.get(
            "trend",
            {},
        )

        features[
            f"{prefix}_trend"
        ] = trend.get(
            "trend"
        )

        features[
            f"{prefix}_trend_strength"
        ] = trend.get(
            "strength"
        )

        features[
            f"{prefix}_rsi"
        ] = data.get(
            "rsi"
        )

        features[
            f"{prefix}_atr_pct"
        ] = data.get(
            "atr_pct"
        )

        macd_data = data.get(
            "macd",
            {},
        )

        features[
            f"{prefix}_macd_hist"
        ] = macd_data.get(
            "histogram"
        )

        features[
            f"{prefix}_macd_acceleration"
        ] = macd_data.get(
            "histogram_acceleration"
        )

        momentum = data.get(
            "momentum",
            {},
        )

        features[
            f"{prefix}_momentum_3"
        ] = momentum.get(
            "3_candle_pct"
        )

        features[
            f"{prefix}_momentum_6"
        ] = momentum.get(
            "6_candle_pct"
        )

        features[
            f"{prefix}_momentum_acceleration"
        ] = momentum.get(
            "acceleration"
        )

        volume = data.get(
            "volume",
            {},
        )

        features[
            f"{prefix}_volume_ratio"
        ] = volume.get(
            "ratio"
        )

        features[
            f"{prefix}_volume_acceleration"
        ] = volume.get(
            "acceleration"
        )

        breakout = data.get(
            "breakout",
            {},
        )

        features[
            f"{prefix}_bull_breakout"
        ] = breakout.get(
            "bullish_breakout"
        )

        features[
            f"{prefix}_bear_breakout"
        ] = breakout.get(
            "bearish_breakout"
        )

        features[
            f"{prefix}_breakout_volume_confirmed"
        ] = breakout.get(
            "volume_confirmation"
        )

        sr = data.get(
            "support_resistance",
            {},
        )

        features[
            f"{prefix}_support_distance"
        ] = sr.get(
            "distance_to_support_pct"
        )

        features[
            f"{prefix}_resistance_distance"
        ] = sr.get(
            "distance_to_resistance_pct"
        )

        volatility = data.get(
            "volatility",
            {},
        )

        features[
            f"{prefix}_volatility_regime"
        ] = volatility.get(
            "regime"
        )

    return features


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- TECHNICAL ANALYSIS ENGINE",
        flush=True,
    )

    print(
        "NO API KEYS REQUIRED",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )

    print(
        "TECHNICAL ANALYSIS MODULE: READY",
        flush=True,
    )
