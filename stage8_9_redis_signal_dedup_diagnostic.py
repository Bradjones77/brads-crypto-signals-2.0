"""
BRAD'S SIGNALS BOT 2.0
Stage 8.9 controlled Redis signal dedup diagnostic

Purpose:
- Prove the Redis signal-send lock is exclusive.
- Prove the Redis sent marker blocks duplicate recognition.
- Prove lock release allows a fresh claim.
- Clean up every synthetic Redis key afterward.

Safety:
- No Telegram API call.
- No market signal created.
- No confidence threshold changes.
- No PostgreSQL writes.
- No Bitget order/trade execution.
"""

import uuid
import main


PREFIX = "STAGE8_9 REDIS SIGNAL DEDUP DIAGNOSTIC: "


def run():
    print(PREFIX + "START", flush=True)
    print(PREFIX + "NO TELEGRAM SEND; NO DB WRITE; NO TRADE", flush=True)

    client = main.get_redis_client()
    if client is None:
        raise RuntimeError("Redis unavailable")

    test_id = "SIGNALS2_TEST_" + uuid.uuid4().hex
    lock_key = main.REDIS_SIGNAL_SEND_LOCK_PREFIX + test_id
    sent_key = main.REDIS_SIGNAL_SENT_PREFIX + test_id

    try:
        client.delete(lock_key, sent_key)

        if main.redis_signal_already_sent(test_id):
            raise RuntimeError("Fresh test ID unexpectedly marked sent")
        print(PREFIX + "CHECK 1 PASS - fresh ID is not marked sent", flush=True)

        first_lock = main.acquire_signal_send_lock(test_id)
        if first_lock is not True:
            raise RuntimeError("First send lock was not acquired")
        print(PREFIX + "CHECK 2 PASS - first send lock acquired", flush=True)

        second_lock = main.acquire_signal_send_lock(test_id)
        if second_lock is not False:
            raise RuntimeError("Second concurrent send lock was not blocked")
        print(PREFIX + "CHECK 3 PASS - duplicate concurrent lock blocked", flush=True)

        main.release_signal_send_lock(test_id)
        third_lock = main.acquire_signal_send_lock(test_id)
        if third_lock is not True:
            raise RuntimeError("Lock could not be reacquired after release")
        print(PREFIX + "CHECK 4 PASS - lock release/reacquire works", flush=True)

        marker_written = main.mark_signal_sent_redis(test_id)
        if marker_written is not True:
            raise RuntimeError("Sent marker write failed")
        if main.redis_signal_already_sent(test_id) is not True:
            raise RuntimeError("Sent marker readback failed")
        print(PREFIX + "CHECK 5 PASS - sent marker write/readback works", flush=True)

        main.release_signal_send_lock(test_id)

        # This mirrors the first Redis gate in the real Telegram send path:
        # an already-sent marker means the opportunity must be skipped.
        if not main.redis_signal_already_sent(test_id):
            raise RuntimeError("Duplicate marker disappeared unexpectedly")
        print(PREFIX + "CHECK 6 PASS - duplicate send would be skipped", flush=True)

        print(PREFIX + "PASS - Redis signal dedup protection verified", flush=True)
        return True

    finally:
        # Synthetic test keys must never remain in Redis.
        try:
            client.delete(lock_key, sent_key)
            print(PREFIX + "CLEANUP PASS - synthetic Redis keys removed", flush=True)
        except Exception as exc:
            print(PREFIX + "CLEANUP FAIL (" + type(exc).__name__ + ")", flush=True)


if __name__ == "__main__":
    run()
