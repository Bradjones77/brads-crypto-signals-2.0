"""BRAD'S SIGNALS BOT 2.0 - controlled Telegram end-to-end test.

Synthetic signal only.
Uses the real telegram_formatter -> telegram_sender path.
No database writes. No market scan. No trade execution.
"""
import sys
from datetime import datetime, timezone

import telegram_formatter
import telegram_sender

TEST_SCORE = 82.0

def main():
    print("TELEGRAM E2E TEST: START", flush=True)
    print("SYNTHETIC ONLY: True", flush=True)
    print("DATABASE WRITES: NONE", flush=True)
    print("TRADE EXECUTION: NONE", flush=True)

    opportunity = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100000.00,
        "observed_at": datetime.now(timezone.utc),
        "selector_status": "SELECTED",
        "confidence_result": {
            "final_confidence": TEST_SCORE,
            "eligible": True,
            "decision": "ELIGIBLE",
            "evidence_gates": {
                "passed": True,
                "reasons": [],
            },
        },
    }

    record = telegram_formatter.build_signal_message_record(opportunity)

    if record.get("ready") is not True:
        print(
            "TELEGRAM E2E TEST: FAIL (formatter rejected synthetic approved signal)",
            flush=True,
        )
        sys.exit(1)

    print(
        "TELEGRAM E2E TEST: FORMATTER PASS (score=82.0; threshold=80.0)",
        flush=True,
    )

    # Make the Telegram message unmistakably synthetic so it cannot be confused
    # with a live market signal.
    record["message"] = (
        "BRAD'S SIGNALS BOT 2.0 - CONTROLLED TEST\n\n"
        "SYNTHETIC SIGNAL - NOT A REAL TRADE\n"
        "BTCUSDT LONG\n"
        "Internal confidence score: 82/100\n"
        "Entry: TEST DATA ONLY\n\n"
        "Formatter -> Sender -> Telegram: TEST\n"
        "No trade executed.\n"
        "Not written to learning memory."
    )

    result = telegram_sender.send_signal_record(record)

    if result.get("sent") is not True:
        print(
            "TELEGRAM E2E TEST: FAIL (" +
            str(result.get("reason") or "unknown") +
            ")",
            flush=True,
        )
        sys.exit(1)

    print("TELEGRAM E2E TEST: PASS", flush=True)
    print("TELEGRAM MESSAGE SENT: 1", flush=True)
    print("DATABASE WRITES: 0", flush=True)
    print("TRADES: 0", flush=True)

if __name__ == "__main__":
    main()
