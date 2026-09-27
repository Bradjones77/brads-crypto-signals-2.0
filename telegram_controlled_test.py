import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BOT_TOKEN = os.environ.get("SIGNALS2_TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("SIGNALS2_TELEGRAM_CHAT_ID", "").strip()

TEST_MESSAGE = (
    "BRAD'S SIGNALS BOT 2.0 - TELEGRAM TEST\n\n"
    "Telegram connection test: PASS\n"
    "Minimum signal confidence: 80\n"
    "Development mode only\n"
    "No trade executed."
)

def fail(message):
    print("TELEGRAM CONTROLLED TEST: FAIL - " + str(message), flush=True)
    sys.exit(1)

def main():
    print("TELEGRAM CONTROLLED TEST: START", flush=True)
    print("TELEGRAM CONTROLLED TEST: scanner signals NOT connected", flush=True)
    print("TELEGRAM CONTROLLED TEST: trade execution NONE", flush=True)

    if not BOT_TOKEN:
        fail("SIGNALS2_TELEGRAM_BOT_TOKEN is missing")
    if not CHAT_ID:
        fail("SIGNALS2_TELEGRAM_CHAT_ID is missing")

    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": TEST_MESSAGE,
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            description = json.loads(detail).get("description", "HTTP " + str(exc.code))
        except Exception:
            description = "HTTP " + str(exc.code)
        fail(description)
    except Exception as exc:
        fail(type(exc).__name__ + ": " + str(exc))

    try:
        payload = json.loads(raw)
    except Exception:
        fail("Telegram returned a non-JSON response")

    if payload.get("ok") is not True:
        fail(payload.get("description") or "Telegram API returned ok=false")

    message_id = (payload.get("result") or {}).get("message_id")
    print("TELEGRAM CONTROLLED TEST: PASS (message_id=" + str(message_id) + ")", flush=True)
    print("TELEGRAM CONTROLLED TEST: exactly one test message sent", flush=True)
    print("TELEGRAM CONTROLLED TEST: no scanner signal sent; no trade executed", flush=True)

if __name__ == "__main__":
    main()
