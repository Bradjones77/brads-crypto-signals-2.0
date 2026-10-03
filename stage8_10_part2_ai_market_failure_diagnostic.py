"""
Brad's Signals Bot 2.0
Stage 8.10 Part 2 - AI / analysis failure-resilience diagnostic

SAFE TEST ONLY:
- No Telegram send
- No PostgreSQL write
- No Bitget call
- No OpenAI call
- No trade
- Does not change the 80 confidence threshold
"""

import inspect
import main


class BrokenAIAnalyst:
    @staticmethod
    def analyze_with_ai(**kwargs):
        raise ConnectionError("STAGE8_10_PART2_SYNTHETIC_AI_FAILURE")


class BrokenConfidenceEngine:
    @staticmethod
    def calculate_final_confidence(**kwargs):
        raise RuntimeError("STAGE8_10_PART2_SYNTHETIC_CONFIDENCE_FAILURE")


def synthetic_opportunity():
    return {
        "symbol": "SIGNALS2_STAGE8_10_TEST",
        "direction": "LONG",
        "current_price": 100.0,
        "technical_analysis": {},
        "market_context": {},
        "memory_analysis": {},
    }


def main_test():
    prefix = "STAGE8_10 PART2 DIAGNOSTIC: "
    print(prefix + "START", flush=True)
    print(
        prefix
        + "NO TELEGRAM SEND; NO DB WRITE; NO BITGET; NO OPENAI; NO TRADE",
        flush=True,
    )

    original_ai_analyst = main.ai_analyst
    original_confidence_engine = main.confidence_engine

    try:
        # CHECK 1 - AI exception must become unavailable, never an invented score.
        main.ai_analyst = BrokenAIAnalyst()
        opportunity = synthetic_opportunity()
        result = main.run_ai_stage(opportunity)
        ai_result = result.get("ai_result", {})

        if ai_result.get("available") is not False:
            raise RuntimeError("AI failure did not become unavailable")
        if ai_result.get("ai_score") is not None:
            raise RuntimeError("AI failure produced a score")
        if ai_result.get("error_type") != "ConnectionError":
            raise RuntimeError("AI failure type was not preserved")

        print(
            prefix
            + "CHECK 1 PASS - synthetic AI/API failure returns unavailable with no score",
            flush=True,
        )

        # CHECK 2 - confidence-engine exception must reject at zero.
        main.confidence_engine = BrokenConfidenceEngine()
        opportunity = synthetic_opportunity()
        result = main.run_confidence_stage(opportunity)
        confidence = result.get("confidence_result", {})

        if float(confidence.get("final_confidence", -1)) != 0.0:
            raise RuntimeError("Confidence failure did not return zero")
        if confidence.get("eligible") is not False:
            raise RuntimeError("Confidence failure remained eligible")
        if confidence.get("decision") != "REJECTED":
            raise RuntimeError("Confidence failure was not rejected")

        print(
            prefix
            + "CHECK 2 PASS - confidence-engine failure fails closed as REJECTED",
            flush=True,
        )

        # CHECK 3 - verify deployed scanner contains mandatory BTC/ETH reference
        # fail-closed guards. This is source inspection only: it makes no market call.
        scanner_source = inspect.getsource(main.run_controlled_market_scanner)

        required_fragments = (
            'for reference_symbol in ("BTCUSDT", "ETHUSDT")',
            '"Required reference market failed: "',
            'if symbol in ("BTCUSDT", "ETHUSDT")',
            '"BTC and ETH snapshots use different five-minute candles"',
        )

        missing = [
            fragment for fragment in required_fragments
            if fragment not in scanner_source
        ]
        if missing:
            raise RuntimeError(
                "Required BTC/ETH reference-market fail-closed guard missing"
            )

        print(
            prefix
            + "CHECK 3 PASS - deployed scanner contains BTC/ETH reference-market fail-closed guards",
            flush=True,
        )

        # CHECK 4 - development safety flags and threshold remain intact.
        if main.DEVELOPMENT_MODE is not True:
            raise RuntimeError("Development mode changed")
        if main.LIVE_SCANNING_ENABLED is not False:
            raise RuntimeError("Static live-scanning flag changed")
        if main.TELEGRAM_SENDING_ENABLED is not False:
            raise RuntimeError("Static Telegram flag changed")
        if float(main.MINIMUM_SIGNAL_CONFIDENCE) != 80.0:
            raise RuntimeError("Minimum confidence changed")

        print(
            prefix
            + "CHECK 4 PASS - development safety flags and 80 threshold intact",
            flush=True,
        )

        # CHECK 5 - no trade execution callable exposed by main.
        trade_names = (
            "place_order",
            "execute_trade",
            "open_position",
            "submit_order",
        )
        detected = [
            name for name in trade_names
            if callable(getattr(main, name, None))
        ]
        if detected:
            raise RuntimeError("Trade execution callable detected")

        print(
            prefix + "CHECK 5 PASS - no trade execution callable detected",
            flush=True,
        )

        print(
            prefix + "PASS - AI and analysis failure-resilience checks verified",
            flush=True,
        )
        return True

    finally:
        main.ai_analyst = original_ai_analyst
        main.confidence_engine = original_confidence_engine
        print(prefix + "CLEANUP PASS", flush=True)


if __name__ == "__main__":
    main_test()
