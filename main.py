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

except Exception as exc:

    ai_analyst = None
    print(
        "AI ANALYST IMPORT ERROR: " + type(exc).__name__ + ": " + str(exc),
        flush=True,
    )


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
        technical_features = {}
        market_features = {}

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
                technical_features=technical_features if isinstance(technical_features, dict) else {},
                market_features=market_features if isinstance(market_features, dict) else {},
                opportunity_time=opportunity[
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

        "opportunities":
        opportunities,

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
    """Store all considered opportunities, including selector rejections.

    Does not connect automatically, send messages, or execute trades.
    The caller supplies an explicit database connection. Fail closed on
    malformed records and propagate database errors to the caller.
    """
    if database_connection is None:
        return {"stored": False, "count": 0,
                "reason": "Explicit database connection required."}
    if memory_engine is None or technical_analysis is None or market_context is None:
        raise RuntimeError("Required memory/feature module unavailable")
    if not isinstance(batch_result, dict):
        raise ValueError("Invalid analysis batch")
    opportunities = batch_result.get("opportunities")
    if not isinstance(opportunities, list):
        raise ValueError("Batch must contain the complete opportunities list")
    selection = batch_result.get("selection") or {}
    if not isinstance(selection, dict):
        raise ValueError("Invalid selection result")
    selected = selection.get("selected") or []
    if not isinstance(selected, list):
        raise ValueError("Invalid selected list")
    selected_ids = {id(item) for item in selected}
    if len(selected_ids) != len(selected) or any(
            not any(item is candidate for candidate in opportunities)
            for item in selected):
        raise ValueError("Selected items must belong to the original batch")
    if batch_result.get("opportunity_count") != len(opportunities):
        raise ValueError("Opportunity count mismatch")
    stored_ids = []
    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            raise ValueError("Malformed opportunity")
        confidence = opportunity.get("confidence_result") or {}
        if not isinstance(confidence, dict):
            raise ValueError("Malformed confidence result")
        score = float(confidence.get("final_confidence"))
        if not __import__("math").isfinite(score) or not 0 <= score <= 100:
            raise ValueError("Invalid confidence score")
        technical = opportunity.get("technical_analysis") or {}
        market = opportunity.get("market_context") or {}
        if not isinstance(technical, dict) or not isinstance(market, dict):
            raise ValueError("Malformed analysis features")
        tech_features = technical_analysis.build_feature_vector(technical)
        market_features = market_context.build_context_features(market)
        if not isinstance(tech_features, dict) or not isinstance(market_features, dict):
            raise ValueError("Feature extraction failed")
        components = confidence.get("component_scores") or {}
        if not isinstance(components, dict):
            raise ValueError("Malformed confidence components")
        is_selected = id(opportunity) in selected_ids
        # Selection is not proof of Telegram delivery. Never mark as sent here.
        decision = "SELECTED_NOT_SENT" if is_selected else "REJECTED"
        reason = None if is_selected else (
            opportunity.get("selector_rejection_reason")
            or confidence.get("rejection_reason")
            or "Not selected by batch selector"
        )
        record_id = memory_engine.store_opportunity(
            conn=database_connection,
            symbol=opportunity["symbol"],
            direction=opportunity["direction"],
            entry_price=opportunity["entry_price"],
            decision=decision,
            technical_features=tech_features,
            market_features=market_features,
            raw_analysis=technical,
            raw_market_context=market,
            final_confidence=score,
            technical_confidence=components.get("technical"),
            memory_confidence=components.get("memory"),
            ai_confidence=components.get("ai"),
            market_confidence=components.get("market"),
            rejection_reason=reason,
            signal_sent=False,
            ai_analysis=opportunity.get("ai_result") or {},
            model_version="STEP4.12_NO_AI",
            strategy_version="STEP4.12_BATCH_MEMORY",
            created_at=opportunity["observed_at"],
        )
        stored_ids.append(record_id)
    if len(set(stored_ids)) != len(stored_ids):
        raise ValueError("Duplicate opportunity IDs in batch")
    return {"stored": True, "count": len(stored_ids),
            "opportunity_ids": stored_ids, "signals_sent": 0}


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


# ============================================================
# STEP 4.7: OPT-IN SYNTHETIC MEMORY WRITE / READ DIAGNOSTIC
# Writes one clearly labelled test record; never sends or trades.
# ============================================================
def run_memory_storage_diagnostic():
    prefix = "MEMORY STORAGE DIAGNOSTIC: "
    print(prefix + "START (one synthetic record; no sends or trades)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or memory_engine is None):
        print(prefix + "FAIL (safety flag or memory module unavailable)", flush=True)
        return False
    connection = None
    try:
        # Stable timestamp makes a restart idempotent: ON CONFLICT DO NOTHING.
        from datetime import datetime as _datetime, timezone as _timezone
        test_time = _datetime(2026, 9, 22, 0, 0, tzinfo=_timezone.utc)
        test_symbol = "SIGNALS2TESTUSDT"
        test_direction = "LONG"
        test_id = memory_engine.build_opportunity_id(
            test_symbol, test_direction, test_time.isoformat())
        connection = memory_engine.connect()
        # Schema must already exist from Step 4.6. Do not initialize here.
        record_id = memory_engine.store_opportunity(
            conn=connection, symbol=test_symbol, direction=test_direction,
            entry_price=100.0, decision="SYNTHETIC_TEST_REJECTED",
            technical_features={"test_only": True},
            market_features={"test_only": True},
            raw_analysis={"test_only": True},
            raw_market_context={"test_only": True},
            final_confidence=0.0, rejection_reason="Step 4.7 synthetic test only",
            signal_sent=False, model_version="STEP4.7_TEST",
            strategy_version="STEP4.7_TEST", created_at=test_time)
        if record_id != test_id:
            raise RuntimeError("Synthetic ID mismatch")
        record = memory_engine.get_opportunity(connection, test_id)
        if (not record or record.get("symbol") != test_symbol
                or record.get("direction") != test_direction
                or record.get("decision") != "SYNTHETIC_TEST_REJECTED"
                or record.get("signal_sent") is not False
                or float(record.get("entry_price") or 0) != 100.0):
            raise RuntimeError("Synthetic opportunity readback mismatch")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT symbol, direction, entry_price, outcome_complete
                FROM signals2_outcomes WHERE opportunity_id = %s
            """, (test_id,))
            outcome = cursor.fetchone()
            cursor.execute("""
                SELECT COUNT(*) FROM signals2_opportunities
                WHERE opportunity_id = %s
            """, (test_id,))
            count = cursor.fetchone()[0]
        if (not outcome or outcome[0] != test_symbol
                or outcome[1] != test_direction or float(outcome[2]) != 100.0
                or outcome[3] is not False or count != 1):
            raise RuntimeError("Synthetic outcome or duplicate check failed")
        print(prefix + "PASS (1 synthetic opportunity and matching pending outcome verified; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        # Do not log exception text; it could contain database credentials.
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ============================================================
# STEP 4.8: OPT-IN ONE-SHOT MARKET ANALYSIS -> MEMORY TEST
# Real public candles; saves four LONG/SHORT observations, including
# rejected candidates. No Telegram delivery or trade execution.
# ============================================================

# ============================================================
# ONE-OFF OBSERVATION COLLECTION (OPT-IN; NO SENDS OR TRADES)
# ============================================================

def run_one_off_observation_collection():
    """Collect BTC/ETH LONG/SHORT once, with completed-candle validation.

    The five-minute candle timestamp is the observation identity. A database
    advisory lock prevents concurrent copies of this diagnostic from racing.
    This is not a continuous scanner or a Telegram delivery test.
    """
    prefix = "OBSERVATION COLLECTION DIAGNOSTIC: "
    print(prefix + "START (one batch; no Telegram sends or trades)", flush=True)
    required = (bitget_market, technical_analysis, market_context,
                memory_engine, pattern_memory, confidence_engine,
                signal_selector, telegram_formatter)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or any(module is None for module in required)):
        print(prefix + "FAIL (safety flags or module unavailable)", flush=True)
        return False
    # Avoid surprise paid AI requests in this initial memory-connection test.
    if os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() == "true":
        print(prefix + "SKIPPED (set SIGNALS2_AI_ENABLED=false for this test)", flush=True)
        return False
    conn = None
    lock_acquired = False
    try:
        from datetime import timedelta
        import math
        frames = ("5m", "15m", "30m", "1H", "4H", "1D")
        analyses, candles_by_symbol, prices, candle_times = {}, {}, {}, {}
        # Fetch and validate *all* input data before any database write.
        for symbol in ("BTCUSDT", "ETHUSDT"):
            candles = bitget_market.get_multi_timeframe_candles(
                symbol=symbol, timeframes=frames, limit=200)
            if any(len(candles.get(frame, [])) < 55 for frame in frames):
                raise ValueError("Insufficient closed candle history: " + symbol)
            analysis = technical_analysis.analyze_symbol(
                symbol=symbol, multi_timeframe_candles=candles)
            if not all(analysis.get("timeframes", {}).get(frame, {}).get("valid")
                       for frame in frames):
                raise ValueError("Invalid timeframe analysis: " + symbol)
            price = float(candles["5m"][-1]["close"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("Invalid price: " + symbol)
            stamp = int(candles["5m"][-1]["timestamp"])
            if stamp <= 0 or stamp % 300000:
                raise ValueError("Invalid five-minute candle timestamp")
            analyses[symbol], candles_by_symbol[symbol] = analysis, candles
            prices[symbol], candle_times[symbol] = price, stamp
        if len(set(candle_times.values())) != 1:
            raise ValueError("BTC and ETH snapshots refer to different five-minute candles")
        # Observed time is the close of the common last fully closed 5m candle.
        observed_at = datetime.fromtimestamp(
            (next(iter(candle_times.values())) + 300000) / 1000, tz=timezone.utc)
        context = market_context.build_market_context(
            btc_analysis=analyses["BTCUSDT"], eth_analysis=analyses["ETHUSDT"],
            all_symbol_analyses=list(analyses.values()))
        conn = memory_engine.connect()
        # PostgreSQL session-level advisory lock, released in finally.
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (220250925,))
            lock_acquired = bool(cur.fetchone()[0])
        if not lock_acquired:
            print(prefix + "SKIPPED (another collection is running)", flush=True)
            return False
        with conn.cursor() as cur:
            cur.execute("""SELECT symbol, direction FROM signals2_opportunities
                           WHERE symbol IN ('BTCUSDT', 'ETHUSDT')
                             AND created_at >= %s AND created_at < %s""",
                        (observed_at, observed_at + timedelta(minutes=5)))
            existing = {(str(row[0]), str(row[1])) for row in cur.fetchall()}
        expected = {(symbol, direction) for symbol in ("BTCUSDT", "ETHUSDT")
                    for direction in ("LONG", "SHORT")}
        if existing & expected:
            print(prefix + "SKIPPED (this five-minute candle already has observations)", flush=True)
            return False
        opportunities = []
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for direction in ("LONG", "SHORT"):
                coin_context = market_context.build_coin_market_context(
                    coin_analysis=analyses[symbol], btc_analysis=analyses["BTCUSDT"],
                    market_context=context, direction=direction)
                opportunity = analyse_opportunity(
                    symbol=symbol, direction=direction, current_price=prices[symbol],
                    multi_timeframe_candles=candles_by_symbol[symbol],
                    full_market_context=coin_context, database_connection=conn,
                    observed_at=observed_at)
                confidence = opportunity.get("confidence_result") or {}
                score = float(confidence.get("final_confidence"))
                if not math.isfinite(score) or not 0 <= score <= 100:
                    raise ValueError("Invalid confidence score")
                if (confidence.get("component_scores") or {}).get("technical") is None:
                    raise ValueError("Missing technical confidence")
                if confidence.get("eligible") and (
                        score < MINIMUM_SIGNAL_CONFIDENCE or
                        (confidence.get("evidence_gates") or {}).get("passed") is not True):
                    raise ValueError("Confidence eligibility gate violation")
                opportunities.append(opportunity)
        batch = process_analysis_batch(opportunities, recent_signal_times={})
        if batch.get("opportunity_count") != 4:
            raise ValueError("Expected exactly four observations")
        result = store_analysis_batch(batch, database_connection=conn)
        if not result.get("stored") or result.get("count") != 4:
            raise RuntimeError("Observation storage incomplete")
        for opportunity, record_id in zip(opportunities, result["opportunity_ids"]):
            record = memory_engine.get_opportunity(conn, record_id)
            if (not record or record.get("signal_sent") is not False
                    or record.get("symbol") != opportunity["symbol"]
                    or record.get("direction") != opportunity["direction"]):
                raise RuntimeError("Stored observation readback mismatch")
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM signals2_outcomes WHERE opportunity_id=%s",
                            (record_id,))
                if cur.fetchone()[0] != 1:
                    raise RuntimeError("Missing outcome record")
            print(prefix + opportunity["symbol"] + " " + opportunity["direction"] +
                  "; confidence=" + str(opportunity["confidence_result"]["final_confidence"]) +
                  "; memory_usable=" + str(bool((opportunity.get("memory_analysis") or {}).get("memory_usable"))) +
                  "; sent=False", flush=True)
        print(prefix + "PASS (4 observations and outcome rows verified; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if conn is not None:
            if lock_acquired:
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_advisory_unlock(%s)", (220250925,))
                except Exception:
                    pass
            try:
                conn.close()
            except Exception:
                pass


# ============================================================
# CONTROLLED AUTOMATIC OBSERVATION COLLECTOR (OPT-IN)
# Default: ONE cycle only. Continuous mode requires explicit opt-in.
# Uses the already verified one-off collector, including its DB lock,
# five-minute candle identity, six-timeframe checks and readback.
# ============================================================
def run_automatic_observation_collector():
    import time
    prefix = "AUTO OBSERVATION: "
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() == "true"):
        print(prefix + "BLOCKED (safety settings; AI must be disabled)", flush=True)
        return False
    continuous = os.environ.get("SIGNALS2_AUTO_OBSERVATION_CONTINUOUS", "").strip().lower() == "true"
    # Never start an unbounded loop by simply enabling the test switch.
    max_cycles = 0 if continuous else 1
    print(prefix + ("START (continuous, five-minute boundaries)" if continuous else
                    "START (one scheduled cycle only)"), flush=True)
    cycles = 0
    while max_cycles == 0 or cycles < max_cycles:
        # Start 30 seconds after the next UTC five-minute boundary to allow
        # Bitget to publish the just-closed candle. No requests during sleep.
        now = time.time()
        next_boundary = (int(now) // 300 + 1) * 300
        wait = max(0.0, next_boundary + 30 - now)
        print(prefix + "WAIT (" + str(int(wait)) + " seconds until next closed candle)", flush=True)
        time.sleep(wait)
        # Recheck safety before every cycle, including after a long wait.
        if (LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED or
                os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() == "true"):
            print(prefix + "STOPPED (safety settings changed)", flush=True)
            return False
        cycles += 1
        print(prefix + "CYCLE " + str(cycles) + ": START", flush=True)
        try:
            passed = run_one_off_observation_collection()
        except Exception as exc:
            print(prefix + "CYCLE " + str(cycles) + ": FAIL (" + type(exc).__name__ + ")", flush=True)
            passed = False
        print(prefix + "CYCLE " + str(cycles) + ": " + ("PASS" if passed else "SKIPPED_OR_FAILED"), flush=True)
    print(prefix + "STOPPED (one scheduled cycle completed; no sends or trades)", flush=True)
    return True


# ============================================================
# HOURLY MEMORY LEARNING LOOP (OPT-IN)
# Collects one BTC/ETH LONG/SHORT observation batch per hour and then
# completes mature outcomes once they are at least 24h + 5m old.
# This avoids the old five-minute continuous collector (~1,152 rows/day).
# No Telegram sends, live scanning, AI calls or trade execution.
# ============================================================
def run_hourly_memory_learning_loop():
    import time
    prefix = "HOURLY MEMORY LOOP: "
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() == "true"):
        print(prefix + "BLOCKED (safety settings; AI must be disabled)", flush=True)
        return False
    if memory_engine is None or outcome_tracker is None:
        print(prefix + "BLOCKED (memory/outcome module unavailable)", flush=True)
        return False

    print(prefix + "START (hourly; 4 observations/cycle; mature outcomes only; no sends or trades)", flush=True)
    cycle = 0
    while True:
        # Run 30 seconds after the next UTC hour so the latest closed candles
        # are available from Bitget. Sleeping performs no API or DB activity.
        now = time.time()
        next_hour = (int(now) // 3600 + 1) * 3600
        wait = max(0.0, next_hour + 30 - now)
        print(prefix + "WAIT (" + str(int(wait)) + " seconds until next hourly cycle)", flush=True)
        time.sleep(wait)

        if (LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED or
                os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() == "true"):
            print(prefix + "STOPPED (safety settings changed)", flush=True)
            return False

        cycle += 1
        print(prefix + "CYCLE " + str(cycle) + ": START", flush=True)

        try:
            collected = run_one_off_observation_collection()
            print(prefix + "CYCLE " + str(cycle) + ": COLLECTION " +
                  ("PASS" if collected else "SKIPPED_OR_FAILED"), flush=True)
        except Exception as exc:
            print(prefix + "CYCLE " + str(cycle) + ": COLLECTION FAIL (" +
                  type(exc).__name__ + ")", flush=True)

        connection = None
        lock_acquired = False
        try:
            connection = memory_engine.connect()
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (220250926,))
                lock_acquired = bool(cursor.fetchone()[0])
            if not lock_acquired:
                print(prefix + "CYCLE " + str(cycle) + ": OUTCOMES SKIPPED (another updater is running)", flush=True)
                continue

            # Only touch observations old enough for the final 24h checkpoint.
            # A small 5m buffer avoids asking for a candle that may not yet be closed.
            with connection.cursor(cursor_factory=__import__(
                    "psycopg2.extras", fromlist=["RealDictCursor"]).RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT r.*
                    FROM signals2_outcomes r
                    WHERE r.outcome_complete = FALSE
                      AND r.opportunity_time <= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours 5 minutes'
                      -- Never feed synthetic diagnostics to Bitget. Step 4.7
                      -- deliberately stores SIGNALS2TESTUSDT, which is not a
                      -- real exchange symbol and must stay outside learning.
                      AND r.symbol NOT LIKE 'SIGNALS2%'
                    ORDER BY r.opportunity_time ASC
                    LIMIT 24
                """)
                records = [dict(row) for row in cursor.fetchall()]

            updated = completed = waiting = 0
            for record in records:
                result = outcome_tracker.update_one_outcome(connection, record)
                updated += int(bool(result.get("updated")))
                with connection.cursor() as cursor:
                    cursor.execute("SELECT outcome_complete FROM signals2_outcomes WHERE opportunity_id=%s",
                                   (record["opportunity_id"],))
                    row = cursor.fetchone()
                is_complete = bool(row and row[0])
                completed += int(is_complete)
                waiting += int(not is_complete)

            print(prefix + "CYCLE " + str(cycle) + ": OUTCOMES checked=" +
                  str(len(records)) + "; updated=" + str(updated) +
                  "; completed=" + str(completed) + "; waiting=" + str(waiting), flush=True)
            print(prefix + "CYCLE " + str(cycle) + ": PASS (no sends or trades)", flush=True)
        except Exception as exc:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            # Outcome failures must be diagnosable without exposing secrets.
            # Exception text from this path is generated by our DB/public-market
            # code; redact any configured secrets defensively before logging it.
            detail = str(exc).replace("\n", " ").replace("\r", " ")[:500]
            for secret_name in ("SIGNALS2_DATABASE_URL", "DATABASE_URL",
                                "BITGET_API_KEY", "BITGET_SECRET_KEY",
                                "BITGET_PASSPHRASE", "OPENAI_API_KEY"):
                secret_value = os.environ.get(secret_name)
                if secret_value:
                    detail = detail.replace(secret_value, "[REDACTED]")
            print(prefix + "CYCLE " + str(cycle) + ": OUTCOMES FAIL (" +
                  type(exc).__name__ + "): " + detail, flush=True)
        finally:
            if connection is not None:
                if lock_acquired:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT pg_advisory_unlock(%s)", (220250926,))
                    except Exception:
                        pass
                try:
                    connection.close()
                except Exception:
                    pass


def run_market_memory_diagnostic():
    prefix = "MARKET MEMORY DIAGNOSTIC: "
    print(prefix + "START (4 market observations; database writes; no sends or trades)", flush=True)
    required = (bitget_market, technical_analysis, market_context,
                confidence_engine, signal_selector, telegram_formatter, memory_engine)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or any(module is None for module in required)):
        print(prefix + "FAIL (safety flags or required module unavailable)", flush=True)
        return False
    connection = None
    try:
        frames = ("5m", "15m", "30m", "1H", "4H", "1D")
        analyses, candles_by_symbol, prices = {}, {}, {}
        for symbol in ("BTCUSDT", "ETHUSDT"):
            candles = bitget_market.get_multi_timeframe_candles(
                symbol=symbol, timeframes=frames, limit=200)
            if any(len(candles.get(frame, [])) < 55 for frame in frames):
                raise ValueError("Insufficient candle history for " + symbol)
            analysis = technical_analysis.analyze_symbol(
                symbol=symbol, multi_timeframe_candles=candles)
            if not all(analysis.get("timeframes", {}).get(frame, {}).get("valid") for frame in frames):
                raise ValueError("Invalid technical timeframe for " + symbol)
            price = float(candles["5m"][-1]["close"])
            if not __import__("math").isfinite(price) or price <= 0:
                raise ValueError("Invalid price for " + symbol)
            analyses[symbol], candles_by_symbol[symbol], prices[symbol] = analysis, candles, price
        context = market_context.build_market_context(
            btc_analysis=analyses["BTCUSDT"], eth_analysis=analyses["ETHUSDT"],
            all_symbol_analyses=list(analyses.values()))
        observed_at = utc_now()
        opportunities = []
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for direction in ("LONG", "SHORT"):
                coin_context = market_context.build_coin_market_context(
                    coin_analysis=analyses[symbol], btc_analysis=analyses["BTCUSDT"],
                    market_context=context, direction=direction)
                opportunity = analyse_opportunity(
                    symbol=symbol, direction=direction, current_price=prices[symbol],
                    multi_timeframe_candles=candles_by_symbol[symbol],
                    full_market_context=coin_context, database_connection=None,
                    observed_at=observed_at)
                confidence = opportunity.get("confidence_result") or {}
                if confidence.get("component_scores", {}).get("technical") is None:
                    raise ValueError("Confidence analysis missing for " + symbol + " " + direction)
                score = float(confidence.get("final_confidence", 0))
                if not __import__("math").isfinite(score) or score < 0 or score > 100:
                    raise ValueError("Invalid confidence score")
                if confidence.get("eligible") and (score < MINIMUM_SIGNAL_CONFIDENCE or
                        confidence.get("evidence_gates", {}).get("passed") is not True):
                    raise ValueError("Confidence safety gate violation")
                opportunities.append(opportunity)
        batch = process_analysis_batch(opportunities, recent_signal_times={})
        selected = batch.get("selection", {}).get("selected", [])
        if batch.get("opportunity_count") != 4 or len(selected) != batch.get("selected_count"):
            raise ValueError("Selector count mismatch")
        # A selected candidate is NOT a sent signal. Preserve that distinction.
        connection = memory_engine.connect()
        stored_ids = []
        for opportunity in opportunities:
            confidence = opportunity["confidence_result"]
            components = confidence.get("component_scores") or {}
            technical = opportunity.get("technical_analysis") or {}
            market = opportunity.get("market_context") or {}
            try:
                tech_features = technical_analysis.build_feature_vector(technical) or {}
            except Exception:
                tech_features = {}
            try:
                market_features = market_context.build_context_features(market) or {}
            except Exception:
                market_features = {}
            if not isinstance(tech_features, dict) or not isinstance(market_features, dict):
                raise ValueError("Feature extraction returned invalid type")
            record_id = memory_engine.store_opportunity(
                conn=connection, symbol=opportunity["symbol"],
                direction=opportunity["direction"],
                entry_price=opportunity["entry_price"],
                decision=str(confidence.get("decision") or "REJECTED"),
                technical_features=tech_features, market_features=market_features,
                raw_analysis=technical, raw_market_context=market,
                final_confidence=float(confidence["final_confidence"]),
                technical_confidence=components.get("technical"),
                memory_confidence=components.get("memory"),
                ai_confidence=components.get("ai"),
                market_confidence=components.get("market"),
                rejection_reason=confidence.get("rejection_reason"),
                signal_sent=False, ai_analysis=opportunity.get("ai_result") or {},
                model_version="STEP4.8_NO_AI", strategy_version="STEP4.8_MARKET_MEMORY_TEST",
                created_at=opportunity["observed_at"])
            record = memory_engine.get_opportunity(connection, record_id)
            if (not record or record.get("symbol") != opportunity["symbol"]
                    or record.get("direction") != opportunity["direction"]
                    or record.get("signal_sent") is not False):
                raise RuntimeError("Opportunity readback mismatch")
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM signals2_outcomes WHERE opportunity_id = %s", (record_id,))
                if cursor.fetchone()[0] != 1:
                    raise RuntimeError("Missing matching outcome")
            stored_ids.append(record_id)
            print(prefix + opportunity["symbol"] + " " + opportunity["direction"] +
                  " stored; confidence=" + str(confidence["final_confidence"]) +
                  "; decision=" + str(confidence.get("decision")), flush=True)
        if len(set(stored_ids)) != 4:
            raise RuntimeError("Duplicate opportunity IDs")
        print(prefix + "PASS (4 market observations and matching outcomes verified; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        # Do not print exception content; it could contain database credentials.
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def run_outcome_tracking_diagnostic():
    """One-shot follow-up for only Step 4.8 records; never scans or sends."""
    prefix = "OUTCOME TRACKING DIAGNOSTIC: "
    print(prefix + "START (Step 4.8 observations only; no sends or trades)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or memory_engine is None or outcome_tracker is None or bitget_market is None):
        print(prefix + "FAIL (safety flags or required module unavailable)", flush=True)
        return False
    connection = None
    try:
        connection = memory_engine.connect()
        with connection.cursor(cursor_factory=__import__("psycopg2.extras", fromlist=["RealDictCursor"]).RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM signals2_outcomes
                WHERE opportunity_id IN (
                    SELECT opportunity_id FROM signals2_opportunities
                    WHERE strategy_version = %s AND symbol IN ('BTCUSDT', 'ETHUSDT')
                ) ORDER BY opportunity_time ASC
            """, ("STEP4.8_MARKET_MEMORY_TEST",))
            records = [dict(row) for row in cursor.fetchall()]
        if len(records) != 4 or {(r["symbol"], r["direction"]) for r in records} != {
                ("BTCUSDT", "LONG"), ("BTCUSDT", "SHORT"),
                ("ETHUSDT", "LONG"), ("ETHUSDT", "SHORT")}:
            raise ValueError("Expected exactly four distinct Step 4.8 records")
        checked = updated = waiting = completed = 0
        for record in records:
            # update_one_outcome fetches public closed candles and updates this record only.
            result = outcome_tracker.update_one_outcome(connection, record)
            checked += 1
            updated += int(bool(result.get("updated")))
            waiting += int(not result.get("updated"))
            completed += int(bool(result.get("complete")))
            with connection.cursor() as cursor:
                cursor.execute("SELECT price_1m, price_5m, price_10m, price_30m, price_1h, price_4h, price_12h, price_24h, outcome_complete FROM signals2_outcomes WHERE opportunity_id = %s", (record["opportunity_id"],))
                row = cursor.fetchone()
            if row is None or (row[-1] and any(value is None for value in row[:-1])):
                raise RuntimeError("Outcome readback invalid")
            checkpoints = sum(value is not None for value in row[:-1])
            print(prefix + str(record["symbol"]) + " " + str(record["direction"]) +
                  "; checkpoints=" + str(checkpoints) + "; updated=" +
                  str(bool(result.get("updated"))) + "; complete=" + str(bool(row[-1])), flush=True)
        print(prefix + "PASS (checked=" + str(checked) + "; updated=" + str(updated) +
              "; waiting=" + str(waiting) + "; completed=" + str(completed) +
              "; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass



# ============================================================
# STEP 4.10: OPT-IN, ONE-SHOT PATTERN MEMORY DIAGNOSTIC
# Read-only database check + in-memory synthetic calculation.
# No synthetic database writes, Telegram, scanning or trades.
# ============================================================
def run_pattern_memory_diagnostic():
    prefix = "PATTERN MEMORY DIAGNOSTIC: "
    print(prefix + "START (read-only history; synthetic calculations only)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or memory_engine is None or pattern_memory is None):
        print(prefix + "FAIL (safety flags or required module unavailable)", flush=True)
        return False
    connection = None
    try:
        from datetime import timedelta
        import psycopg2
        now = utc_now()
        connection = memory_engine.connect()
        connection.set_session(readonly=True, autocommit=False)
        # Real historical analysis: pending observations must not count as evidence.
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*), COUNT(*) FILTER (WHERE r.outcome_complete = TRUE)
                FROM signals2_opportunities o
                JOIN signals2_outcomes r ON r.opportunity_id = o.opportunity_id
                WHERE o.strategy_version = %s
                  AND o.symbol IN ('BTCUSDT', 'ETHUSDT')
            """, ("STEP4.8_MARKET_MEMORY_TEST",))
            real_count, completed_count = cursor.fetchone()
        if real_count != 4:
            raise ValueError("Expected exactly four Step 4.8 observations")
        print(prefix + "real observations=4; completed=" + str(completed_count), flush=True)
        if completed_count > 4:
            raise ValueError("Invalid completed outcome count")
        # Test the actual database-backed matcher. It must not use the pending records.
        real = pattern_memory.analyze_pattern_memory(
            conn=connection, symbol="BTCUSDT", direction="LONG",
            technical_features={}, market_features={}, opportunity_time=now)
        if real.get("memory_usable") is not False or real.get("memory_score") is not None:
            raise ValueError("Real memory should remain unavailable with insufficient evidence")
        print(prefix + "real memory correctly unavailable (insufficient matches)", flush=True)
        # Pure in-memory examples: exercise actual similarity, sample and scoring functions.
        features = {name: 1.0 for name in list(pattern_memory.FEATURE_WEIGHTS)[:12]}
        historical = []
        for index in range(12):
            historical.append({
                "symbol": "BTCUSDT", "direction": "LONG",
                "created_at": now - timedelta(days=index + 1),
                "technical_features": features, "market_features": {},
                "return_1m_pct": 0.2 if index % 3 else -0.1,
                "direction_correct_1m": index % 3 != 0,
                "return_5m_pct": 0.3 if index % 3 else -0.2,
                "direction_correct_5m": index % 3 != 0,
            })
        matches = [pattern_memory.score_historical_match(
            "BTCUSDT", "LONG", features, now, row) for row in historical]
        if any(match is None for match in matches):
            raise ValueError("Identical synthetic patterns did not match")
        quality = pattern_memory.sample_quality(matches)
        horizons = {h: pattern_memory.analyze_horizon(matches, h)
                    for h in pattern_memory.OUTCOME_WEIGHTS}
        score = pattern_memory.calculate_memory_evidence_score(horizons, quality)
        if (not quality.get("memory_usable") or score is None or not (0 <= score <= 100)
                or horizons["1m"]["sample_size"] != 12
                or horizons["24h"]["sample_size"] != 0):
            raise ValueError("Synthetic memory scoring or missing-horizon handling failed")
        print(prefix + "synthetic 12 matches; effective_n=" +
              str(quality["effective_sample_size"]) + "; score=" + str(score), flush=True)
        # Opposite-direction records must not support a LONG prediction.
        opposite = pattern_memory.score_historical_match(
            "BTCUSDT", "LONG", features, now, dict(historical[0], direction="SHORT"))
        if opposite is not None:
            raise ValueError("Opposite direction incorrectly included")
        # A future record must never support a historical prediction.
        future = pattern_memory.score_historical_match(
            "BTCUSDT", "LONG", features, now,
            dict(historical[0], created_at=now + timedelta(days=1)))
        if future is not None:
            raise ValueError("Future record incorrectly included")
        print(prefix + "PASS (real DB read-only; synthetic score valid; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        # Never log exception text: database exceptions may contain credentials.
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
# STEP 4.11: OPT-IN HISTORICAL CANDLE AND OUTCOME DIAGNOSTIC
# Public GET data; only the four existing Step 4.8 outcomes may be updated.
# ============================================================
def run_step411_historical_diagnostic():
    prefix = "STEP 4.11 DIAGNOSTIC: "
    print(prefix + "START (public historical candles; four existing outcomes only)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or bitget_market is None or outcome_tracker is None or memory_engine is None):
        print(prefix + "FAIL (safety flags or missing module)", flush=True)
        return False
    connection = None
    try:
        minute = 60_000
        # Exercise actual paginated endpoint across a page boundary, on closed minutes.
        end_ms = (int(time.time() * 1000) // minute - 2) * minute
        start_ms = end_ms - 181 * minute
        candles = bitget_market.get_historical_1m_candles("BTCUSDT", start_ms, end_ms)
        if len(candles) != 181 or any(c["timestamp"] != start_ms + i * minute
                                       for i, c in enumerate(candles)):
            raise ValueError("Historical page continuity or count mismatch")
        print(prefix + "historical BTCUSDT 181 closed minutes: PASS (pagination)", flush=True)
        connection = memory_engine.connect()
        with connection.cursor(cursor_factory=__import__("psycopg2.extras", fromlist=["RealDictCursor"]).RealDictCursor) as cursor:
            cursor.execute("""
                SELECT r.* FROM signals2_outcomes r
                JOIN signals2_opportunities o ON o.opportunity_id = r.opportunity_id
                WHERE o.strategy_version = %s AND o.symbol IN ('BTCUSDT','ETHUSDT')
                ORDER BY r.opportunity_time ASC
            """, ("STEP4.8_MARKET_MEMORY_TEST",))
            records = [dict(row) for row in cursor.fetchall()]
        if len(records) != 4 or {(r["symbol"], r["direction"]) for r in records} != {
                ("BTCUSDT", "LONG"), ("BTCUSDT", "SHORT"),
                ("ETHUSDT", "LONG"), ("ETHUSDT", "SHORT")}:
            raise ValueError("Expected exactly four Step 4.8 outcomes")
        completed = updated = waiting = 0
        for record in records:
            result = outcome_tracker.update_one_outcome(connection, record)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT price_1m, price_5m, price_10m, price_30m, price_1h,
                           price_4h, price_12h, price_24h, outcome_complete
                    FROM signals2_outcomes WHERE opportunity_id = %s
                """, (record["opportunity_id"],))
                row = cursor.fetchone()
            if row is None or (row[-1] and any(v is None for v in row[:-1])):
                raise ValueError("Incomplete outcome incorrectly marked complete")
            updated += int(bool(result.get("updated")))
            waiting += int(not result.get("updated"))
            completed += int(bool(row[-1]))
            print(prefix + str(record["symbol"]) + " " + str(record["direction"]) +
                  "; checkpoints=" + str(sum(v is not None for v in row[:-1])) +
                  "; complete=" + str(bool(row[-1])), flush=True)
        print(prefix + "PASS (historical pagination verified; outcomes checked=4; updated=" +
              str(updated) + "; waiting=" + str(waiting) + "; completed=" +
              str(completed) + "; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        # Give enough sanitized detail to diagnose public historical-data
        # failures without exposing credentials or database connection strings.
        detail = str(exc).replace("\n", " ").replace("\r", " ")[:500]
        for secret_name in ("SIGNALS2_DATABASE_URL", "DATABASE_URL",
                            "BITGET_API_KEY", "BITGET_SECRET_KEY",
                            "BITGET_PASSPHRASE", "OPENAI_API_KEY"):
            secret_value = os.environ.get(secret_name)
            if secret_value:
                detail = detail.replace(secret_value, "[REDACTED]")
        print(prefix + "FAIL (" + type(exc).__name__ + "): " + detail, flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ============================================================
# STEP 4.12: OPT-IN DATABASE BATCH STORAGE DIAGNOSTIC
# Synthetic BTC/ETH observations, no market scanning or sending.
# ============================================================
def run_step412_batch_memory_diagnostic():
    prefix = "STEP 4.12 DIAGNOSTIC: "
    print(prefix + "START (synthetic batch; no sends or trades)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or any(module is None for module in
                   (memory_engine, technical_analysis, market_context))):
        print(prefix + "FAIL (safety flags or missing module)", flush=True)
        return False
    connection = None
    try:
        # Fixed timestamp means redeploying this diagnostic cannot duplicate rows.
        test_time = datetime(2026, 9, 23, 0, 0, tzinfo=timezone.utc)
        examples = []
        for symbol in ("SIGNALS2STEP412BTC", "SIGNALS2STEP412ETH"):
            for direction in ("LONG", "SHORT"):
                examples.append({
                    "symbol": symbol, "direction": direction,
                    "entry_price": 100.0, "observed_at": test_time,
                    "technical_analysis": {}, "market_context": {},
                    "ai_result": {"available": False},
                    "confidence_result": {
                        "final_confidence": 50.0,
                        "component_scores": {},
                        "rejection_reason": "Step 4.12 synthetic test only",
                    },
                })
        batch = {"opportunity_count": 4,
                 "opportunities": examples,
                 "selection": {"selected": [], "rejected": examples},
                 "formatted_signals": []}
        connection = memory_engine.connect()
        result = store_analysis_batch(batch, database_connection=connection)
        if not result.get("stored") or result.get("count") != 4:
            raise ValueError("Batch storage count mismatch")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*), COUNT(r.opportunity_id),
                       COUNT(*) FILTER (WHERE o.signal_sent = FALSE),
                       COUNT(*) FILTER (WHERE o.decision = 'REJECTED')
                FROM signals2_opportunities o
                LEFT JOIN signals2_outcomes r ON r.opportunity_id = o.opportunity_id
                WHERE o.opportunity_id = ANY(%s)
            """, (result["opportunity_ids"],))
            counts = cursor.fetchone()
        if counts != (4, 4, 4, 4):
            raise ValueError("Database readback mismatch")
        print(prefix + "PASS (4 synthetic opportunities + outcomes; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ============================================================
# STEP 5.1: OPT-IN, SYNTHETIC, ONE-SHOT OPENAI DIAGNOSTIC
# Never fetches prices, writes to the database, sends or trades.
# ============================================================
def run_ai_one_shot_diagnostic():
    prefix = "AI ONE-SHOT DIAGNOSTIC: "
    print(prefix + "START (synthetic evidence; at most one API call)", flush=True)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or ai_analyst is None):
        print(prefix + "FAIL (safety flags or analyst unavailable)", flush=True)
        return False
    if os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() != "true":
        print(prefix + "UNAVAILABLE (SIGNALS2_AI_ENABLED is not true)", flush=True)
        return False
    try:
        result = ai_analyst.analyze_with_ai(
            symbol="BTCUSDT", direction="LONG", current_price=100.0,
            technical_analysis={"timeframes": {"1h": "synthetic mixed"}},
            market_context={"regime": "synthetic uncertain"},
            memory_analysis={"memory_usable": False},
        )
        if not isinstance(result, dict) or not result.get("available"):
            reason = result.get("reasoning_summary", "unknown") if isinstance(result, dict) else "invalid result"
            # Do not print request details, API keys or full response.
            print(prefix + "UNAVAILABLE (" + str(reason)[:200] + ")", flush=True)
            return False
        score = result.get("ai_score")
        if score is None or not 0 <= float(score) <= 100:
            print(prefix + "FAIL (invalid evidence score)", flush=True)
            return False
        print(prefix + "PASS (structured response validated; no sends or trades)", flush=True)
        return True
    except Exception as exc:
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False


# ============================================================
# STEP 5.5: OPT-IN REAL-MARKET AI DIAGNOSTIC
# Exactly one BTCUSDT LONG analysis; no database, sends or trades.
# WARNING: Startup opt-in can repeat on container restarts. Reset
# BOTH flags immediately after the test.
# ============================================================
def run_real_market_ai_diagnostic():
    prefix = "REAL MARKET AI DIAGNOSTIC: "
    print(prefix + "START (BTCUSDT LONG; one AI request maximum)", flush=True)
    required = (bitget_market, technical_analysis, market_context, ai_analyst,
                confidence_engine)
    if (not DEVELOPMENT_MODE or LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED
            or any(module is None for module in required)):
        print(prefix + "FAIL (safety flags or missing module)", flush=True)
        return False
    if os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() != "true":
        print(prefix + "UNAVAILABLE (AI connection disabled)", flush=True)
        return False
    try:
        frames = ("5m", "15m", "30m", "1H", "4H", "1D")
        analyses, prices = {}, {}
        for symbol in ("BTCUSDT", "ETHUSDT"):
            candles = bitget_market.get_multi_timeframe_candles(
                symbol=symbol, timeframes=frames, limit=200)
            if any(len(candles.get(frame, [])) < 55 for frame in frames):
                raise ValueError("Insufficient closed candles for " + symbol)
            analysis = technical_analysis.analyze_symbol(
                symbol=symbol, multi_timeframe_candles=candles)
            if not all(analysis.get("timeframes", {}).get(frame, {}).get("valid") for frame in frames):
                raise ValueError("Invalid timeframe for " + symbol)
            price = float(candles["5m"][-1]["close"])
            if not __import__("math").isfinite(price) or price <= 0:
                raise ValueError("Invalid closed price")
            analyses[symbol], prices[symbol] = analysis, price
        full_context = market_context.build_market_context(
            btc_analysis=analyses["BTCUSDT"], eth_analysis=analyses["ETHUSDT"],
            all_symbol_analyses=list(analyses.values()))
        coin_context = market_context.build_coin_market_context(
            coin_analysis=analyses["BTCUSDT"], btc_analysis=analyses["BTCUSDT"],
            market_context=full_context, direction="LONG")
        # Call the AI once directly, with real evidence and unavailable memory.
        # Do not invoke the normal multi-opportunity controller or any storage.
        result = ai_analyst.analyze_with_ai(
            symbol="BTCUSDT", direction="LONG", current_price=prices["BTCUSDT"],
            technical_analysis=analyses["BTCUSDT"], market_context=coin_context,
            memory_analysis={"memory_usable": False, "memory_score": None})
        if not isinstance(result, dict) or result.get("available") is not True:
            print(prefix + "UNAVAILABLE (" + str(
                result.get("reasoning_summary", "unknown") if isinstance(result, dict)
                else "invalid result")[:180] + ")", flush=True)
            return False
        score = float(result.get("ai_score"))
        if not __import__("math").isfinite(score) or not 0 <= score <= 100:
            raise ValueError("Invalid AI evidence score")
        confidence = confidence_engine.calculate_final_confidence(
            symbol="BTCUSDT", direction="LONG",
            technical_analysis=analyses["BTCUSDT"], market_context=coin_context,
            memory_analysis={"memory_usable": False, "memory_score": None},
            ai_result=result)
        final_score = float(confidence.get("final_confidence", -1))
        if not __import__("math").isfinite(final_score) or not 0 <= final_score <= 100:
            raise ValueError("Invalid final confidence")
        if confidence.get("eligible") and (final_score < MINIMUM_SIGNAL_CONFIDENCE
                or confidence.get("evidence_gates", {}).get("passed") is not True):
            raise ValueError("Confidence safety gate violation")
        print(prefix + "AI available; evidence_score=" + str(round(score, 2)) +
              "; final_confidence=" + str(round(final_score, 2)) +
              "; eligible=" + str(bool(confidence.get("eligible"))) +
              "; decision=" + str(confidence.get("decision")), flush=True)
        print(prefix + "PASS (one real-market analysis; no database writes, sends or trades)", flush=True)
        return True
    except Exception as exc:
        # No exception detail: request exceptions could contain credentials.
        print(prefix + "FAIL (" + type(exc).__name__ + ")", flush=True)
        return False


# ============================================================
# TASK 6: CONTROLLED AUTOMATIC MARKET SCANNER (OPT-IN)
#
# Development-only scanner:
# - Public Bitget market data
# - BTCUSDT / ETHUSDT only for the first controlled rollout
# - LONG + SHORT analysis
# - Uses technical, market context, memory, AI (only when explicitly enabled),
#   confidence, selector and formatter stages
# - Stores every considered opportunity for unbiased learning
# - DOES NOT send Telegram messages
# - DOES NOT execute trades
#
# Enable with:
# SIGNALS2_CONTROLLED_SCANNER_ON_START=true
#
# Optional:
# SIGNALS2_CONTROLLED_SCANNER_CONTINUOUS=true
# SIGNALS2_CONTROLLED_SCANNER_INTERVAL_SECONDS=600
# ============================================================

def run_controlled_market_scanner():
    prefix = "CONTROLLED SCANNER: "
    required = (
        bitget_market, technical_analysis, market_context, memory_engine,
        pattern_memory, confidence_engine, signal_selector, telegram_formatter,
    )

    if not DEVELOPMENT_MODE:
        print(prefix + "BLOCKED (development mode required)", flush=True)
        return False
    if LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED:
        print(prefix + "BLOCKED (live scanning/Telegram flags must remain disabled)", flush=True)
        return False
    if any(module is None for module in required):
        print(prefix + "BLOCKED (required module unavailable)", flush=True)
        return False

    continuous = (
        os.environ.get("SIGNALS2_CONTROLLED_SCANNER_CONTINUOUS", "")
        .strip().lower() == "true"
    )
    try:
        interval = int(
            os.environ.get(
                "SIGNALS2_CONTROLLED_SCANNER_INTERVAL_SECONDS",
                str(SCAN_INTERVAL_SECONDS),
            )
        )
    except Exception:
        interval = SCAN_INTERVAL_SECONDS
    interval = max(300, interval)

    ai_enabled = (
        os.environ.get("SIGNALS2_AI_ENABLED", "").strip().lower() == "true"
    )
    if ai_enabled and ai_analyst is None:
        print(prefix + "BLOCKED (AI enabled but analyst unavailable)", flush=True)
        return False

    print(
        prefix + "START (" +
        ("continuous; " + str(interval) + "s interval" if continuous else "one cycle") +
        "; dynamic Bitget USDT futures; Telegram OFF; no trades)",
        flush=True,
    )

    cycle = 0
    while True:
        cycle += 1
        print(prefix + "CYCLE " + str(cycle) + ": START", flush=True)
        connection = None
        try:
            import math
            from datetime import timedelta

            # Re-check safety every cycle.
            if LIVE_SCANNING_ENABLED or TELEGRAM_SENDING_ENABLED:
                raise RuntimeError("Safety flags changed")

            frames = ("5m", "15m", "30m", "1H", "4H", "1D")

            # Discover the current Bitget USDT perpetual universe dynamically.
            # Use the exchange ticker snapshot only as a cheap liquidity prefilter;
            # the full six-timeframe analysis is still the source of signal evidence.
            tradeable = set(bitget_market.get_tradeable_symbols() or [])
            tickers = bitget_market.get_all_futures_tickers() or []
            if not tradeable or not tickers:
                raise RuntimeError("Bitget market universe unavailable")

            ranked = []
            for ticker in tickers:
                if not isinstance(ticker, dict):
                    continue
                symbol = str(ticker.get("symbol") or "").upper().strip()
                if symbol not in tradeable or not symbol.endswith("USDT"):
                    continue
                try:
                    # Bitget futures ticker payloads expose USDT turnover as
                    # usdtVolume on current API versions. Fall back safely to
                    # quoteVolume/turnover if present; malformed values rank last.
                    liquidity = float(
                        ticker.get("usdtVolume")
                        or ticker.get("quoteVolume")
                        or ticker.get("turnover")
                        or 0.0
                    )
                except Exception:
                    liquidity = 0.0
                if not math.isfinite(liquidity) or liquidity < 0:
                    liquidity = 0.0
                ranked.append((liquidity, symbol))

            ranked.sort(key=lambda item: (-item[0], item[1]))
            try:
                max_candidates = int(os.environ.get(
                    "SIGNALS2_SCANNER_MAX_CANDIDATES", "10"
                ))
            except Exception:
                max_candidates = 10
            max_candidates = max(2, min(max_candidates, 25))

            candidate_symbols = []
            for _, symbol in ranked:
                if symbol not in candidate_symbols:
                    candidate_symbols.append(symbol)
                if len(candidate_symbols) >= max_candidates:
                    break

            # BTC and ETH are always analysed because market_context requires
            # them as reference markets, even if they fall outside the top-N.
            analysis_symbols = list(candidate_symbols)
            for reference_symbol in ("BTCUSDT", "ETHUSDT"):
                if reference_symbol not in tradeable:
                    raise RuntimeError(reference_symbol + " is not tradeable")
                if reference_symbol not in analysis_symbols:
                    analysis_symbols.append(reference_symbol)

            print(
                prefix + "DISCOVERY universe=" + str(len(tradeable)) +
                "; ticker_matches=" + str(len(ranked)) +
                "; candidates=" + str(len(candidate_symbols)) +
                "; top=" + ",".join(candidate_symbols),
                flush=True,
            )

            analyses = {}
            candles_by_symbol = {}
            prices = {}
            candle_times = {}

            # Fetch/validate all public market data before any DB write.
            for symbol in analysis_symbols:
                candles = bitget_market.get_multi_timeframe_candles(
                    symbol=symbol,
                    timeframes=frames,
                    limit=200,
                )
                counts = {frame: len(candles.get(frame, [])) for frame in frames}
                if any(count < 55 for count in counts.values()):
                    raise ValueError("Insufficient closed candle history: " + symbol)

                analysis = technical_analysis.analyze_symbol(
                    symbol=symbol,
                    multi_timeframe_candles=candles,
                )
                if not all(
                    analysis.get("timeframes", {}).get(frame, {}).get("valid")
                    for frame in frames
                ):
                    raise ValueError("Invalid timeframe analysis: " + symbol)

                last_5m = candles["5m"][-1]
                price = float(last_5m["close"])
                stamp = int(last_5m["timestamp"])
                if not math.isfinite(price) or price <= 0:
                    raise ValueError("Invalid price: " + symbol)
                if stamp <= 0 or stamp % 300000:
                    raise ValueError("Invalid five-minute candle timestamp: " + symbol)

                analyses[symbol] = analysis
                candles_by_symbol[symbol] = candles
                prices[symbol] = price
                candle_times[symbol] = stamp

            reference_times = {
                candle_times.get("BTCUSDT"), candle_times.get("ETHUSDT")
            }
            if None in reference_times or len(reference_times) != 1:
                raise ValueError("BTC and ETH snapshots use different five-minute candles")

            observed_at = datetime.fromtimestamp(
                (next(iter(candle_times.values())) + 300000) / 1000,
                tz=timezone.utc,
            )

            full_context = market_context.build_market_context(
                btc_analysis=analyses["BTCUSDT"],
                eth_analysis=analyses["ETHUSDT"],
                all_symbol_analyses=list(analyses.values()),
            )

            connection = memory_engine.connect()

            # Do not duplicate observations already collected by the hourly
            # memory loop for the same closed five-minute candle.
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT symbol, direction
                       FROM signals2_opportunities
                       WHERE symbol IN ('BTCUSDT', 'ETHUSDT')
                         AND created_at >= %s
                         AND created_at < %s""",
                    (observed_at, observed_at + timedelta(minutes=5)),
                )
                existing = {
                    (str(row[0]), str(row[1]))
                    for row in cursor.fetchall()
                }

            opportunities = []
            skipped_existing = 0

            for symbol in candidate_symbols:
                for direction in ("LONG", "SHORT"):
                    if (symbol, direction) in existing:
                        skipped_existing += 1
                        continue

                    coin_context = market_context.build_coin_market_context(
                        coin_analysis=analyses[symbol],
                        btc_analysis=analyses["BTCUSDT"],
                        market_context=full_context,
                        direction=direction,
                    )

                    opportunity = analyse_opportunity(
                        symbol=symbol,
                        direction=direction,
                        current_price=prices[symbol],
                        multi_timeframe_candles=candles_by_symbol[symbol],
                        full_market_context=coin_context,
                        database_connection=connection,
                        observed_at=observed_at,
                    )

                    confidence = opportunity.get("confidence_result") or {}
                    score = float(confidence.get("final_confidence"))
                    if not math.isfinite(score) or not 0 <= score <= 100:
                        raise ValueError("Invalid confidence score")
                    if confidence.get("eligible") and (
                        score < MINIMUM_SIGNAL_CONFIDENCE
                        or (confidence.get("evidence_gates") or {}).get("passed") is not True
                    ):
                        raise ValueError("Confidence eligibility gate violation")

                    opportunities.append(opportunity)
                    print(
                        prefix + symbol + " " + direction +
                        "; confidence=" + str(round(score, 2)) +
                        "; memory_usable=" +
                        str(bool((opportunity.get("memory_analysis") or {}).get("memory_usable"))) +
                        "; ai_available=" +
                        str(bool((opportunity.get("ai_result") or {}).get("available"))),
                        flush=True,
                    )

            if not opportunities:
                print(
                    prefix + "CYCLE " + str(cycle) +
                    ": SKIPPED (this closed candle already stored)",
                    flush=True,
                )
            else:
                batch = process_analysis_batch(
                    opportunities,
                    recent_signal_times={},
                )
                selection = batch.get("selection") or {}
                selected = selection.get("selected") or []
                formatted = batch.get("formatted_signals") or []

                # The controlled scanner may FORMAT an approved candidate,
                # but sending is forbidden in this stage.
                if TELEGRAM_SENDING_ENABLED:
                    raise RuntimeError("Telegram sending unexpectedly enabled")

                stored = store_analysis_batch(
                    batch,
                    database_connection=connection,
                )
                if not stored.get("stored") or stored.get("count") != len(opportunities):
                    raise RuntimeError("Scanner memory storage incomplete")

                for candidate in selected:
                    confidence = candidate.get("confidence_result") or {}
                    if (
                        float(confidence.get("final_confidence", 0)) < MINIMUM_SIGNAL_CONFIDENCE
                        or confidence.get("eligible") is not True
                        or (confidence.get("evidence_gates") or {}).get("passed") is not True
                    ):
                        raise RuntimeError("Selected candidate violated approval gates")

                print(
                    prefix + "CYCLE " + str(cycle) +
                    ": PASS (analysed=" + str(len(opportunities)) +
                    "; existing_skipped=" + str(skipped_existing) +
                    "; selected=" + str(len(selected)) +
                    "; formatted=" + str(len(formatted)) +
                    "; stored=" + str(stored.get("count")) +
                    "; sent=0; trades=0)",
                    flush=True,
                )

            if connection is not None:
                connection.close()
                connection = None

        except Exception as exc:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
                try:
                    connection.close()
                except Exception:
                    pass
                connection = None

            detail = str(exc).replace("\n", " ").replace("\r", " ")[:400]
            for secret_name in (
                "SIGNALS2_DATABASE_URL", "DATABASE_URL",
                "BITGET_API_KEY", "BITGET_SECRET_KEY",
                "BITGET_PASSPHRASE", "OPENAI_API_KEY",
                "SIGNALS2_TELEGRAM_BOT_TOKEN",
            ):
                secret_value = os.environ.get(secret_name)
                if secret_value:
                    detail = detail.replace(secret_value, "[REDACTED]")

            print(
                prefix + "CYCLE " + str(cycle) + ": FAIL (" +
                type(exc).__name__ + "): " + detail,
                flush=True,
            )

        if not continuous:
            print(
                prefix + "STOPPED (one controlled cycle completed; no sends or trades)",
                flush=True,
            )
            return True

        print(
            prefix + "WAIT (" + str(interval) + " seconds until next cycle)",
            flush=True,
        )
        time.sleep(interval)


if __name__ == "__main__":

    try:

        development_self_test()

        if os.environ.get("SIGNALS2_AI_TEST_ON_START", "").strip().lower() == "true":
            run_ai_one_shot_diagnostic()

        if os.environ.get("SIGNALS2_AI_REAL_MARKET_TEST_ON_START", "").strip().lower() == "true":
            run_real_market_ai_diagnostic()

        if os.environ.get("SIGNALS2_STEP412_TEST_ON_START", "").lower().strip() == "true":
            run_step412_batch_memory_diagnostic()

        if os.environ.get("SIGNALS2_STEP411_TEST_ON_START", "").lower().strip() == "true":
            run_step411_historical_diagnostic()

        if os.environ.get("SIGNALS2_PATTERN_MEMORY_TEST_ON_START", "").lower().strip() == "true":
            run_pattern_memory_diagnostic()

        if os.environ.get("SIGNALS2_OUTCOME_TEST_ON_START", "").lower().strip() == "true":
            run_outcome_tracking_diagnostic()

        if os.environ.get("SIGNALS2_OBSERVATION_COLLECTION_TEST_ON_START", "").lower().strip() == "true":
            run_one_off_observation_collection()

        if os.environ.get("SIGNALS2_AUTO_OBSERVATION_TEST_ON_START", "").lower().strip() == "true":
            run_automatic_observation_collector()

        if os.environ.get("SIGNALS2_CONTROLLED_SCANNER_ON_START", "").lower().strip() == "true":
            run_controlled_market_scanner()

        if os.environ.get("SIGNALS2_HOURLY_MEMORY_LOOP_ON_START", "").lower().strip() == "true":
            run_hourly_memory_learning_loop()

        if os.environ.get("SIGNALS2_MARKET_MEMORY_TEST_ON_START", "").lower().strip() == "true":
            run_market_memory_diagnostic()

        if os.environ.get("SIGNALS2_MEMORY_STORAGE_TEST_ON_START", "").lower().strip() == "true":
            run_memory_storage_diagnostic()

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
