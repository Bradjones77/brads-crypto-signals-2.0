import time
import os
import json
import urllib.request
import urllib.error
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# MAIN CONTROLLER
#
# PURPOSE:
#
# Bring together the separate Bot 2.0 engines:
#
# Bitget market data
# Technical analysis
# Market context
# Long-term memory
# Historical pattern matching
# AI analysis
# Confidence calculation
# Signal selection
# Telegram formatting
# Outcome tracking
#
#
# IMPORTANT:
#
# THIS BUILD IS STILL IN DEVELOPMENT MODE.
#
# It does NOT:
#
# - Place trades
# - Modify the existing execution bot
# - Send Telegram messages
# - Start continuous live scanning
# - Require API keys yet
#
# Connections will be added AFTER all files are reviewed.
# ============================================================


BOT_VERSION = "BRADS-SIGNALS-BOT-2.0"

DEVELOPMENT_MODE = True

LIVE_SCANNING_ENABLED = False

TELEGRAM_SENDING_ENABLED = False

AI_CONNECTION_ENABLED = False

DATABASE_CONNECTION_ENABLED = False


# ============================================================
# SIGNAL RULE
# ============================================================


MINIMUM_SIGNAL_CONFIDENCE = 75.0


# ============================================================
# FUTURE SCAN SETTINGS
#
# These will be reviewed before live connection.
# ============================================================


SCAN_INTERVAL_SECONDS = 600

MAX_SIGNALS_PER_BATCH = 5


# ============================================================
# SAFE IMPORTS
#
# During the build stage, some integrations may deliberately
# be unavailable.
#
# main.py should still load so we can test the structure.
# ============================================================


try:

    import technical_analysis

except Exception:

    technical_analysis = None


try:

    import market_context

except Exception:

    market_context = None


try:

    import memory_engine

except Exception:

    memory_engine = None


try:

    import outcome_tracker

except Exception:

    outcome_tracker = None


try:

    import pattern_memory

except Exception:

    pattern_memory = None


try:

    import ai_analyst

except Exception:

    ai_analyst = None


try:

    import confidence_engine

except Exception:

    confidence_engine = None


try:

    import signal_selector

except Exception:

    signal_selector = None


try:

    import telegram_formatter

except Exception:

    telegram_formatter = None


try:

    import bitget_market

except Exception:

    bitget_market = None


# ============================================================
# TIME
# ============================================================


def utc_now():

    return datetime.now(
        timezone.utc
    )


# ============================================================
# MODULE STATUS
# ============================================================


def module_status():

    return {

        "bitget_market":
        bitget_market is not None,

        "technical_analysis":
        technical_analysis is not None,

        "market_context":
        market_context is not None,

        "memory_engine":
        memory_engine is not None,

        "outcome_tracker":
        outcome_tracker is not None,

        "pattern_memory":
        pattern_memory is not None,

        "ai_analyst":
        ai_analyst is not None,

        "confidence_engine":
        confidence_engine is not None,

        "signal_selector":
        signal_selector is not None,

        "telegram_formatter":
        telegram_formatter is not None,
    }


# ============================================================
# BUILD OPPORTUNITY
#
# This is the common structure passed between Bot 2.0 files.
# ============================================================


def build_opportunity(
    symbol: str,
    direction: str,
    current_price: float,
    observed_at=None,
) -> Dict[str, Any]:

    if observed_at is None:

        observed_at = utc_now()

    return {

        "bot_version":
        BOT_VERSION,

        "symbol":
        str(
            symbol
        ).upper(),

        "direction":
        str(
            direction
        ).upper(),

        "current_price":
        float(
            current_price
        ),

        "entry_price":
        float(
            current_price
        ),

        "observed_at":
        observed_at,

        "technical_analysis":
        {},

        "market_context":
        {},

        "memory_analysis":
        {},

        "ai_result":
        {},

        "confidence_result":
        {},

        "selector_result":
        {},

        "telegram_message":
        None,
    }


# ============================================================
# TECHNICAL ANALYSIS STAGE
# ============================================================


def run_technical_stage(
    opportunity: Dict[str, Any],
    multi_timeframe_candles: Dict[str, Any],
) -> Dict[str, Any]:

    if technical_analysis is None:

        opportunity[
            "technical_analysis"
        ] = {}

        return opportunity

    try:

        result = (
            technical_analysis.analyze_symbol(
                multi_timeframe_candles
            )
        )

        opportunity[
            "technical_analysis"
        ] = result or {}

    except Exception as exc:

        opportunity[
            "technical_analysis"
        ] = {

            "error":
            str(
                exc
            )
        }

    return opportunity


# ============================================================
# MARKET CONTEXT STAGE
#
# The complete market-context object can be prepared once per
# scan and then attached to each opportunity.
# ============================================================


def run_market_context_stage(
    opportunity: Dict[str, Any],
    full_market_context: Dict[str, Any],
) -> Dict[str, Any]:

    opportunity[
        "market_context"
    ] = (
        full_market_context
        if isinstance(
            full_market_context,
            dict,
        )
        else {}
    )

    return opportunity


# ============================================================
# HISTORICAL MEMORY STAGE
#
# This remains inactive until the database is connected.
# ============================================================


def run_memory_stage(
    opportunity: Dict[str, Any],
    database_connection=None,
) -> Dict[str, Any]:

    if (
        pattern_memory is None
        or database_connection is None
    ):

        opportunity[
            "memory_analysis"
        ] = {

            "memory_usable":
            False,

            "memory_score":
            None,

            "reason":
            "Historical database not connected yet.",
        }

        return opportunity

    try:

        combined_features = {}

        technical = (
            opportunity.get(
                "technical_analysis",
                {}
            )
            or {}
        )

        market = (
            opportunity.get(
                "market_context",
                {}
            )
            or {}
        )

        if technical_analysis is not None:

            try:

                technical_features = (
                    technical_analysis
                    .build_feature_vector(
                        technical
                    )
                )

                if isinstance(
                    technical_features,
                    dict,
                ):

                    combined_features.update(
                        technical_features
                    )

            except Exception:

                pass

        if market_context is not None:

            try:

                market_features = (
                    market_context
                    .build_context_features(
                        market
                    )
                )

                if isinstance(
                    market_features,
                    dict,
                ):

                    combined_features.update(
                        market_features
                    )

            except Exception:

                pass

        result = (
            pattern_memory
            .analyze_pattern_memory(
                conn=database_connection,
                symbol=opportunity[
                    "symbol"
                ],
                direction=opportunity[
                    "direction"
                ],
                current_features=combined_features,
                before_time=opportunity[
                    "observed_at"
                ],
            )
        )

        opportunity[
            "memory_analysis"
        ] = result or {}

    except Exception as exc:

        opportunity[
            "memory_analysis"
        ] = {

            "memory_usable":
            False,

            "memory_score":
            None,

            "error":
            str(
                exc
            ),
        }

    return opportunity


# ============================================================
# AI STAGE
#
# File 8 deliberately returns unavailable until we connect
# the AI at the final integration stage.
# ============================================================


def run_ai_stage(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    if ai_analyst is None:

        opportunity[
            "ai_result"
        ] = {

            "available":
            False,

            "ai_score":
            None,
        }

        return opportunity

    try:

        result = (
            ai_analyst.analyze_with_ai(
                symbol=opportunity[
                    "symbol"
                ],
                direction=opportunity[
                    "direction"
                ],
                current_price=opportunity[
                    "current_price"
                ],
                technical_analysis=opportunity.get(
                    "technical_analysis",
                    {},
                ),
                market_context=opportunity.get(
                    "market_context",
                    {},
                ),
                memory_analysis=opportunity.get(
                    "memory_analysis",
                    {},
                ),
            )
        )

        opportunity[
            "ai_result"
        ] = result or {}

    except Exception as exc:

        opportunity[
            "ai_result"
        ] = {

            "available":
            False,

            "ai_score":
            None,

            "error":
            str(
                exc
            ),
        }

    return opportunity


# ============================================================
# CONFIDENCE STAGE
# ============================================================


def run_confidence_stage(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    if confidence_engine is None:

        opportunity[
            "confidence_result"
        ] = {

            "final_confidence":
            0.0,

            "eligible":
            False,

            "decision":
            "REJECTED",

            "rejection_reason":
            "Confidence engine unavailable",
        }

        return opportunity

    try:

        result = (
            confidence_engine
            .calculate_final_confidence(
                symbol=opportunity[
                    "symbol"
                ],
                direction=opportunity[
                    "direction"
                ],
                technical_analysis=opportunity.get(
                    "technical_analysis",
                    {},
                ),
                market_context=opportunity.get(
                    "market_context",
                    {},
                ),
                memory_analysis=opportunity.get(
                    "memory_analysis",
                    {},
                ),
                ai_result=opportunity.get(
                    "ai_result",
                    {},
                ),
            )
        )

        opportunity[
            "confidence_result"
        ] = result or {}

    except Exception as exc:

        opportunity[
            "confidence_result"
        ] = {

            "final_confidence":
            0.0,

            "eligible":
            False,

            "decision":
            "REJECTED",

            "rejection_reason":
            str(
                exc
            ),
        }

    return opportunity


# ============================================================
# ANALYSE ONE OPPORTUNITY
#
# This is the core Bot 2.0 reasoning pipeline.
# ============================================================


def analyse_opportunity(
    symbol: str,
    direction: str,
    current_price: float,
    multi_timeframe_candles: Dict[str, Any],
    full_market_context: Dict[str, Any],
    database_connection=None,
    observed_at=None,
) -> Dict[str, Any]:

    opportunity = (
        build_opportunity(
            symbol=symbol,
            direction=direction,
            current_price=current_price,
            observed_at=observed_at,
        )
    )

    opportunity = (
        run_technical_stage(
            opportunity,
            multi_timeframe_candles,
        )
    )

    opportunity = (
        run_market_context_stage(
            opportunity,
            full_market_context,
        )
    )

    opportunity = (
        run_memory_stage(
            opportunity,
            database_connection,
        )
    )

    opportunity = (
        run_ai_stage(
            opportunity
        )
    )

    opportunity = (
        run_confidence_stage(
            opportunity
        )
    )

    return opportunity


# ============================================================
# SELECT BEST SIGNALS
# ============================================================


def select_best_signals(
    opportunities: List[Dict[str, Any]],
    recent_signal_times=None,
) -> Dict[str, Any]:

    if signal_selector is None:

        return {

            "selected":
            [],

            "rejected":
            opportunities,

            "error":
            "Signal selector unavailable",
        }

    return (
        signal_selector.select_signals(
            opportunities=opportunities,
            recent_signal_times=recent_signal_times,
            max_signals=MAX_SIGNALS_PER_BATCH,
        )
    )


# ============================================================
# FORMAT SELECTED SIGNALS
#
# Still does NOT send anything to Telegram.
# ============================================================


def format_selected_signals(
    selected_opportunities: List[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    if telegram_formatter is None:

        return []

    return (
        telegram_formatter
        .format_selected_signals(
            selected_opportunities
        )
    )


# ============================================================
# PROCESS A COMPLETED ANALYSIS BATCH
#
# Input:
# already analysed opportunities
#
# Output:
# selected signals + formatted messages
#
# No Telegram sending occurs.
# ============================================================


def process_analysis_batch(
    opportunities: List[Dict[str, Any]],
    recent_signal_times=None,
) -> Dict[str, Any]:

    selection = (
        select_best_signals(
            opportunities,
            recent_signal_times,
        )
    )

    selected = (
        selection.get(
            "selected",
            []
        )
    )

    formatted = (
        format_selected_signals(
            selected
        )
    )

    return {

        "bot_version":
        BOT_VERSION,

        "processed_at":
        utc_now(),

        "opportunity_count":
        len(
            opportunities
        ),

        "selected_count":
        len(
            selected
        ),

        "selection":
        selection,

        "formatted_signals":
        formatted,
    }


# ============================================================
# FUTURE DATABASE STORAGE
#
# This deliberately does nothing yet.
#
# During final integration this will store EVERY considered
# opportunity:
#
# - signals we send
# - signals below 75
# - signals rejected by evidence gates
# - duplicate/cooldown opportunities
#
# This is essential for unbiased learning.
# ============================================================


def store_analysis_batch(
    batch_result: Dict[str, Any],
    database_connection=None,
):

    if database_connection is None:

        return {

            "stored":
            False,

            "reason":
            "Database connection not configured yet.",
        }

    return {

        "stored":
        False,

        "reason":
        "Final database integration still pending.",
    }


# ============================================================
# FUTURE TELEGRAM SENDER
#
# Deliberately disabled.
# ============================================================


def send_formatted_signals(
    formatted_signals: List[
        Dict[str, Any]
    ],
):

    if not TELEGRAM_SENDING_ENABLED:

        return {

            "sent":
            0,

            "reason":
            "Telegram sending intentionally disabled.",
        }

    # Telegram connection will be added during final
    # integration.

    return {

        "sent":
        0,

        "reason":
        "Telegram integration not configured yet.",
    }


# ============================================================
# FUTURE OUTCOME TRACKING
#
# The actual outcome tracker already exists.
#
# It will be connected after the database + Bitget data
# integration has been fully checked.
# ============================================================


def run_outcome_tracking(
    database_connection=None,
):

    if database_connection is None:

        return {

            "updated":
            0,

            "reason":
            "Database not connected.",
        }

    if outcome_tracker is None:

        return {

            "updated":
            0,

            "reason":
            "Outcome tracker unavailable.",
        }

    return {

        "updated":
        0,

        "reason":
        "Outcome tracking integration deferred until final review.",
    }


# ============================================================
# DEVELOPMENT STATUS
# ============================================================


def development_status():

    status = module_status()

    loaded = sum(
        1
        for available in status.values()
        if available
    )

    total = len(
        status
    )

    return {

        "bot_version":
        BOT_VERSION,

        "development_mode":
        DEVELOPMENT_MODE,

        "modules_loaded":
        loaded,

        "modules_expected":
        total,

        "modules":
        status,

        "minimum_signal_confidence":
        MINIMUM_SIGNAL_CONFIDENCE,

        "live_scanning":
        LIVE_SCANNING_ENABLED,

        "telegram_sending":
        TELEGRAM_SENDING_ENABLED,

        "ai_connection":
        AI_CONNECTION_ENABLED,

        "database_connection":
        DATABASE_CONNECTION_ENABLED,

        "trade_execution":
        False,
    }


# ============================================================
# PRINT STARTUP STATUS
# ============================================================


def print_startup_status():

    status = (
        development_status()
    )

    print(
        "=" * 60,
        flush=True,
    )

    print(
        BOT_VERSION,
        flush=True,
    )

    print(
        "=" * 60,
        flush=True,
    )

    print(
        "DEVELOPMENT MODE:",
        status[
            "development_mode"
        ],
        flush=True,
    )

    print(
        "MODULES LOADED:",
        f"{status['modules_loaded']}/"
        f"{status['modules_expected']}",
        flush=True,
    )

    for module_name, available in (
        status[
            "modules"
        ].items()
    ):

        print(
            f"{module_name}: "
            f"{'READY' if available else 'NOT LOADED'}",
            flush=True,
        )

    print(
        "MINIMUM SIGNAL CONFIDENCE:",
        MINIMUM_SIGNAL_CONFIDENCE,
        flush=True,
    )

    print(
        "0-74.99: DO NOT SEND",
        flush=True,
    )

    print(
        "75-100: ELIGIBLE",
        flush=True,
    )

    print(
        "LIVE SCANNING: DISABLED",
        flush=True,
    )

    print(
        "TELEGRAM SENDING: DISABLED",
        flush=True,
    )

    print(
        "AI API CONNECTION: DEFERRED",
        flush=True,
    )

    print(
        "DATABASE CONNECTION: DEFERRED",
        flush=True,
    )

    print(
        "BITGET KEYS: NOT REQUIRED YET",
        flush=True,
    )

    print(
        "TRADE EXECUTION CODE: NONE",
        flush=True,
    )

    print(
        "=" * 60,
        flush=True,
    )


# ============================================================
# DEVELOPMENT SELF TEST
#
# Running:
#
# python main.py
#
# will ONLY print the development status.
#
# It will NOT scan, send Telegram messages or place trades.
# ============================================================


def development_self_test():

    print_startup_status()

    print(
        "\nBOT 2.0 CONTROLLER STRUCTURE: READY",
        flush=True,
    )

    print(
        "LIVE CONNECTIONS WILL BE ADDED "
        "AFTER FINAL CROSS-FILE REVIEW.",
        flush=True,
    )


# ============================================================
# EXPLICIT TELEGRAM CONNECTION TEST ONLY
# This does not enable market scanning or signal delivery.
# Set SIGNALS2_TELEGRAM_TEST_ON_START=true for ONE deployment,
# then remove/reset it to avoid another message on restart.
# ============================================================


def send_telegram_connection_test():
    token = os.environ.get("SIGNALS2_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("SIGNALS2_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("TELEGRAM TEST: missing token or chat ID", flush=True)
        return False
    if not chat_id.lstrip("-").isdigit():
        print("TELEGRAM TEST: invalid chat ID", flush=True)
        return False

    payload = json.dumps({
        "chat_id": chat_id,
        "text": "Signals Bot 2.0: Telegram connection test successful. "
                "This is NOT a trading signal. Live scanning and signal sending remain disabled.",
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.loads(response.read(65536).decode("utf-8"))
        if result.get("ok") is True:
            print("TELEGRAM TEST: message sent successfully", flush=True)
            return True
        print("TELEGRAM TEST: Telegram rejected the message", flush=True)
    except urllib.error.HTTPError as exc:
        # Do not print response body or URL: URL contains the secret token.
        print("TELEGRAM TEST: HTTP error status", exc.code, flush=True)
    except Exception as exc:
        # Avoid printing exception text, which can contain the token URL.
        print("TELEGRAM TEST: connection failed (" + type(exc).__name__ + ")", flush=True)
    return False


# ============================================================
# MAIN
# ============================================================


if __name__ == "__main__":

    try:

        development_self_test()

        if os.environ.get("SIGNALS2_TELEGRAM_TEST_ON_START", "").lower().strip() == "true":
            send_telegram_connection_test()

        # One-shot read-only market data diagnostic. Does not scan continuously,
        # calculate signals, send Telegram messages, or place trades.
        if os.environ.get("SIGNALS2_BITGET_TEST_ON_START", "").lower().strip() == "true":
            print("BITGET DIAGNOSTIC: starting public read-only test", flush=True)
            if bitget_market is None:
                print("BITGET DIAGNOSTIC: module unavailable", flush=True)
            else:
                try:
                    passed = bitget_market.bitget_public_self_test()
                    print("BITGET DIAGNOSTIC: " + ("PASS" if passed else "FAIL"), flush=True)
                except Exception as exc:
                    # Avoid dumping request URLs or private credentials into logs.
                    print("BITGET DIAGNOSTIC: FAIL (" + type(exc).__name__ + ")", flush=True)


    except KeyboardInterrupt:

        print(
            "\nStopped.",
            flush=True,
        )

    except Exception:

        print(
            "\nDEVELOPMENT SELF TEST ERROR:",
            flush=True,
        )

        traceback.print_exc()
