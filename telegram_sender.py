"""BRAD'S SIGNALS BOT 2.0 - Telegram sender transport.

Accepts only records already approved by telegram_formatter.py and performs
independent transport-level safety checks before calling Telegram.
No trade execution code exists in this module.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

SENDER_VERSION = "signals2-telegram-sender-v1.1"
MIN_CONFIDENCE = 80.0
REQUEST_TIMEOUT_SECONDS = 10
BOT_TOKEN_ENV = "SIGNALS2_TELEGRAM_BOT_TOKEN"
CHAT_ID_ENV = "SIGNALS2_TELEGRAM_CHAT_ID"

def _safe_float(value: Any):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _validate_record(record: Dict[str, Any]):
    # telegram_formatter.build_signal_message_record() returns:
    # ready, formatter_version, symbol, direction, confidence,
    # entry_price, signal_time, message, errors.
    if not isinstance(record, dict):
        return False, "record_not_dict"
    if record.get("ready") is not True:
        return False, "record_not_ready"
    if record.get("errors") not in (None, []):
        return False, "formatter_errors_present"

    symbol = str(record.get("symbol") or "").strip().upper()
    direction = str(record.get("direction") or "").strip().upper()
    confidence = _safe_float(record.get("confidence"))
    entry_price = _safe_float(record.get("entry_price"))
    signal_time = record.get("signal_time")
    message = record.get("message")

    if not symbol or not symbol.endswith("USDT"):
        return False, "invalid_symbol"
    if direction not in ("LONG", "SHORT"):
        return False, "invalid_direction"
    if confidence is None or confidence < MIN_CONFIDENCE or confidence > 100:
        return False, "confidence_not_eligible"
    if entry_price is None or entry_price <= 0:
        return False, "invalid_entry_price"
    if signal_time is None:
        return False, "missing_signal_time"
    if not isinstance(message, str) or not message.strip():
        return False, "missing_message"

    # Basic consistency checks prevent a mismatched formatter record being sent.
    upper_message = message.upper()
    if symbol not in upper_message or direction not in upper_message:
        return False, "message_record_mismatch"

    return True, "approved"

def send_signal_record(record: Dict[str, Any]) -> Dict[str, Any]:
    valid, reason = _validate_record(record)
    if not valid:
        return {
            "ok": False, "sent": False, "reason": reason,
            "sender_version": SENDER_VERSION,
        }

    token = os.getenv(BOT_TOKEN_ENV, "").strip()
    chat_id = os.getenv(CHAT_ID_ENV, "").strip()
    if not token or not chat_id:
        return {
            "ok": False, "sent": False,
            "reason": "telegram_credentials_missing",
            "sender_version": SENDER_VERSION,
        }

    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": record["message"],
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "BradsSignalsBot2.0/" + SENDER_VERSION,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {}

        if data.get("ok") is not True:
            return {
                "ok": False, "sent": False,
                "reason": "telegram_api_rejected",
                "sender_version": SENDER_VERSION,
            }

        result = data.get("result") or {}
        return {
            "ok": True,
            "sent": True,
            "reason": "sent",
            "telegram_message_id": result.get("message_id"),
            "sender_version": SENDER_VERSION,
        }

    except urllib.error.HTTPError as exc:
        return {
            "ok": False, "sent": False,
            "reason": "telegram_http_error",
            "http_status": getattr(exc, "code", None),
            "sender_version": SENDER_VERSION,
        }
    except urllib.error.URLError:
        return {
            "ok": False, "sent": False,
            "reason": "telegram_network_error",
            "sender_version": SENDER_VERSION,
        }
    except TimeoutError:
        return {
            "ok": False, "sent": False,
            "reason": "telegram_timeout",
            "sender_version": SENDER_VERSION,
        }
    except Exception as exc:
        return {
            "ok": False, "sent": False,
            "reason": "telegram_unexpected_error",
            "error_type": type(exc).__name__,
            "sender_version": SENDER_VERSION,
        }

def sender_status() -> Dict[str, Any]:
    return {
        "sender_version": SENDER_VERSION,
        "minimum_confidence": MIN_CONFIDENCE,
        "bot_token_configured": bool(os.getenv(BOT_TOKEN_ENV, "").strip()),
        "chat_id_configured": bool(os.getenv(CHAT_ID_ENV, "").strip()),
        "trade_execution": False,
    }
