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
                symbol=opportunity["symbol"],
                multi_timeframe_candles=multi_timeframe_candles
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




# ============================================================
# STEP 3: OPT-IN, ONE-SHOT, READ-ONLY INTEGRATION DIAGNOSTIC
# No database connection, AI API, Telegram network call, or trading.
# ============================================================
def run_read_only_integration_diagnostic():
    prefix = "INTEGRATION DIAGNOSTIC: "
    print(prefix + "START (BTCUSDT/ETHUSDT; no sends or trades)", flush=True)
    required = (bitget_market, technical_analysis, market_context,
                confidence_engine, signal_selector, telegram_formatter)
    if not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED or any(m is None for m in required):
        print(prefix + "FAIL (safety flag or required module)", flush=True)
        return False
    try:
        frames = ("5m", "15m", "30m", "1H", "4H", "1D")
        analyses, candle_sets, prices = {}, {}, {}
        for symbol in ("BTCUSDT", "ETHUSDT"):
            candles = bitget_market.get_multi_timeframe_candles(
                symbol=symbol, timeframes=frames, limit=200)
            counts = {frame: len(candles.get(frame, [])) for frame in frames}
            print(prefix + symbol + " candle counts " + str(counts), flush=True)
            if any(n < 55 for n in counts.values()):
                raise ValueError(symbol + " insufficient closed candle history")
            analysis = technical_analysis.analyze_symbol(
                symbol=symbol, multi_timeframe_candles=candles)
            if not all(analysis.get("timeframes", {}).get(frame, {}).get("valid") for frame in frames):
                raise ValueError(symbol + " invalid technical timeframe")
            last = candles["5m"][-1]
            price = float(last["close"])
            if price <= 0:
                raise ValueError(symbol + " invalid last closed price")
            analyses[symbol], candle_sets[symbol], prices[symbol] = analysis, candles, price
        full_context = market_context.build_market_context(
            btc_analysis=analyses["BTCUSDT"], eth_analysis=analyses["ETHUSDT"],
            all_symbol_analyses=list(analyses.values()))
        opportunities = []
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for direction in ("LONG", "SHORT"):
                coin_context = market_context.build_coin_market_context(
                    coin_analysis=analyses[symbol], btc_analysis=analyses["BTCUSDT"],
                    market_context=full_context, direction=direction)
                # Invoke the actual controller stages; memory/AI deliberately deferred.
                opportunity = analyse_opportunity(
                    symbol=symbol, direction=direction, current_price=prices[symbol],
                    multi_timeframe_candles=candle_sets[symbol],
                    full_market_context=coin_context, database_connection=None)
                confidence = opportunity.get("confidence_result", {})
                if not isinstance(confidence, dict) or confidence.get("component_scores", {}).get("technical") is None:
                    raise ValueError(symbol + " " + direction + " confidence stage failed")
                if confidence.get("eligible") and (float(confidence.get("final_confidence", 0)) < 75
                                                  or confidence.get("evidence_gates", {}).get("passed") is not True):
                    raise ValueError("Confidence safety gate violation")
                opportunities.append(opportunity)
                print(prefix + symbol + " " + direction + " " + json.dumps({
                    "score": confidence.get("final_confidence"),
                    "decision": confidence.get("decision"),
                    "eligible": confidence.get("eligible"),
                    "gate_reasons": confidence.get("evidence_gates", {}).get("reasons"),
                    "rejection_reason": confidence.get("rejection_reason")}, default=str), flush=True)
        result = process_analysis_batch(opportunities, recent_signal_times={})
        selected = result.get("selection", {}).get("selected", [])
        formatted = result.get("formatted_signals", [])
        if result.get("opportunity_count") != 4 or result.get("selected_count") != len(selected):
            raise ValueError("Selector batch count mismatch")
        if len(formatted) > len(selected):
            raise ValueError("Formatter output count exceeds selected count")
        for opportunity in selected:
            conf = opportunity.get("confidence_result", {})
            if (float(conf.get("final_confidence", 0)) < 75 or
                    conf.get("eligible") is not True or
                    conf.get("evidence_gates", {}).get("passed") is not True):
                raise ValueError("Selected signal violates confidence gate")
        print(prefix + "selection " + json.dumps({
            "considered": len(opportunities), "selected": len(selected),
            "formatted": len(formatted)}, default=str), flush=True)
        print(prefix + "PASS (one shot; read only; no signal sent; no trade)", flush=True)
        return True
    except Exception as exc:
        print(prefix + "FAIL (" + type(exc).__name__ + ": " + str(exc) + ")", flush=True)
        return False


def run_read_only_database_diagnostic():
    """One-shot PostgreSQL connectivity check; no schema changes or data writes."""
    prefix = "DATABASE DIAGNOSTIC: "
    print(prefix + "START (read only; no writes)", flush=True)
    database_url = os.environ.get("SIGNALS2_DATABASE_URL", "").strip()
    if not database_url:
        print(prefix + "FAIL (SIGNALS2_DATABASE_URL is missing)", flush=True)
        return False
    connection = None
    try:
        import psycopg2
        # Set read-only before the first query; do not log connection details.
        connection = psycopg2.connect(database_url, connect_timeout=8)
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        if result != (1,):
            raise RuntimeError("Unexpected database response")
        print(prefix + "PASS (SELECT 1; read only; no data written)", flush=True)
        return True
    except Exception as exc:
        # Never print exception messages: they may include database host or credentials.
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.rollback()
                connection.close()
            except Exception:
                pass


# ============================================================
# STEP 4: OPT-IN, ONE-SHOT MEMORY SCHEMA INITIALIZATION
# Creates the four Signals 2.0 tables and indexes ONLY.
# Does not store opportunities, fetch prices, send or trade.
# ============================================================
def run_memory_schema_diagnostic():
    prefix = "MEMORY SCHEMA DIAGNOSTIC: "
    print(prefix + "START (schema only; no opportunity data)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or memory_engine is None):
        print(prefix + "FAIL (safety flag or memory module unavailable)", flush=True)
        return False
    connection = None
    try:
        connection = memory_engine.connect()
        memory_engine.ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name IN (
                    'signals2_opportunities', 'signals2_outcomes',
                    'signals2_market_snapshots', 'signals2_model_versions')
            """)
            names = {row[0] for row in cursor.fetchall()}
        if names != {'signals2_opportunities', 'signals2_outcomes',
                     'signals2_market_snapshots', 'signals2_model_versions'}:
            raise RuntimeError("Expected Signals 2.0 tables not all present")
        print(prefix + "PASS (4 tables verified; no opportunity data written)", flush=True)
        return True
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        # Do not log exception details; they could contain connection secrets.
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


if __name__ == "__main__":

    try:

        development_self_test()

        if os.environ.get("SIGNALS2_MEMORY_SCHEMA_TEST_ON_START", "").lower().strip() == "true":
            run_memory_schema_diagnostic()

        if os.environ.get("SIGNALS2_DATABASE_TEST_ON_START", "").lower().strip() == "true":
            run_read_only_database_diagnostic()

        if os.environ.get("SIGNALS2_INTEGRATION_TEST_ON_START", "").lower().strip() == "true":
            run_read_only_integration_diagnostic()

        if os.environ.get("SIGNALS2_TELEGRAM_TEST_ON_START", "").lower().strip() == "true":
            send_telegram_connection_test()

        # One-shot technical-analysis diagnostic; never sends signals or trades.
        if os.environ.get("SIGNALS2_TECHNICAL_TEST_ON_START", "").lower().strip() == "true":
            print("TECHNICAL DIAGNOSTIC: starting BTCUSDT read-only analysis", flush=True)
            if bitget_market is None or technical_analysis is None:
                print("TECHNICAL DIAGNOSTIC: FAIL (module unavailable)", flush=True)
            else:
                try:
                    frames = ("5m", "15m", "30m", "1H", "4H", "1D")
                    candles = bitget_market.get_multi_timeframe_candles(
                        symbol="BTCUSDT", timeframes=frames, limit=200
                    )
                    counts = {frame: len(candles.get(frame, [])) for frame in frames}
                    print("TECHNICAL DIAGNOSTIC: candle counts " + str(counts), flush=True)
                    if any(counts[frame] < 55 for frame in frames):
                        raise ValueError("Missing or insufficient closed candle history")
                    analysis = technical_analysis.analyze_symbol(
                        symbol="BTCUSDT", multi_timeframe_candles=candles
                    )
                    timeframe_results = analysis.get("timeframes", {})
                    valid = {frame: bool(timeframe_results.get(frame, {}).get("valid")) for frame in frames}
                    alignment = analysis.get("multi_timeframe", {})
                    print("TECHNICAL DIAGNOSTIC: valid timeframes " + str(valid), flush=True)
                    print("TECHNICAL DIAGNOSTIC: alignment " + str(alignment.get("overall")), flush=True)
                    if not all(valid.values()) or alignment.get("valid_timeframes") != len(frames):
                        raise ValueError("Technical analysis did not validate all timeframes")
                    if analysis.get("price") is None:
                        raise ValueError("No analyzed price")
                    print("TECHNICAL DIAGNOSTIC: PASS", flush=True)
                except Exception as exc:
                    print("TECHNICAL DIAGNOSTIC: FAIL (" + type(exc).__name__ + ")", flush=True)

        # One-shot confidence diagnostic: public candles only; no signals or trades.
        if os.environ.get("SIGNALS2_CONFIDENCE_TEST_ON_START", "").lower().strip() == "true":
            print("CONFIDENCE DIAGNOSTIC: starting read-only BTC/ETH analysis", flush=True)
            if any(module is None for module in (bitget_market, technical_analysis, market_context, confidence_engine)):
                print("CONFIDENCE DIAGNOSTIC: FAIL (required module unavailable)", flush=True)
            else:
                try:
                    frames = ("5m", "15m", "30m", "1H", "4H", "1D")
                    analyses = {}
                    for symbol in ("BTCUSDT", "ETHUSDT"):
                        candles = bitget_market.get_multi_timeframe_candles(
                            symbol=symbol, timeframes=frames, limit=200
                        )
                        counts = {frame: len(candles.get(frame, [])) for frame in frames}
                        print("CONFIDENCE DIAGNOSTIC: " + symbol + " candle counts " + str(counts), flush=True)
                        if any(count < 55 for count in counts.values()):
                            raise ValueError(symbol + " insufficient candle history")
                        analysis = technical_analysis.analyze_symbol(
                            symbol=symbol, multi_timeframe_candles=candles
                        )
                        if not all(analysis.get("timeframes", {}).get(frame, {}).get("valid") for frame in frames):
                            raise ValueError(symbol + " invalid timeframe analysis")
                        analyses[symbol] = analysis
                    full_context = market_context.build_market_context(
                        btc_analysis=analyses["BTCUSDT"],
                        eth_analysis=analyses["ETHUSDT"],
                        all_symbol_analyses=list(analyses.values()),
                    )
                    for direction in ("LONG", "SHORT"):
                        coin_context = market_context.build_coin_market_context(
                            coin_analysis=analyses["BTCUSDT"],
                            btc_analysis=analyses["BTCUSDT"],
                            market_context=full_context,
                            direction=direction,
                        )
                        result = confidence_engine.calculate_final_confidence(
                            symbol="BTCUSDT", direction=direction,
                            technical_analysis=analyses["BTCUSDT"],
                            market_context=coin_context,
                            memory_analysis={"memory_usable": False},
                            ai_result={"available": False},
                        )
                        print("CONFIDENCE DIAGNOSTIC: " + direction + " " + json.dumps({
                            "score": result.get("final_confidence"),
                            "decision": result.get("decision"),
                            "eligible": result.get("eligible"),
                            "components": result.get("component_scores"),
                            "quality": result.get("component_quality"),
                            "gate_reasons": result.get("evidence_gates", {}).get("reasons"),
                            "rejection_reason": result.get("rejection_reason"),
                        }, default=str), flush=True)
                        if result.get("component_scores", {}).get("technical") is None:
                            raise ValueError("No technical score for " + direction)
                        if result.get("component_scores", {}).get("market") is None:
                            raise ValueError("No market score for " + direction)
                        if result.get("eligible") != confidence_engine.signal_is_eligible(result):
                            raise ValueError("Eligibility mismatch for " + direction)
                        if result.get("eligible") and result.get("final_confidence", 0) < 75.0:
                            raise ValueError("Threshold violation for " + direction)
                    print("CONFIDENCE DIAGNOSTIC: PASS (calculation only; no signal sent)", flush=True)
                except Exception as exc:
                    print("CONFIDENCE DIAGNOSTIC: FAIL (" + type(exc).__name__ + ": " + str(exc) + ")", flush=True)

        # One-shot selector diagnostic: synthetic opportunities only; no messages or trades.
        if os.environ.get("SIGNALS2_SELECTOR_TEST_ON_START", "").lower().strip() == "true":
            print("SELECTOR DIAGNOSTIC: starting synthetic safety checks", flush=True)
            if signal_selector is None:
                print("SELECTOR DIAGNOSTIC: FAIL (module unavailable)", flush=True)
            else:
                try:
                    from datetime import timedelta
                    now = utc_now()

                    def sample(symbol="BTCUSDT", direction="LONG", score=75.0,
                               eligible=True, decision="ELIGIBLE", gate_passed=True,
                               observed_at=None):
                        return {
                            "symbol": symbol, "direction": direction,
                            "current_price": 100.0,
                            "observed_at": now if observed_at is None else observed_at,
                            "confidence_result": {
                                "final_confidence": score, "eligible": eligible,
                                "decision": decision,
                                "evidence_gates": {"passed": gate_passed,
                                                   "reasons": [] if gate_passed else ["Synthetic gate failure"]},
                            },
                        }

                    checks = []
                    def check(name, condition):
                        checks.append((name, bool(condition)))
                        print("SELECTOR DIAGNOSTIC: " + name + " " +
                              ("PASS" if condition else "FAIL"), flush=True)

                    evaluate = signal_selector.evaluate_opportunity
                    check("below 75 rejected", not evaluate(sample(score=74.99), now=now)["selected"])
                    check("exactly 75 eligible", evaluate(sample(score=75.0), now=now)["selected"])
                    check("engine ineligible rejected", not evaluate(sample(eligible=False), now=now)["selected"])
                    check("contradictory decision rejected", not evaluate(sample(decision="REJECTED"), now=now)["selected"])
                    check("failed evidence gate rejected", not evaluate(sample(gate_passed=False), now=now)["selected"])
                    missing = sample()
                    missing.pop("observed_at")
                    check("missing timestamp rejected", not evaluate(missing, now=now)["selected"])
                    check("stale opportunity rejected", not evaluate(
                        sample(observed_at=now - timedelta(seconds=181)), now=now)["selected"])
                    check("cooldown rejected", not evaluate(
                        sample(), recent_signal_times={"BTCUSDT:LONG": now}, now=now)["selected"])
                    batch = signal_selector.select_signals(
                        [sample(score=76), sample(score=80)], now=now)
                    check("same-batch duplicate rejected", batch["selected_count"] == 1 and
                          batch["rejected_count"] == 1 and
                          batch["selected"][0]["confidence_result"]["final_confidence"] == 80)
                    check("opposite directions distinct", signal_selector.select_signals(
                        [sample(direction="LONG"), sample(direction="SHORT")], now=now)["selected_count"] == 2)
                    passed = sum(result for _, result in checks)
                    print("SELECTOR DIAGNOSTIC: " + ("PASS" if passed == len(checks) else "FAIL") +
                          " (" + str(passed) + "/" + str(len(checks)) +
                          "; synthetic only; no signal sent)", flush=True)
                except Exception as exc:
                    print("SELECTOR DIAGNOSTIC: FAIL (" + type(exc).__name__ + ": " + str(exc) + ")", flush=True)

        # One-shot formatter diagnostic: synthetic data only; no Telegram calls or trades.
        if os.environ.get("SIGNALS2_FORMATTER_TEST_ON_START", "").lower().strip() == "true":
            print("FORMATTER DIAGNOSTIC: starting synthetic approval checks", flush=True)
            if telegram_formatter is None:
                print("FORMATTER DIAGNOSTIC: FAIL (module unavailable)", flush=True)
            else:
                try:
                    now = utc_now()

                    def formatter_sample(score=75.0, selected=True, eligible=True,
                                         decision="ELIGIBLE", gate_passed=True):
                        return {
                            "symbol": "BTCUSDT", "direction": "LONG",
                            "entry_price": 67452.30, "observed_at": now,
                            "selector_status": "SELECTED" if selected else "NOT_SELECTED",
                            "confidence_result": {
                                "final_confidence": score, "eligible": eligible,
                                "decision": decision,
                                "evidence_gates": {"passed": gate_passed,
                                                   "reasons": [] if gate_passed else ["Synthetic failure"]},
                            },
                        }

                    checks = []

                    def formatter_check(name, condition):
                        passed = bool(condition)
                        checks.append(passed)
                        print("FORMATTER DIAGNOSTIC: " + name + " " +
                              ("PASS" if passed else "FAIL"), flush=True)

                    build = telegram_formatter.build_signal_message_record
                    good = build(formatter_sample())
                    message = good.get("message") or ""
                    formatter_check("approved 75 ready", good.get("ready") is True)
                    formatter_check("basic message fields", all(part in message for part in (
                        "TRADE SIGNAL", "LONG", "BTCUSDT", "Confidence:", "Time:", "Entry:")))
                    formatter_check("no TP or SL", all(part not in message for part in (
                        "TP1", "TP2", "TP3", "Stop Loss", "Stop-loss", "SL:")))
                    formatter_check("below 75 rejected", build(formatter_sample(score=74.99)).get("ready") is False)
                    formatter_check("unselected rejected", build(formatter_sample(selected=False)).get("ready") is False)
                    formatter_check("engine ineligible rejected", build(formatter_sample(eligible=False)).get("ready") is False)
                    formatter_check("rejected decision rejected", build(formatter_sample(decision="REJECTED")).get("ready") is False)
                    formatter_check("failed evidence gate rejected", build(formatter_sample(gate_passed=False)).get("ready") is False)
                    no_gates = formatter_sample()
                    no_gates["confidence_result"].pop("evidence_gates")
                    formatter_check("missing evidence gates rejected", build(no_gates).get("ready") is False)
                    no_time = formatter_sample()
                    no_time.pop("observed_at")
                    formatter_check("missing timestamp rejected", build(no_time).get("ready") is False)
                    no_price = formatter_sample()
                    no_price["entry_price"] = 0
                    formatter_check("invalid price rejected", build(no_price).get("ready") is False)
                    formatter_check("unselected direct format blocked",
                                    telegram_formatter.format_trade_signal(formatter_sample(selected=False)) is None)
                    formatter_check("no sending enabled", TELEGRAM_SENDING_ENABLED is False)
                    count = sum(checks)
                    print("FORMATTER DIAGNOSTIC: " + ("PASS" if count == len(checks) else "FAIL") +
                          " (" + str(count) + "/" + str(len(checks)) +
                          "; synthetic only; no signal sent)", flush=True)
                except Exception as exc:
                    print("FORMATTER DIAGNOSTIC: FAIL (" + type(exc).__name__ + ": " + str(exc) + ")", flush=True)

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
