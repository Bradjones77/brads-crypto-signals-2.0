"""
BRAD'S SIGNALS BOT 2.0
Stage 8.10 controlled failure-resilience diagnostic

This diagnostic tests failure-handling primitives only.
It does NOT:
- send Telegram messages
- create market signals
- write PostgreSQL records
- call Bitget
- call OpenAI
- place trades
- change confidence thresholds

Tests:
1) Redis signal lock failure -> fail closed
2) Redis scanner lock unavailable/error -> documented fail-open behavior
3) Redis synthetic lock cleanup
4) Telegram runtime safety flags remain valid
5) Trade execution remains absent/disabled
"""

import main

PREFIX = "STAGE8_10 FAILURE DIAGNOSTIC: "


class BrokenRedis:
    def set(self, *args, **kwargs):
        raise ConnectionError("synthetic redis set failure")

    def exists(self, *args, **kwargs):
        raise ConnectionError("synthetic redis exists failure")

    def delete(self, *args, **kwargs):
        raise ConnectionError("synthetic redis delete failure")


def run():
    print(PREFIX + "START", flush=True)
    print(PREFIX + "NO TELEGRAM SEND; NO DB WRITE; NO BITGET; NO OPENAI; NO TRADE", flush=True)

    original_get_redis_client = main.get_redis_client

    try:
        # ----------------------------------------------------
        # Check 1: signal-send Redis failure must fail closed.
        # ----------------------------------------------------
        main.get_redis_client = lambda: BrokenRedis()
        signal_lock = main.acquire_signal_send_lock("SIGNALS2_STAGE8_10_TEST")
        if signal_lock is not False:
            raise RuntimeError("Signal send lock did not fail closed")
        print(PREFIX + "CHECK 1 PASS - Redis signal-send lock failure fails closed", flush=True)

        # ----------------------------------------------------
        # Check 2: scanner Redis lock currently intentionally
        # fails open so Redis outage does not kill analysis.
        # This records/proves the deployed behavior.
        # ----------------------------------------------------
        scanner_lock = main.acquire_scanner_cycle_lock("SIGNALS2_STAGE8_10_TEST")
        if scanner_lock is not True:
            raise RuntimeError("Scanner Redis lock did not use documented fail-open behavior")
        print(PREFIX + "CHECK 2 PASS - scanner Redis lock failure uses documented fail-open behavior", flush=True)

        # ----------------------------------------------------
        # Check 3: restore real Redis and prove lock lifecycle.
        # ----------------------------------------------------
        main.get_redis_client = original_get_redis_client
        client = main.get_redis_client()
        if client is None:
            raise RuntimeError("Real Redis unavailable")

        test_id = "SIGNALS2_STAGE8_10_CLEANUP_TEST"
        lock_key = main.REDIS_SIGNAL_SEND_LOCK_PREFIX + test_id
        sent_key = main.REDIS_SIGNAL_SENT_PREFIX + test_id
        client.delete(lock_key, sent_key)

        if main.acquire_signal_send_lock(test_id) is not True:
            raise RuntimeError("Could not acquire real synthetic signal lock")
        main.release_signal_send_lock(test_id)
        if client.exists(lock_key):
            raise RuntimeError("Synthetic signal lock remained after release")
        client.delete(lock_key, sent_key)
        print(PREFIX + "CHECK 3 PASS - Redis synthetic lock cleanup verified", flush=True)

        # ----------------------------------------------------
        # Check 4: runtime safety flags.
        # ----------------------------------------------------
        if main.DEVELOPMENT_MODE is not True:
            raise RuntimeError("Development mode is not enabled")
        if main.LIVE_SCANNING_ENABLED is not False:
            raise RuntimeError("Static live scanning flag is enabled")
        if main.TELEGRAM_SENDING_ENABLED is not False:
            raise RuntimeError("Static Telegram sending flag is enabled")
        if float(main.MINIMUM_SIGNAL_CONFIDENCE) != 80.0:
            raise RuntimeError("Minimum confidence changed")
