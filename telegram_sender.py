1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
"""BRAD'S SIGNALS BOT 2.0 - Telegram sender transport."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

SENDER_VERSION = "signals2-telegram-sender-v1.0"
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
    if not isinstance(record, dict):
        return False, "record_not_dict"
    if record.get("ready") is not True:
        return False, "record_not_ready"

    message = record.get("message")
    if not isinstance(message, str) or not message.strip():
        message = record.get("telegram_message")
    if not isinstance(message, str) or not message.strip():
        return False, "missing_message"

    opportunity = record.get("opportunity")
    if isinstance(opportunity, dict):
        selector = opportunity.get("selector_result") or {}
        confidence_result = opportunity.get("confidence_result") or {}
        status = str(selector.get("selector_status") or selector.get("status") or "").upper()
        if status != "SELECTED":
            return False, "selector_not_selected"
        if confidence_result.get("eligible") is not True:
            return False, "confidence_not_eligible"
        if str(confidence_result.get("decision") or "").upper() != "ELIGIBLE":
            return False, "confidence_decision_not_eligible"
        confidence = _safe_float(
            confidence_result.get("final_confidence")
            if confidence_result.get("final_confidence") is not None
            else confidence_result.get("confidence")
        )
    else:
        status = str(record.get("selector_status") or record.get("status") or "").upper()
        if status != "SELECTED":
            return False, "selector_not_selected"
        confidence = _safe_float(
            record.get("final_confidence")
            if record.get("final_confidence") is not None
            else record.get("confidence")
        )

    if confidence is None or confidence < MIN_CONFIDENCE:
        return False, "confidence_below_80"
    return True, "approved"

