import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# TELEGRAM SIGNAL FORMATTER V1
#
# PURPOSE:
#
# Convert an approved Signals Bot 2.0 opportunity into a
# clean Telegram message.
#
#
# SIGNAL FORMAT:
#
# TRADE SIGNAL
#
# LONG
# (BTCUSDT)
#
# Confidence: 82%
# Time: 08:42 UTC
# Entry: $67452.30
#
#
# IMPORTANT:
#
# - Only formats messages
# - Does NOT connect to Telegram
# - Does NOT send messages
# - Does NOT place trades
# - Does NOT access Bitget
# - Does NOT access OpenAI
# - Does NOT calculate confidence
#
#
# TP / SL are intentionally NOT generated here.
#
# The execution bot will eventually handle its own
# protection orders.
# ============================================================


TELEGRAM_FORMATTER_VERSION = "signals2-telegram-formatter-v2-approval-gates"

MIN_CONFIDENCE = 75.0


# ============================================================
# HELPERS
# ============================================================


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


def normalize_symbol(
    symbol,
) -> str:

    return (
        str(
            symbol or ""
        )
        .upper()
        .strip()
    )


def normalize_direction(
    direction,
) -> str:

    direction = (
        str(
            direction or ""
        )
        .upper()
        .strip()
    )

    if direction not in {
        "LONG",
        "SHORT",
    }:

        return "UNKNOWN"

    return direction


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

        return value.astimezone(
            timezone.utc
        )

    if isinstance(
        value,
        (int, float),
    ):

        timestamp = float(
            value
        )

        if timestamp > 10_000_000_000:

            timestamp /= 1000.0

        try:

            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

        except Exception:

            return None

    if isinstance(
        value,
        str,
    ):

        try:

            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:

                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except Exception:

            return None

    return None


# ============================================================
# PRICE FORMATTING
#
# Crypto prices can range from:
#
# BTC = tens of thousands
#
# to
#
# small altcoins = fractions of a cent.
#
# We preserve useful precision automatically.
# ============================================================


def format_price(
    price,
) -> str:

    price = safe_float(
        price
    )

    if (
        price is None
        or price <= 0
    ):

        return "N/A"

    if price >= 10000:

        return (
            f"${price:,.2f}"
        )

    if price >= 100:

        return (
            f"${price:,.3f}"
        )

    if price >= 1:

        return (
            f"${price:,.4f}"
        )

    if price >= 0.1:

        return (
            f"${price:.5f}"
        )

    if price >= 0.01:

        return (
            f"${price:.6f}"
        )

    if price >= 0.001:

        return (
            f"${price:.7f}"
        )

    return (
        f"${price:.8f}"
    )


# ============================================================
# CONFIDENCE FORMATTING
# ============================================================


def format_confidence(
    confidence,
) -> str:

    confidence = safe_float(
        confidence
    )

    if confidence is None:

        return "N/A"

    confidence = max(
        0.0,
        min(
            100.0,
            confidence,
        ),
    )

    # Keep one decimal only when needed.

    if float(
        confidence
    ).is_integer():

        return (
            f"{int(confidence)}%"
        )

    return (
        f"{confidence:.1f}%"
    )


# ============================================================
# TIME FORMATTING
# ============================================================


def format_utc_time(
    value=None,
) -> str:

    timestamp = (
        ensure_datetime(
            value
        )
    )

    if timestamp is None:

        timestamp = datetime.now(
            timezone.utc
        )

    return timestamp.strftime(
        "%H:%M UTC"
    )


# ============================================================
# EXTRACT CONFIDENCE
# ============================================================


def extract_confidence(
    opportunity: Dict[str, Any],
) -> Optional[float]:

    confidence_result = (
        opportunity.get(
            "confidence_result"
        )
    )

    if isinstance(
        confidence_result,
        dict,
    ):

        confidence = safe_float(
            confidence_result.get(
                "final_confidence"
            )
        )

        if confidence is not None:

            return confidence

    return safe_float(
        opportunity.get(
            "final_confidence"
        )
    )


# ============================================================
# EXTRACT PRICE
# ============================================================


def extract_price(
    opportunity: Dict[str, Any],
) -> Optional[float]:

    for field in [

        "current_price",

        "entry_price",

        "price",

    ]:

        price = safe_float(
            opportunity.get(
                field
            )
        )

        if (
            price is not None
            and price > 0
        ):

            return price

    return None


# ============================================================
# EXTRACT SIGNAL TIME
# ============================================================


def extract_signal_time(
    opportunity: Dict[str, Any],
):

    for field in [

        "observed_at",

        "opportunity_time",

        "created_at",

        "timestamp",

    ]:

        value = (
            opportunity.get(
                field
            )
        )

        if value is not None:

            parsed = (
                ensure_datetime(
                    value
                )
            )

            if parsed is not None:

                return parsed

    return None


# ============================================================
# VALIDATE SIGNAL BEFORE FORMATTING
#
# This repeats the 75 confidence protection.
#
# Even though signal_selector.py already checks it,
# the Telegram layer will not format a sub-75 signal.
# ============================================================


def validate_signal(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    reasons = []

    if not isinstance(
        opportunity,
        dict,
    ):

        return {

            "valid":
            False,

            "reasons":
            [
                "Signal is not a dictionary"
            ],
        }

    symbol = normalize_symbol(
        opportunity.get(
            "symbol"
        )
    )

    direction = normalize_direction(
        opportunity.get(
            "direction"
        )
    )

    confidence = (
        extract_confidence(
            opportunity
        )
    )

    price = (
        extract_price(
            opportunity
        )
    )

    # Format only opportunities actually selected by signal_selector.py.
    # A high numeric score alone does not authorize signal delivery.
    if opportunity.get("selector_status") != "SELECTED":
        reasons.append("Opportunity was not selected by signal selector")

    confidence_result = opportunity.get("confidence_result")
    if not isinstance(confidence_result, dict):
        reasons.append("Missing confidence engine result")
    else:
        if confidence_result.get("eligible") is not True:
            reasons.append("Confidence engine did not mark signal eligible")
        if str(confidence_result.get("decision", "")).strip().upper() != "ELIGIBLE":
            reasons.append("Confidence engine decision is not ELIGIBLE")
        gates = confidence_result.get("evidence_gates")
        if not isinstance(gates, dict) or gates.get("passed") is not True:
            reasons.append("Confidence evidence gates did not pass")

    if extract_signal_time(opportunity) is None:
        reasons.append("Missing or invalid signal timestamp")

    if not symbol:

        reasons.append(
            "Missing symbol"
        )

    if direction == "UNKNOWN":

        reasons.append(
            "Invalid direction"
        )

    if confidence is None:

        reasons.append(
            "Missing confidence"
        )

    elif confidence < MIN_CONFIDENCE:

        reasons.append(
            (
                f"Confidence {confidence:.2f} "
                f"is below {MIN_CONFIDENCE:.0f}"
            )
        )

    if (
        price is None
        or price <= 0
    ):

        reasons.append(
            "Invalid entry price"
        )

    return {

        "valid":
        len(
            reasons
        )
        == 0,

        "reasons":
        reasons,

        "symbol":
        symbol,

        "direction":
        direction,

        "confidence":
        confidence,

        "price":
        price,
    }


# ============================================================
# BUILD STANDARD SIGNAL MESSAGE
# ============================================================


def format_trade_signal(
    opportunity: Dict[str, Any],
) -> Optional[str]:

    validation = (
        validate_signal(
            opportunity
        )
    )

    if not validation[
        "valid"
    ]:

        return None

    symbol = (
        validation[
            "symbol"
        ]
    )

    direction = (
        validation[
            "direction"
        ]
    )

    confidence = (
        validation[
            "confidence"
        ]
    )

    price = (
        validation[
            "price"
        ]
    )

    signal_time = (
        extract_signal_time(
            opportunity
        )
    )

    message = (

        "TRADE SIGNAL\n"
        "\n"

        f"{direction}\n"

        f"({symbol})\n"
        "\n"

        f"Confidence: "
        f"{format_confidence(confidence)}\n"

        f"Time: "
        f"{format_utc_time(signal_time)}\n"

        f"Entry: "
        f"{format_price(price)}"
    )

    return message


# ============================================================
# OPTIONAL DETAILED SIGNAL
#
# This is for the future analysis/testing channel.
#
# It can show WHY the signal scored highly.
#
# It is deliberately separate from the normal clean signal.
# ============================================================


def format_detailed_signal(
    opportunity: Dict[str, Any],
) -> Optional[str]:

    basic_message = (
        format_trade_signal(
            opportunity
        )
    )

    if basic_message is None:

        return None

    confidence_result = (
        opportunity.get(
            "confidence_result",
            {}
        )
        or {}
    )

    component_scores = (
        confidence_result.get(
            "component_scores",
            {}
        )
        or {}
    )

    technical = (
        safe_float(
            component_scores.get(
                "technical"
            )
        )
    )

    market = (
        safe_float(
            component_scores.get(
                "market"
            )
        )
    )

    memory = (
        safe_float(
            component_scores.get(
                "memory"
            )
        )
    )

    ai = (
        safe_float(
            component_scores.get(
                "ai"
            )
        )
    )

    details = []

    if technical is not None:

        details.append(
            f"Technical: "
            f"{technical:.1f}"
        )

    if market is not None:

        details.append(
            f"Market: "
            f"{market:.1f}"
        )

    if memory is not None:

        details.append(
            f"Memory: "
            f"{memory:.1f}"
        )

    if ai is not None:

        details.append(
            f"AI: "
            f"{ai:.1f}"
        )

    if not details:

        return basic_message

    return (

        basic_message

        + "\n\n"

        + "ANALYSIS\n"

        + "\n".join(
            details
        )
    )


# ============================================================
# FORMAT REJECTION FOR INTERNAL LOGS
#
# Rejected opportunities will NOT go to the normal
# Telegram signal channel.
#
# This is only useful for future debugging/testing.
# ============================================================


def format_rejection(
    opportunity: Dict[str, Any],
    reason: str,
) -> str:

    symbol = normalize_symbol(
        opportunity.get(
            "symbol"
        )
    )

    direction = normalize_direction(
        opportunity.get(
            "direction"
        )
    )

    confidence = (
        extract_confidence(
            opportunity
        )
    )

    confidence_text = (
        format_confidence(
            confidence
        )
        if confidence is not None
        else "N/A"
    )

    return (

        "SIGNAL REJECTED\n"
        "\n"

        f"Symbol: {symbol or 'UNKNOWN'}\n"

        f"Direction: {direction}\n"

        f"Confidence: {confidence_text}\n"

        f"Reason: {reason}"
    )


# ============================================================
# BUILD MESSAGE RECORD
#
# This gives the future Telegram sender a clean structure.
# ============================================================


def build_signal_message_record(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    validation = (
        validate_signal(
            opportunity
        )
    )

    if not validation[
        "valid"
    ]:

        return {

            "ready":
            False,

            "formatter_version":
            TELEGRAM_FORMATTER_VERSION,

            "message":
            None,

            "errors":
            validation[
                "reasons"
            ],
        }

    message = (
        format_trade_signal(
            opportunity
        )
    )

    return {

        "ready":
        True,

        "formatter_version":
        TELEGRAM_FORMATTER_VERSION,

        "symbol":
        validation[
            "symbol"
        ],

        "direction":
        validation[
            "direction"
        ],

        "confidence":
        validation[
            "confidence"
        ],

        "entry_price":
        validation[
            "price"
        ],

        "signal_time":
        extract_signal_time(
            opportunity
        ),

        "message":
        message,

        "errors":
        [],
    }


# ============================================================
# FORMAT MULTIPLE SELECTED SIGNALS
# ============================================================


def format_selected_signals(
    selected_opportunities,
):

    if not isinstance(
        selected_opportunities,
        list,
    ):

        return []

    results = []

    for opportunity in (
        selected_opportunities
    ):

        if not isinstance(
            opportunity,
            dict,
        ):

            continue

        record = (
            build_signal_message_record(
                opportunity
            )
        )

        results.append(
            record
        )

    return results


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    example = {

        "selector_status": "SELECTED",
        "confidence_result": {
            "final_confidence": 82.4,
            "eligible": True,
            "decision": "ELIGIBLE",
            "evidence_gates": {"passed": True, "reasons": []},
        },

        "symbol":
        "BTCUSDT",

        "direction":
        "LONG",

        "current_price":
        67452.30,

        "final_confidence":
        82.4,

        "observed_at":
        datetime.now(
            timezone.utc
        ),
    }

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- TELEGRAM FORMATTER",
        flush=True,
    )

    print(
        "MINIMUM CONFIDENCE:",
        MIN_CONFIDENCE,
        flush=True,
    )

    print(
        "TP / SL GENERATION: DISABLED",
        flush=True,
    )

    print(
        "TELEGRAM CONNECTION: NOT ADDED YET",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )

    print(
        "\nEXAMPLE MESSAGE:\n",
        flush=True,
    )

    print(
        format_trade_signal(
            example
        ),
        flush=True,
    )
