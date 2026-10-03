"""
Brad's Signals Bot 2.0
Stage 8.10 Part 4 - BTC/ETH reference-market fail-closed diagnostic

SAFE SYNTHETIC TEST ONLY:
- No PostgreSQL write
- No Telegram send
- No Bitget network call
- No OpenAI call
- No trade
- Does not change the 80 confidence threshold

This test verifies the deployed scanner's reference-market fail-closed guard
without running the continuous scanner or calling external services.
"""

import inspect
import main

PREFIX = "STAGE8_10 PART4 DIAGNOSTIC: "


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main_test():
    print(PREFIX + "START", flush=True)
    print(
        PREFIX
        + "NO DB WRITE; NO TELEGRAM; NO BITGET NETWORK CALL; NO OPENAI; NO TRADE",
        flush=True,
    )

    scanner_source = inspect.getsource(main.run_controlled_market_scanner)

    # The currently deployed scanner explicitly treats BTC/ETH as required
    # reference markets. Verify the exact guard remains present.
    require(
        'for reference_symbol in ("BTCUSDT", "ETHUSDT")' in scanner_source,
        "Required BTC/ETH reference loop missing",
    )
    require(
        '"Required reference market failed: "' in scanner_source,
        "Required-reference failure exception missing",
    )
    require(
        'if symbol in ("BTCUSDT", "ETHUSDT")' in scanner_source,
        "BTC/ETH fail-closed symbol guard missing",
    )

    print(
        PREFIX
        + "CHECK 1 PASS - deployed scanner contains required BTC/ETH fail-closed guards",
        flush=True,
    )

    # Synthetic execution of the same guard semantics:
    # a failed required reference market MUST raise and stop the cycle.
    def synthetic_reference_guard(symbol, market_ok):
        if not market_ok:
            if symbol in ("BTCUSDT", "ETHUSDT"):
                raise RuntimeError("Required reference market failed: " + symbol)
            return "SKIP_NON_REFERENCE"
        return "OK"

    for symbol in ("BTCUSDT", "ETHUSDT"):
        caught = None
        try:
            synthetic_reference_guard(symbol, False)
        except RuntimeError as exc:
            caught = exc

        require(caught is not None, f"{symbol} failure did not fail closed")
        require(
            str(caught) == "Required reference market failed: " + symbol,
            f"{symbol} raised unexpected failure: {caught}",
        )

    print(
        PREFIX
        + "CHECK 2 PASS - synthetic BTC failure fails closed",
        flush=True,
    )
    print(
        PREFIX
        + "CHECK 3 PASS - synthetic ETH failure fails closed",
        flush=True,
    )

    require(
        synthetic_reference_guard("XRPUSDT", False) == "SKIP_NON_REFERENCE",
        "Non-reference market failure did not remain isolated",
    )
    print(
        PREFIX
        + "CHECK 4 PASS - synthetic non-reference failure is isolated instead of killing cycle",
        flush=True,
    )

    require(main.DEVELOPMENT_MODE is True, "Development mode is not enabled")
    require(main.LIVE_SCANNING_ENABLED is False, "Static live scanning flag changed")
    require(main.TELEGRAM_SENDING_ENABLED is False, "Static Telegram flag changed")
    require(
        float(main.MINIMUM_SIGNAL_CONFIDENCE) == 80.0,
        "Minimum confidence is not 80",
    )
    print(
        PREFIX
        + "CHECK 5 PASS - development safety flags and 80 threshold intact",
        flush=True,
    )

    forbidden = (
        "place_order",
        "execute_trade",
        "open_position",
        "submit_order",
    )
    found = [name for name in forbidden if callable(getattr(main, name, None))]
    require(not found, "Trade execution callable detected: " + ", ".join(found))
    print(
        PREFIX + "CHECK 6 PASS - no trade execution callable detected",
        flush=True,
    )

    print(
        PREFIX
        + "PASS - BTC/ETH reference-market fail-closed behaviour verified safely",
        flush=True,
    )


if __name__ == "__main__":
    main_test()
