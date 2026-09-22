import time
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from bitget_market import get_candles, get_historical_1m_candles

from memory_engine import (
    get_pending_outcomes,
    update_outcome,
    mark_outcome_complete,
)


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# OUTCOME TRACKER V2
#
# OUTCOME HORIZONS:
#
# 30 seconds
# 1 minute
# 5 minutes
# 10 minutes
# 30 minutes
# 1 hour
# 4 hours
# 12 hours
# 24 hours
#
# ALSO TRACKS:
#
# - Direction-adjusted returns
# - MFE
# - MAE
# - Highest price
# - Lowest price
# - Early momentum
# - Early continuation
# - Early reversal
#
# IMPORTANT:
#
# Exact 30-second outcomes cannot reliably be reconstructed
# later from 1-minute candles.
#
# The future main controller can therefore call
# record_live_price_checkpoint() at/after 30 seconds.
#
# THIS FILE:
#
# - DOES NOT PLACE TRADES
# - DOES NOT MODIFY POSITIONS
# - DOES NOT SEND TELEGRAM
# ============================================================


# ============================================================
# OUTCOME HORIZONS
# ============================================================


OUTCOME_HORIZONS = {

    "30s": 30,

    "1m": 60,

    "5m": 5 * 60,

    "10m": 10 * 60,

    "30m": 30 * 60,

    "1h": 60 * 60,

    "4h": 4 * 60 * 60,

    "12h": 12 * 60 * 60,

    "24h": 24 * 60 * 60,
}


# ============================================================
# DATABASE FIELD MAP
# ============================================================


HORIZON_FIELDS = {

    "30s": (
        "price_30s",
        "return_30s_pct",
        "direction_correct_30s",
    ),

    "1m": (
        "price_1m",
        "return_1m_pct",
        "direction_correct_1m",
    ),

    "5m": (
        "price_5m",
        "return_5m_pct",
        "direction_correct_5m",
    ),

    "10m": (
        "price_10m",
        "return_10m_pct",
        "direction_correct_10m",
    ),

    "30m": (
        "price_30m",
        "return_30m_pct",
        "direction_correct_30m",
    ),

    "1h": (
        "price_1h",
        "return_1h_pct",
        "direction_correct_1h",
    ),

    "4h": (
        "price_4h",
        "return_4h_pct",
        "direction_correct_4h",
    ),

    "12h": (
        "price_12h",
        "return_12h_pct",
        "direction_correct_12h",
    ),

    "24h": (
        "price_24h",
        "return_24h_pct",
        "direction_correct_24h",
    ),
}


# ============================================================
# TIME HELPERS
# ============================================================


def utc_now():

    return datetime.now(
        timezone.utc
    )


def timestamp_seconds(
    value,
) -> Optional[float]:

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

        return value.timestamp()

    if isinstance(
        value,
        (int, float),
    ):

        value = float(
            value
        )

        if value > 10_000_000_000:

            value /= 1000.0

        return value

    if isinstance(
        value,
        str,
    ):

        try:

            parsed = (
                datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )

            if parsed.tzinfo is None:

                parsed = (
                    parsed.replace(
                        tzinfo=timezone.utc
                    )
                )

            return parsed.timestamp()

        except Exception:

            return None

    return None


def candle_timestamp_seconds(
    candle: Dict[str, Any],
) -> Optional[float]:

    return timestamp_seconds(
        candle.get(
            "timestamp"
        )
    )


# ============================================================
# RETURN CALCULATION
# ============================================================


def directional_return(
    entry_price: float,
    future_price: float,
    direction: str,
) -> Optional[float]:

    try:

        entry_price = float(
            entry_price
        )

        future_price = float(
            future_price
        )

    except Exception:

        return None

    if entry_price <= 0:

        return None

    raw_return = (
        (
            future_price
            - entry_price
        )
        / entry_price
    ) * 100.0

    direction = (
        str(direction)
        .upper()
        .strip()
    )

    if direction == "LONG":

        return raw_return

    if direction == "SHORT":

        return -raw_return

    return None


def direction_correct(
    result,
) -> Optional[bool]:

    if result is None:

        return None

    return (
        result > 0
    )


# ============================================================
# LIVE CHECKPOINT
# ============================================================


def record_live_price_checkpoint(
    conn,
    opportunity: Dict[str, Any],
    horizon_name: str,
    live_price: float,
) -> bool:

    """
    Records an exact live observation.

    Most importantly this allows the future main controller
    to record the 30-second checkpoint without pretending
    a 1-minute historical candle gives us that exact price.
    """

    if horizon_name not in HORIZON_FIELDS:

        return False

    try:

        live_price = float(
            live_price
        )

        entry_price = float(
            opportunity[
                "entry_price"
            ]
        )

    except Exception:

        return False

    if (
        live_price <= 0
        or entry_price <= 0
    ):

        return False

    opportunity_id = (
        opportunity.get(
            "opportunity_id"
        )
    )

    direction = (
        opportunity.get(
            "direction"
        )
    )

    if not opportunity_id:

        return False

    (
        price_field,
        return_field,
        correct_field,
    ) = HORIZON_FIELDS[
        horizon_name
    ]

    result = directional_return(
        entry_price=entry_price,
        future_price=live_price,
        direction=direction,
    )

    update_outcome(
        conn,
        opportunity_id,

        **{
            price_field:
            live_price,

            return_field:
            result,

            correct_field:
            direction_correct(
                result
            ),
        },
    )

    return True


# ============================================================
# FIND HISTORICAL CANDLE
# ============================================================


def find_first_candle_at_or_after(
    candles: List[Dict[str, Any]],
    target_timestamp: float,
) -> Optional[Dict[str, Any]]:

    best = None
    best_timestamp = None

    for candle in candles:

        ts = (
            candle_timestamp_seconds(
                candle
            )
        )

        if ts is None:

            continue

        if ts < target_timestamp:

            continue

        if (
            best_timestamp is None
            or ts < best_timestamp
        ):

            best = candle
            best_timestamp = ts

    return best


# ============================================================
# HISTORICAL PRICE AT HORIZON
# ============================================================


def historical_price_at_horizon(
    candles: List[Dict[str, Any]],
    opportunity_timestamp: float,
    horizon_seconds: int,
    now_timestamp: Optional[float] = None,
) -> Optional[float]:
    """Use the first completed 1m close at/after the target, at most 60s late.

    A candle timestamp is its OPEN in milliseconds. A close that is still in
    the future must never be used, even if an exchange response includes it.
    Missing or aged-out history remains missing; never use a coarser candle.
    """
    if now_timestamp is None:
        now_timestamp = utc_now().timestamp()
    target = opportunity_timestamp + horizon_seconds
    candidates = []
    for candle in candles:
        ts = candle_timestamp_seconds(candle)
        if ts is None:
            continue
        close_time = ts + 60
        if not (target <= close_time <= target + 60 and close_time <= now_timestamp):
            continue
        try:
            price = float(candle["close"])
        except (ValueError, TypeError, KeyError):
            continue
        if math.isfinite(price) and price > 0:
            candidates.append((close_time, price))
    return min(candidates)[1] if candidates else None


# ============================================================
# MFE / MAE
# ============================================================


def calculate_excursions(
    candles: List[Dict[str, Any]],
    opportunity_timestamp: float,
    entry_price: float,
    direction: str,
    horizon_seconds: int,
) -> Dict[str, Optional[float]]:

    try:

        entry_price = float(
            entry_price
        )

    except Exception:

        return {
            "mfe_pct": None,
            "mae_pct": None,
            "highest_price": None,
            "lowest_price": None,
        }

    if entry_price <= 0:

        return {
            "mfe_pct": None,
            "mae_pct": None,
            "highest_price": None,
            "lowest_price": None,
        }

    start_timestamp = (
        opportunity_timestamp
    )

    end_timestamp = (
        opportunity_timestamp
        + horizon_seconds
    )

    highs = []
    lows = []

    for candle in candles:

        ts = (
            candle_timestamp_seconds(
                candle
            )
        )

        if ts is None:

            continue

        # Include only complete 1m candles wholly inside the window.
        if not (
            start_timestamp <= ts
            and ts + 60 <= end_timestamp
        ):

            continue

        try:

            high = float(
                candle[
                    "high"
                ]
            )

            low = float(
                candle[
                    "low"
                ]
            )

        except Exception:

            continue

        if (
            high > 0
            and low > 0
        ):

            highs.append(
                high
            )

            lows.append(
                low
            )

    if (
        not highs
        or not lows
    ):

        return {
            "mfe_pct": None,
            "mae_pct": None,
            "highest_price": None,
            "lowest_price": None,
        }

    highest = max(
        highs
    )

    lowest = min(
        lows
    )

    direction = (
        str(direction)
        .upper()
        .strip()
    )

    if direction == "LONG":

        mfe = (
            (
                highest
                - entry_price
            )
            / entry_price
        ) * 100.0

        mae = (
            (
                entry_price
                - lowest
            )
            / entry_price
        ) * 100.0

    elif direction == "SHORT":

        mfe = (
            (
                entry_price
                - lowest
            )
            / entry_price
        ) * 100.0

        mae = (
            (
                highest
                - entry_price
            )
            / entry_price
        ) * 100.0

    else:

        mfe = None
        mae = None

    if mfe is not None:

        mfe = max(
            0.0,
            mfe,
        )

    if mae is not None:

        mae = max(
            0.0,
            mae,
        )

    return {
        "mfe_pct":
        mfe,

        "mae_pct":
        mae,

        "highest_price":
        highest,

        "lowest_price":
        lowest,
    }


# ============================================================
# SHORT-TERM BEHAVIOUR
# ============================================================


def calculate_early_behaviour(
    opportunity: Dict[str, Any],
    new_fields: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Gives the memory system information about HOW
    the prediction developed.

    Examples:

    +30s -> +1m -> +5m
    can indicate continuation.

    +30s then negative 5m
    can indicate early reversal.
    """

    def get_return(
        field_name,
    ):

        if field_name in new_fields:

            return new_fields.get(
                field_name
            )

        return opportunity.get(
            field_name
        )

    r30s = get_return(
        "return_30s_pct"
    )

    r1m = get_return(
        "return_1m_pct"
    )

    r5m = get_return(
        "return_5m_pct"
    )

    r10m = get_return(
        "return_10m_pct"
    )

    r30m = get_return(
        "return_30m_pct"
    )

    result = {}

    if r30s is not None:

        result[
            "immediate_move_pct"
        ] = r30s

    if r1m is not None:

        result[
            "early_momentum_pct"
        ] = r1m

    if r5m is not None:

        result[
            "momentum_5m_pct"
        ] = r5m

    if r10m is not None:

        result[
            "momentum_10m_pct"
        ] = r10m

    if r30m is not None:

        result[
            "momentum_30m_pct"
        ] = r30m

    # --------------------------------------------------------
    # EARLY CONTINUATION
    # --------------------------------------------------------

    if (
        r1m is not None
        and r5m is not None
    ):

        result[
            "early_continuation"
        ] = (
            r1m > 0
            and r5m > 0
            and r5m >= r1m
        )

    # --------------------------------------------------------
    # EARLY REVERSAL
    # --------------------------------------------------------

    early_positive = False

    if (
        r30s is not None
        and r30s > 0
    ):

        early_positive = True

    elif (
        r1m is not None
        and r1m > 0
    ):

        early_positive = True

    if (
        early_positive
        and r5m is not None
    ):

        result[
            "early_reversal"
        ] = (
            r5m < 0
        )

    return result


# ============================================================
# CALCULATE OUTCOME FIELDS
# ============================================================


def calculate_outcome_fields(
    opportunity: Dict[str, Any],
    candles: List[Dict[str, Any]],
    now_timestamp: Optional[float] = None,
) -> Dict[str, Any]:

    if now_timestamp is None:

        now_timestamp = (
            utc_now().timestamp()
        )

    opportunity_timestamp = (
        timestamp_seconds(
            opportunity.get(
                "opportunity_time"
            )
        )
    )

    if opportunity_timestamp is None:

        return {}

    try:

        entry_price = float(
            opportunity[
                "entry_price"
            ]
        )

    except Exception:

        return {}

    direction = (
        str(
            opportunity.get(
                "direction",
                "",
            )
        )
        .upper()
        .strip()
    )

    age_seconds = (
        now_timestamp
        - opportunity_timestamp
    )

    fields = {}

    # ========================================================
    # HISTORICAL CHECKPOINTS
    #
    # 30 seconds is deliberately excluded here.
    #
    # Exact 30-second price should come from a live observation.
    # ========================================================

    # Historical checkpoint prices require 1m candles. Larger candles
    # are not exact observations at the requested horizon.
    historical_horizons = [

        "1m",
        "5m",
        "10m",
        "30m",
        "1h",
        "4h",
        "12h",
        "24h",
    ]

    for horizon_name in historical_horizons:

        horizon_seconds = (
            OUTCOME_HORIZONS[
                horizon_name
            ]
        )

        if age_seconds < horizon_seconds:

            continue

        (
            price_field,
            return_field,
            correct_field,
        ) = HORIZON_FIELDS[
            horizon_name
        ]

        if opportunity.get(
            price_field
        ) is not None:

            continue

        future_price = (
            historical_price_at_horizon(
                candles=candles,
                opportunity_timestamp=opportunity_timestamp,
                horizon_seconds=horizon_seconds,
                now_timestamp=now_timestamp,
            )
        )

        if future_price is None:

            continue

        result = directional_return(
            entry_price=entry_price,
            future_price=future_price,
            direction=direction,
        )

        fields[
            price_field
        ] = future_price

        fields[
            return_field
        ] = result

        fields[
            correct_field
        ] = direction_correct(
            result
        )

    # ========================================================
    # MFE / MAE
    # ========================================================

    available_horizon = min(
        max(
            age_seconds,
            0.0,
        ),
        OUTCOME_HORIZONS[
            "24h"
        ],
    )

    # Do not report full-window MFE/MAE from partial history.
    earliest = min((candle_timestamp_seconds(c) for c in candles
                    if candle_timestamp_seconds(c) is not None), default=None)
    latest = max((candle_timestamp_seconds(c) for c in candles
                  if candle_timestamp_seconds(c) is not None), default=None)
    full_window = (earliest is not None and latest is not None
                   and earliest >= opportunity_timestamp
                   and earliest < opportunity_timestamp + 60
                   and latest + 60 >= opportunity_timestamp + available_horizon)
    if available_horizon >= 60 and full_window:

        excursions = (
            calculate_excursions(
                candles=candles,
                opportunity_timestamp=opportunity_timestamp,
                entry_price=entry_price,
                direction=direction,
                horizon_seconds=int(
                    available_horizon
                ),
            )
        )

        if excursions.get(
            "mfe_pct"
        ) is not None:

            fields[
                "max_favorable_excursion_pct"
            ] = excursions[
                "mfe_pct"
            ]

        if excursions.get(
            "mae_pct"
        ) is not None:

            fields[
                "max_adverse_excursion_pct"
            ] = excursions[
                "mae_pct"
            ]

        if excursions.get(
            "highest_price"
        ) is not None:

            fields[
                "highest_price"
            ] = excursions[
                "highest_price"
            ]

        if excursions.get(
            "lowest_price"
        ) is not None:

            fields[
                "lowest_price"
            ] = excursions[
                "lowest_price"
            ]

    # ========================================================
    # EARLY BEHAVIOUR
    # ========================================================

    behaviour = (
        calculate_early_behaviour(
            opportunity,
            fields,
        )
    )

    fields.update(
        behaviour
    )

    return fields


# ============================================================
# IS OUTCOME COMPLETE?
# ============================================================


def outcome_is_complete(
    opportunity: Dict[str, Any],
    new_fields: Dict[str, Any],
) -> bool:

    """
    30-second data is valuable but NOT required to mark
    an opportunity complete.

    This is deliberate.

    If the service restarts during the first 30 seconds,
    we do not want an otherwise useful 24-hour historical
    record permanently stuck as incomplete.
    """

    required_fields = [

        "price_1m",
        "price_5m",
        "price_10m",
        "price_30m",
        "price_1h",
        "price_4h",
        "price_12h",
        "price_24h",
    ]

    for field in required_fields:

        existing = (
            opportunity.get(
                field
            )
        )

        new_value = (
            new_fields.get(
                field
            )
        )

        if (
            existing is None
            and new_value is None
        ):

            return False

    return True


# ============================================================
# CANDLE GRANULARITY
# ============================================================


def choose_tracking_granularity(
    age_seconds: float,
) -> str:

    """
    We keep the shortest practical candle interval
    for short-term learning.
    """

    if age_seconds <= (
        2 * 60 * 60
    ):

        return "1m"

    if age_seconds <= (
        8 * 60 * 60
    ):

        return "5m"

    return "15m"


# ============================================================
# REQUIRED CANDLE LIMIT
# ============================================================


def calculate_required_limit(
    age_seconds: float,
    granularity: str,
) -> int:

    seconds_per_candle = {

        "1m": 60,

        "5m": 300,

        "15m": 900,
    }

    candle_seconds = (
        seconds_per_candle[
            granularity
        ]
    )

    required = int(
        age_seconds
        / candle_seconds
    ) + 30

    return max(
        50,
        min(
            required,
            1000,
        ),
    )


# ============================================================
# UPDATE ONE OUTCOME
# ============================================================


def update_one_outcome(
    conn,
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    opportunity_id = (
        opportunity[
            "opportunity_id"
        ]
    )

    symbol = (
        opportunity[
            "symbol"
        ]
    )

    opportunity_timestamp = (
        timestamp_seconds(
            opportunity.get(
                "opportunity_time"
            )
        )
    )

    if opportunity_timestamp is None:

        return {
            "opportunity_id":
            opportunity_id,

            "updated":
            False,

            "reason":
            "Invalid opportunity timestamp",
        }

    now_timestamp = (
        utc_now().timestamp()
    )

    age_seconds = (
        now_timestamp
        - opportunity_timestamp
    )

    # Historical candle processing begins after 1 minute.

    if age_seconds < 120:

        return {
            "opportunity_id":
            opportunity_id,

            "updated":
            False,

            "reason":
            "Waiting for first historical candle",
        }

    # Fetch the full history once the 24-hour horizon has elapsed.
    # Before then, retain the existing recent-candle checkpoint behaviour.
    if age_seconds >= OUTCOME_HORIZONS["24h"] + 60:
        minute_ms = 60_000
        start_ms = (int(opportunity_timestamp * 1000) // minute_ms) * minute_ms
        # Include the minute containing the 24h target, so its close is available.
        end_ms = start_ms + (24 * 60 + 2) * minute_ms
        candles = get_historical_1m_candles(symbol, start_ms, end_ms)
    else:
        candles = get_candles(symbol=symbol, granularity="1m", limit=1000)

    if not candles:

        return {
            "opportunity_id":
            opportunity_id,

            "updated":
            False,

            "reason":
            "No candle data",
        }

    # Reject incomplete history and avoid deriving excursions from
    # a truncated window. Checkpoints can still be stored independently.
    fields = (
        calculate_outcome_fields(
            opportunity=opportunity,
            candles=candles,
            now_timestamp=now_timestamp,
        )
    )

    # Behaviour is derived from checkpoint values; without any new price
    # checkpoint or excursion, there is no reason to issue another DB write.
    new_price_fields = [key for key in fields if key.startswith("price_")]
    new_excursion_fields = [key for key in fields if key in (
        "max_favorable_excursion_pct", "max_adverse_excursion_pct",
        "highest_price", "lowest_price",
    ) and opportunity.get(key) is None]
    if not new_price_fields and not new_excursion_fields:
        return {
            "opportunity_id": opportunity_id,
            "updated": False,
            "reason": "No new observable outcome fields",
        }

    if not fields:

        return {
            "opportunity_id":
            opportunity_id,

            "updated":
            False,

            "reason":
            "No new outcome fields",
        }

    complete = (
        outcome_is_complete(
            opportunity,
            fields,
        )
    )

    if complete:

        fields[
            "outcome_complete"
        ] = True

    update_outcome(
        conn,
        opportunity_id,
        **fields,
    )

    if complete:

        mark_outcome_complete(
            conn,
            opportunity_id,
        )

    return {
        "opportunity_id":
        opportunity_id,

        "symbol":
        symbol,

        "updated":
        True,

        "complete":
        complete,

        "fields":
        fields,
    }


# ============================================================
# UPDATE ALL PENDING OUTCOMES
# ============================================================


def update_pending_outcomes(
    conn,
    limit: int = 500,
) -> Dict[str, int]:

    pending = (
        get_pending_outcomes(
            conn,
            limit=limit,
        )
    )

    stats = {

        "checked": 0,

        "updated": 0,

        "completed": 0,

        "waiting": 0,

        "errors": 0,
    }

    for opportunity in pending:

        stats[
            "checked"
        ] += 1

        try:

            result = (
                update_one_outcome(
                    conn,
                    opportunity,
                )
            )

            if result.get(
                "updated"
            ):

                stats[
                    "updated"
                ] += 1

            else:

                stats[
                    "waiting"
                ] += 1

            if result.get(
                "complete"
            ):

                stats[
                    "completed"
                ] += 1

        except Exception as exc:

            stats[
                "errors"
            ] += 1

            print(
                "OUTCOME TRACKER ERROR:",
                opportunity.get(
                    "symbol"
                ),
                repr(exc),
                flush=True,
            )

            # One broken symbol must never stop
            # the whole learning engine.

            time.sleep(
                0.25
            )

    return stats


# ============================================================
# STATUS
# ============================================================


def print_outcome_stats(
    stats: Dict[str, int],
):

    print(
        "OUTCOME TRACKER:",
        f"checked={stats.get('checked', 0)}",
        f"updated={stats.get('updated', 0)}",
        f"completed={stats.get('completed', 0)}",
        f"waiting={stats.get('waiting', 0)}",
        f"errors={stats.get('errors', 0)}",
        flush=True,
    )


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- OUTCOME TRACKER V2",
        flush=True,
    )

    print(
        "30 SECOND LIVE CHECKPOINT: READY",
        flush=True,
    )

    print(
        "1 MINUTE OUTCOME: READY",
        flush=True,
    )

    print(
        "5 MINUTE OUTCOME: READY",
        flush=True,
    )

    print(
        "10 MINUTE OUTCOME: READY",
        flush=True,
    )

    print(
        "30 MINUTE OUTCOME: READY",
        flush=True,
    )

    print(
        "1H / 4H / 12H / 24H OUTCOMES: READY",
        flush=True,
    )

    print(
        "MFE / MAE LEARNING: READY",
        flush=True,
    )

    print(
        "EARLY CONTINUATION / REVERSAL: READY",
        flush=True,
    )

    print(
        "REJECTED OPPORTUNITY TRACKING: READY",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )
