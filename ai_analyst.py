import json
import math
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# AI MARKET ANALYST
#
# PURPOSE:
#
# Give the AI structured evidence about a potential setup:
#
# - Technical analysis
# - Multi-timeframe trend
# - Market regime
# - BTC / ETH context
# - Relative strength
# - Historical pattern memory
# - Historical outcomes
# - MFE / MAE
# - Early continuation / reversal behaviour
#
# The AI then evaluates:
#
# - Setup quality
# - Evidence agreement
# - Evidence conflicts
# - Market conditions
# - Historical support
# - Main risks
#
# IMPORTANT:
#
# AI DOES NOT:
#
# - Place trades
# - Control Bitget
# - Send Telegram
# - Decide the final confidence alone
# - Change strategy rules
# - Change its own weights
#
# OpenAI connection will be added later.
# ============================================================


AI_ANALYST_VERSION = "2.1.0"

# Explicit opt-in required for every API call. No automatic live use.
AI_ENABLED_FLAG = "SIGNALS2_AI_ENABLED"
AI_TEST_FLAG = "SIGNALS2_AI_TEST_ON_START"



# ============================================================
# AI SCORE RANGE
#
# AI produces an evidence score from 0-100.
#
# This is NOT the final signal confidence.
# ============================================================


MIN_AI_SCORE = 0.0
MAX_AI_SCORE = 100.0


# ============================================================
# VALID CLASSIFICATIONS
# ============================================================


VALID_SETUP_QUALITY = {
    "VERY_WEAK",
    "WEAK",
    "NEUTRAL",
    "GOOD",
    "VERY_GOOD",
    "EXCEPTIONAL",
}


VALID_MARKET_ALIGNMENT = {
    "STRONGLY_AGAINST",
    "AGAINST",
    "MIXED",
    "SUPPORTIVE",
    "STRONGLY_SUPPORTIVE",
}


VALID_HISTORICAL_SUPPORT = {
    "INSUFFICIENT_DATA",
    "NEGATIVE",
    "MIXED",
    "POSITIVE",
    "STRONGLY_POSITIVE",
}


VALID_RISK_LEVELS = {
    "LOW",
    "MODERATE",
    "HIGH",
    "VERY_HIGH",
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


def safe_bool(
    value,
    default=False,
):

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):

        value = (
            value
            .strip()
            .lower()
        )

        if value in {
            "true",
            "yes",
            "1",
        }:
            return True

        if value in {
            "false",
            "no",
            "0",
        }:
            return False

    return default


def clean_text(
    value,
    max_length=1000,
):

    if value is None:
        return ""

    text = str(
        value
    ).strip()

    return text[
        :max_length
    ]


def clean_list(
    value,
    max_items=10,
    max_length=300,
):

    if not isinstance(
        value,
        list,
    ):
        return []

    cleaned = []

    for item in value[
        :max_items
    ]:

        text = clean_text(
            item,
            max_length=max_length,
        )

        if text:
            cleaned.append(
                text
            )

    return cleaned


# ============================================================
# SAFE JSON SERIALIZATION
# ============================================================


def make_json_safe(
    value,
):

    if value is None:

        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):

        if isinstance(
            value,
            float,
        ):

            if not math.isfinite(
                value
            ):
                return None

        return value

    if isinstance(
        value,
        dict,
    ):

        return {

            str(key):
            make_json_safe(
                item
            )

            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        return [

            make_json_safe(
                item
            )

            for item in value
        ]

    return str(
        value
    )


# ============================================================
# COMPACT TECHNICAL DATA
#
# We do not need to send every raw candle to the AI.
#
# The technical analysis engine has already converted the
# candles into useful features.
# ============================================================


def build_technical_summary(
    technical_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        technical_analysis,
        dict,
    ):

        return {}

    summary = {}

    # Preserve the useful structured analysis.

    for key in [
        "symbol",
        "price",
        "multi_timeframe",
        "timeframes",
        "alignment",
        "overall_direction",
        "feature_vector",
    ]:

        if key in technical_analysis:

            summary[
                key
            ] = make_json_safe(
                technical_analysis[
                    key
                ]
            )

    # If the exact structure is different,
    # retain the full object as a fallback.

    if not summary:

        summary = make_json_safe(
            technical_analysis
        )

    return summary


# ============================================================
# COMPACT MARKET CONTEXT
# ============================================================


def build_market_summary(
    market_context: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        market_context,
        dict,
    ):

        return {}

    wanted = [

        "major_context",
        "breadth",
        "volatility",
        "stress",
        "regime",
        "direction_market_agreement",
        "relative_strength_vs_btc",
    ]

    summary = {}

    for key in wanted:

        if key in market_context:

            summary[
                key
            ] = make_json_safe(
                market_context[
                    key
                ]
            )

    if not summary:

        summary = make_json_safe(
            market_context
        )

    return summary


# ============================================================
# COMPACT MEMORY EVIDENCE
# ============================================================


def build_memory_summary(
    memory_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        memory_analysis,
        dict,
    ):

        return {
            "memory_available":
            False,
        }

    # An insufficient sample must never be presented as positive historical evidence.
    if memory_analysis.get("memory_usable") is not True:
        return {
            "memory_available": False,
            "memory_score": None,
            "sample_quality": make_json_safe(memory_analysis.get("sample_quality", {})),
            "same_symbol_matches": memory_analysis.get("same_symbol_matches"),
            "cross_symbol_matches": memory_analysis.get("cross_symbol_matches"),
            "horizons": {},
            "excursions": {},
            "early_behaviour": {},
            "top_historical_matches": [],
        }

    return {

        "memory_available":
        bool(
            memory_analysis.get(
                "memory_usable",
                False,
            )
        ),

        "memory_score":
        memory_analysis.get(
            "memory_score"
        ),

        "sample_quality":
        make_json_safe(
            memory_analysis.get(
                "sample_quality",
                {},
            )
        ),

        "same_symbol_matches":
        memory_analysis.get(
            "same_symbol_matches"
        ),

        "cross_symbol_matches":
        memory_analysis.get(
            "cross_symbol_matches"
        ),

        "horizons":
        make_json_safe(
            memory_analysis.get(
                "horizons",
                {},
            )
        ),

        "excursions":
        make_json_safe(
            memory_analysis.get(
                "excursions",
                {},
            )
        ),

        "early_behaviour":
        make_json_safe(
            memory_analysis.get(
                "early_behaviour",
                {},
            )
        ),

        "top_historical_matches":
        make_json_safe(
            memory_analysis.get(
                "top_historical_matches",
                [],
            )[:10]
        ),
    }


# ============================================================
# BUILD AI EVIDENCE PACKAGE
# ============================================================


def build_ai_evidence_package(
    symbol: str,
    direction: str,
    current_price: float,
    technical_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    memory_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    return {

        "system":
        "BRADS_SIGNALS_BOT_2",

        "ai_analyst_version":
        AI_ANALYST_VERSION,

        "symbol":
        str(
            symbol
        ).upper(),

        "proposed_direction":
        str(
            direction
        ).upper(),

        "current_price":
        safe_float(
            current_price
        ),

        "technical_evidence":
        build_technical_summary(
            technical_analysis
        ),

        "market_evidence":
        build_market_summary(
            market_context
        ),

        "historical_memory":
        build_memory_summary(
            memory_analysis
        ),
    }


# ============================================================
# AI SYSTEM INSTRUCTIONS
#
# This will later be sent as the system prompt.
# ============================================================


def build_system_prompt() -> str:

    return """
You are the market-analysis reasoning component inside
Brad's Crypto Signals Bot 2.0.

You are NOT a trade execution system.

Your job is to critically analyse a proposed LONG or SHORT
crypto market opportunity using ONLY the evidence supplied
to you.

You will receive:

1. Multi-timeframe technical evidence.
2. Momentum and volatility evidence.
3. Wider crypto market context.
4. BTC and ETH context.
5. Market breadth and stress.
6. Relative-strength information.
7. Historical pattern-memory evidence.
8. Historical outcomes of similar setups.

IMPORTANT RULES:

- Do not invent market data.
- Do not invent indicators.
- Do not invent historical examples.
- Do not assume missing information is positive.
- Treat missing information as uncertainty.
- Do not blindly agree with the proposed direction.
- Identify conflicting evidence.
- Give greater confidence when independent evidence agrees.
- Reduce confidence when important evidence conflicts.
- Treat small historical samples cautiously.
- Historical similarity is evidence, not proof.
- Strong recent performance does not guarantee future results.
- Do not recommend leverage.
- Do not recommend position size.
- Do not create stop losses.
- Do not create take-profit levels.
- Do not place or suggest executing a trade.
- Do not change the bot's strategy rules.
- Do not change the bot's confidence threshold.
- Do not claim certainty.

Your score is an AI EVIDENCE SCORE, not the final signal
confidence.

The final confidence is calculated elsewhere using multiple
independent components.

Return ONLY valid JSON.

Required JSON structure:

{
  "ai_score": 0,
  "setup_quality": "NEUTRAL",
  "market_alignment": "MIXED",
  "historical_support": "INSUFFICIENT_DATA",
  "risk_level": "MODERATE",
  "technical_support": [],
  "technical_conflicts": [],
  "market_support": [],
  "market_conflicts": [],
  "historical_supporting_points": [],
  "historical_warning_points": [],
  "main_risks": [],
  "reasoning_summary": "",
  "data_quality": 0,
  "uncertainty": 100
}

ai_score:
0 to 100.

data_quality:
0 to 100.
Higher means the supplied evidence is complete and useful.

uncertainty:
0 to 100.
Higher means the evidence is less reliable, incomplete,
conflicting or statistically weak.

setup_quality must be one of:
VERY_WEAK
WEAK
NEUTRAL
GOOD
VERY_GOOD
EXCEPTIONAL

market_alignment must be one of:
STRONGLY_AGAINST
AGAINST
MIXED
SUPPORTIVE
STRONGLY_SUPPORTIVE

historical_support must be one of:
INSUFFICIENT_DATA
NEGATIVE
MIXED
POSITIVE
STRONGLY_POSITIVE

risk_level must be one of:
LOW
MODERATE
HIGH
VERY_HIGH

Keep reasoning concise and evidence based.
""".strip()


# ============================================================
# BUILD USER PAYLOAD
# ============================================================


def build_user_prompt(
    evidence_package: Dict[str, Any],
) -> str:

    safe_package = (
        make_json_safe(
            evidence_package
        )
    )

    return (
        "Analyse this market opportunity.\n\n"
        + json.dumps(
            safe_package,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


# ============================================================
# DEFAULT AI RESULT
#
# Used when AI is not connected or unavailable.
#
# IMPORTANT:
#
# We do NOT give the opportunity a fake positive AI score.
# ============================================================


def unavailable_ai_result(
    reason: str = "AI not connected",
) -> Dict[str, Any]:

    return {

        "available":
        False,

        "ai_score":
        None,

        "setup_quality":
        "NEUTRAL",

        "market_alignment":
        "MIXED",

        "historical_support":
        "INSUFFICIENT_DATA",

        "risk_level":
        "MODERATE",

        "technical_support":
        [],

        "technical_conflicts":
        [],

        "market_support":
        [],

        "market_conflicts":
        [],

        "historical_supporting_points":
        [],

        "historical_warning_points":
        [],

        "main_risks":
        [],

        "reasoning_summary":
        clean_text(
            reason,
            500,
        ),

        "data_quality":
        0.0,

        "uncertainty":
        100.0,

        "ai_analyst_version":
        AI_ANALYST_VERSION,
    }


# ============================================================
# VALIDATE AI RESPONSE
# ============================================================


def validate_ai_response(
    response: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        response,
        dict,
    ):

        return unavailable_ai_result(
            "AI returned invalid data."
        )

    # Fail closed: all numerical fields are required and must be within range.
    numbers = {}
    for field in ("ai_score", "data_quality", "uncertainty"):
        value = safe_float(response.get(field))
        if value is None or not 0.0 <= value <= 100.0:
            return unavailable_ai_result("AI response has missing or invalid " + field + ".")
        numbers[field] = value
    ai_score = numbers["ai_score"]
    data_quality = numbers["data_quality"]
    uncertainty = numbers["uncertainty"]

    setup_quality = (
        clean_text(
            response.get(
                "setup_quality",
                "NEUTRAL",
            ),
            50,
        )
        .upper()
    )

    if setup_quality not in (
        VALID_SETUP_QUALITY
    ):

        setup_quality = (
            "NEUTRAL"
        )

    market_alignment = (
        clean_text(
            response.get(
                "market_alignment",
                "MIXED",
            ),
            50,
        )
        .upper()
    )

    if market_alignment not in (
        VALID_MARKET_ALIGNMENT
    ):

        market_alignment = (
            "MIXED"
        )

    historical_support = (
        clean_text(
            response.get(
                "historical_support",
                "INSUFFICIENT_DATA",
            ),
            50,
        )
        .upper()
    )

    if historical_support not in (
        VALID_HISTORICAL_SUPPORT
    ):

        historical_support = (
            "INSUFFICIENT_DATA"
        )

    risk_level = (
        clean_text(
            response.get(
                "risk_level",
                "MODERATE",
            ),
            50,
        )
        .upper()
    )

    if risk_level not in (
        VALID_RISK_LEVELS
    ):

        risk_level = (
            "MODERATE"
        )

    return {

        "available":
        True,

        "ai_score":
        round(
            ai_score,
            2,
        ),

        "setup_quality":
        setup_quality,

        "market_alignment":
        market_alignment,

        "historical_support":
        historical_support,

        "risk_level":
        risk_level,

        "technical_support":
        clean_list(
            response.get(
                "technical_support"
            )
        ),

        "technical_conflicts":
        clean_list(
            response.get(
                "technical_conflicts"
            )
        ),

        "market_support":
        clean_list(
            response.get(
                "market_support"
            )
        ),

        "market_conflicts":
        clean_list(
            response.get(
                "market_conflicts"
            )
        ),

        "historical_supporting_points":
        clean_list(
            response.get(
                "historical_supporting_points"
            )
        ),

        "historical_warning_points":
        clean_list(
            response.get(
                "historical_warning_points"
            )
        ),

        "main_risks":
        clean_list(
            response.get(
                "main_risks"
            )
        ),

        "reasoning_summary":
        clean_text(
            response.get(
                "reasoning_summary"
            ),
            1500,
        ),

        "data_quality":
        round(
            data_quality,
            2,
        ),

        "uncertainty":
        round(
            uncertainty,
            2,
        ),

        "ai_analyst_version":
        AI_ANALYST_VERSION,
    }


# ============================================================
# PARSE RAW AI TEXT
# ============================================================


def parse_ai_json(
    raw_text: str,
) -> Dict[str, Any]:

    if not raw_text:

        return unavailable_ai_result(
            "AI returned an empty response."
        )

    text = (
        str(
            raw_text
        )
        .strip()
    )

    # Remove accidental markdown wrappers.

    if text.startswith(
        "```"
    ):

        lines = (
            text.splitlines()
        )

        if lines:

            lines = lines[
                1:
            ]

        if (
            lines
            and lines[-1]
            .strip()
            .startswith(
                "```"
            )
        ):

            lines = lines[
                :-1
            ]

        text = "\n".join(
            lines
        ).strip()

    try:

        data = json.loads(
            text
        )

    except Exception:

        return unavailable_ai_result(
            "AI response was not valid JSON."
        )

    return validate_ai_response(
        data
    )


# ============================================================
# AI RELIABILITY FACTOR
#
# The future confidence engine can use this to decide
# how much influence the AI result deserves.
#
# High data quality + low uncertainty = more useful.
# ============================================================


def calculate_ai_reliability(
    ai_result: Dict[str, Any],
) -> float:

    if not ai_result.get(
        "available"
    ):

        return 0.0

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

    quality_factor = (
        data_quality
        / 100.0
    )

    certainty_factor = (
        1.0
        - (
            uncertainty
            / 100.0
        )
    )

    reliability = (
        quality_factor
        * certainty_factor
    )

    return round(
        clamp(
            reliability,
            0.0,
            1.0,
        ),
        4,
    )


# ============================================================
# AI ANALYSIS PLACEHOLDER
#
# We deliberately do NOT connect OpenAI yet.
#
# When all files are finished, this function will be wired
# to the AI API.
# ============================================================


def analyze_with_ai(
    symbol: str,
    direction: str,
    current_price: float,
    technical_analysis: Dict[str, Any],
    market_context: Dict[str, Any],
    memory_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    evidence_package = (
        build_ai_evidence_package(
            symbol=symbol,
            direction=direction,
            current_price=current_price,
            technical_analysis=technical_analysis,
            market_context=market_context,
            memory_analysis=memory_analysis,
        )
    )

    result = unavailable_ai_result("AI disabled by default.")
    if os.getenv(AI_ENABLED_FLAG, "false").strip().lower() != "true":
        result["evidence_package"] = evidence_package
        return result

    # Bound payload, one request, no retries, and a strict timeout.
    if evidence_package["current_price"] is None or evidence_package["current_price"] <= 0:
        result = unavailable_ai_result("Invalid current price.")
    elif evidence_package["proposed_direction"] not in ("LONG", "SHORT"):
        result = unavailable_ai_result("Invalid direction.")
    elif not evidence_package["technical_evidence"] or not evidence_package["market_evidence"]:
        result = unavailable_ai_result("Insufficient technical or market evidence.")
    else:
        result = _request_openai(evidence_package)

    if result.get("available") and not evidence_package["historical_memory"].get("memory_available"):
        # Reject contradictory model claims rather than silently trusting them.
        if (result.get("historical_support") != "INSUFFICIENT_DATA"
                or result.get("historical_supporting_points")):
            result = unavailable_ai_result("AI claimed support from unusable historical memory.")

    result[
        "evidence_package"
    ] = evidence_package

    return result


# ============================================================
# OPT-IN OPENAI REQUEST — ONE CALL, NO AUTOMATIC RETRIES
# ============================================================


def _request_openai(evidence_package: Dict[str, Any]) -> Dict[str, Any]:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return unavailable_ai_result("OPENAI_API_KEY not configured.")

    # Fixed model and fixed output budget prevent env-driven cost escalation.
    model = "gpt-4o-mini"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(evidence_package)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 900,
    }
    try:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        if len(body) > 24000:
            return unavailable_ai_result("Evidence package exceeds 24 KB request limit.")
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={"Authorization": "Bearer " + key,
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(32769)
        if len(raw) > 32768:
            return unavailable_ai_result("AI response exceeds size limit.")
        envelope = json.loads(raw.decode("utf-8"))
        choices = envelope.get("choices", [])
        if not choices or choices[0].get("finish_reason") != "stop":
            return unavailable_ai_result("AI response incomplete or refused.")
        content = choices[0].get("message", {}).get("content")
        result = parse_ai_json(content)
        # Never log credentials, full response envelopes, or raw market evidence.
        return result
    except urllib.error.HTTPError as exc:
        return unavailable_ai_result("AI HTTP error (status %s)." % exc.code)
    except (urllib.error.URLError, TimeoutError):
        return unavailable_ai_result("AI connection failed or timed out.")
    except (ValueError, KeyError, TypeError, UnicodeError, OSError):
        return unavailable_ai_result("AI response or request processing failed.")


# ============================================================
# BUILD RESULT FOR MEMORY STORAGE
# ============================================================


def build_ai_memory_record(
    ai_result: Dict[str, Any],
) -> Dict[str, Any]:

    return {

        "available":
        ai_result.get(
            "available",
            False,
        ),

        "ai_score":
        ai_result.get(
            "ai_score"
        ),

        "ai_reliability":
        calculate_ai_reliability(
            ai_result
        ),

        "setup_quality":
        ai_result.get(
            "setup_quality"
        ),

        "market_alignment":
        ai_result.get(
            "market_alignment"
        ),

        "historical_support":
        ai_result.get(
            "historical_support"
        ),

        "risk_level":
        ai_result.get(
            "risk_level"
        ),

        "technical_support":
        ai_result.get(
            "technical_support",
            [],
        ),

        "technical_conflicts":
        ai_result.get(
            "technical_conflicts",
            [],
        ),

        "market_support":
        ai_result.get(
            "market_support",
            [],
        ),

        "market_conflicts":
        ai_result.get(
            "market_conflicts",
            [],
        ),

        "historical_supporting_points":
        ai_result.get(
            "historical_supporting_points",
            [],
        ),

        "historical_warning_points":
        ai_result.get(
            "historical_warning_points",
            [],
        ),

        "main_risks":
        ai_result.get(
            "main_risks",
            [],
        ),

        "reasoning_summary":
        ai_result.get(
            "reasoning_summary",
            "",
        ),

        "data_quality":
        ai_result.get(
            "data_quality"
        ),

        "uncertainty":
        ai_result.get(
            "uncertainty"
        ),

        "ai_analyst_version":
        AI_ANALYST_VERSION,
    }


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- AI MARKET ANALYST",
        flush=True,
    )

    print(
        "TECHNICAL EVIDENCE INPUT: READY",
        flush=True,
    )

    print(
        "MARKET CONTEXT INPUT: READY",
        flush=True,
    )

    print(
        "HISTORICAL MEMORY INPUT: READY",
        flush=True,
    )

    print(
        "CONFLICT DETECTION STRUCTURE: READY",
        flush=True,
    )

    print(
        "UNCERTAINTY TRACKING: READY",
        flush=True,
    )

    print(
        "AI RELIABILITY WEIGHTING: READY",
        flush=True,
    )

    print(
        "STRUCTURED JSON VALIDATION: READY",
        flush=True,
    )

    print("OPENAI CONNECTION: OPT-IN ONLY", flush=True)
    if os.getenv(AI_TEST_FLAG, "false").strip().lower() == "true":
        # Synthetic data only: not a real trading signal or performance record.
        diagnostic = analyze_with_ai(
            symbol="BTCUSDT", direction="LONG", current_price=100.0,
            technical_analysis={"timeframes": {"1h": "synthetic mixed"}},
            market_context={"regime": "synthetic uncertain"},
            memory_analysis={"memory_usable": False},
        )
        print("AI ONE-SHOT DIAGNOSTIC: " +
              ("PASS" if diagnostic.get("available") else "UNAVAILABLE"), flush=True)
        print("AI DIAGNOSTIC REASON: " +
              ("valid structured response" if diagnostic.get("available") else
               diagnostic.get("reasoning_summary", "unknown")), flush=True)
        print("AI DIAGNOSTIC: SYNTHETIC ONLY; NO SENDS OR TRADES", flush=True)

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
