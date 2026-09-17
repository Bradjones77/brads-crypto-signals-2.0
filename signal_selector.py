import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# SIGNAL SELECTOR V1
#
# PURPOSE:
#
# Receive fully analysed opportunities AFTER:
#
# - Technical analysis
# - Market context
# - Historical memory
# - AI analysis
# - Confidence engine
#
# Then decide which opportunities are allowed to move
# forward to the Telegram formatting layer.
#
#
# HARD RULE:
#
# 0 - 74.99 = NEVER SEND
# 75 - 100  = ELIGIBLE
#
#
# IMPORTANT:
#
# This file does NOT:
#
# - Calculate technical indicators
# - Calculate final confidence
# - Place trades
# - Access Bitget
# - Access OpenAI
# - Send Telegram
# - Change confidence scores
#
# ============================================================


SIGNAL_SELECTOR_VERSION = "signals2-selector-v1"

MIN_CONFIDENCE = 75.0


# ============================================================
# OPTIONAL SELECTION CONTROLS
#
# These are NOT confidence rules.
#
# They simply stop duplicate / stale / malformed signals.
#
# We can tune these during final integration.
# ============================================================


DEFAULT_MAX_SIGNALS_PER_BATCH = 5

DEFAULT_MAX_SIGNAL_AGE_SECONDS = 180

DEFAULT_SYMBOL_COOLDOWN_MINUTES = 30


# ============================================================
# HELPERS
# ============================================================


def utc_now():

    return datetime.now(
        timezone.utc
    )


def safe_float(
    value,
    default=None,
):

    try:

        if value is None:
            return default

        result = float(
            value
        )

        if not math.isfinite(
            result
        ):
            return default

        return result

    except Exception:

        return default


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


def normalize_symbol(
    symbol,
) -> str:

    return (
        str(
            symbol or ""
        )
        .upper()
        .strip()
    )


def normalize_direction(
    direction,
) -> str:

    direction = (
        str(
            direction or ""
        )
        .upper()
        .strip()
    )

    if direction not in {
        "LONG",
        "SHORT",
    }:

        return "UNKNOWN"

    return direction


def ensure_datetime(
    value,
) -> Optional[datetime]:

    if value is None:

        return None

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:

            value = value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(
        value,
        (int, float),
    ):

        value = float(
            value
        )

        if value > 10_000_000_000:

            value /= 1000.0

        try:

            return datetime.fromtimestamp(
                value,
                tz=timezone.utc,
            )

        except Exception:

            return None

    if isinstance(
        value,
        str,
    ):

        try:

            result = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            if result.tzinfo is None:

                result = result.replace(
                    tzinfo=timezone.utc
                )

            return result

        except Exception:

            return None

    return None


# ============================================================
# EXTRACT CONFIDENCE RESULT
# ============================================================


def get_confidence_result(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    result = opportunity.get(
        "confidence_result"
    )

    if isinstance(
        result,
        dict,
    ):

        return result

    # Fallback allows the selector to accept a flattened
    # opportunity structure later.

    return {

        "final_confidence":
        opportunity.get(
            "final_confidence"
        ),

        "eligible":
        opportunity.get(
            "eligible"
        ),

        "decision":
        opportunity.get(
            "decision"
        ),

        "overall_data_quality":
        opportunity.get(
            "overall_data_quality"
        ),

        "evidence_agreement":
        opportunity.get(
            "evidence_agreement"
        ),

        "component_scores":
        opportunity.get(
            "component_scores",
            {},
        ),
    }


# ============================================================
# BASIC VALIDATION
# ============================================================


def validate_opportunity(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    reasons = []

    if not isinstance(
        opportunity,
        dict,
    ):

        return {

            "valid":
            False,

            "reasons":
            [
                "Opportunity is not a dictionary"
            ],
        }

    symbol = normalize_symbol(
        opportunity.get(
            "symbol"
        )
    )

    direction = normalize_direction(
        opportunity.get(
            "direction"
        )
    )

    price = safe_float(
        opportunity.get(
            "current_price",
            opportunity.get(
                "entry_price"
            ),
        )
    )

    if not symbol:

        reasons.append(
            "Missing symbol"
        )

    if direction == "UNKNOWN":

        reasons.append(
            "Invalid direction"
        )

    if (
        price is None
        or price <= 0
    ):

        reasons.append(
            "Invalid market price"
        )

    confidence_result = (
        get_confidence_result(
            opportunity
        )
    )

    confidence = safe_float(
        confidence_result.get(
            "final_confidence"
        )
    )

    if confidence is None:

        reasons.append(
            "Missing final confidence"
        )

    return {

        "valid":
        len(
            reasons
        )
        == 0,

        "reasons":
        reasons,
    }


# ============================================================
# CONFIDENCE GATE
#
# This deliberately repeats the hard 75 threshold.
#
# Even if another module accidentally marks a 74 signal as
# eligible, this selector will reject it.
# ============================================================


def passes_confidence_gate(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    confidence_result = (
        get_confidence_result(
            opportunity
        )
    )

    confidence = safe_float(
        confidence_result.get(
            "final_confidence"
        )
    )

    if confidence is None:

        return {

            "passed":
            False,

            "confidence":
            None,

            "reason":
            "No final confidence",
        }

    confidence = clamp(
        confidence,
        0.0,
        100.0,
    )

    if confidence < MIN_CONFIDENCE:

        return {

            "passed":
            False,

            "confidence":
            confidence,

            "reason":
            (
                f"Confidence {confidence:.2f} "
                f"is below {MIN_CONFIDENCE:.0f}"
            ),
        }

    # Confidence engine must also have approved
    # its own evidence gates.

    if not bool(
        confidence_result.get(
            "eligible",
            False,
        )
    ):

        return {

            "passed":
            False,

            "confidence":
            confidence,

            "reason":
            (
                confidence_result.get(
                    "rejection_reason"
                )
                or
                "Confidence engine did not mark opportunity eligible"
            ),
        }

    return {

        "passed":
        True,

        "confidence":
        confidence,

        "reason":
        None,
    }


# ============================================================
# SIGNAL AGE
# ============================================================


def calculate_signal_age_seconds(
    opportunity: Dict[str, Any],
    now=None,
) -> Optional[float]:

    if now is None:

        now = utc_now()

    now = ensure_datetime(
        now
    )

    observed_at = (
        ensure_datetime(
            opportunity.get(
                "observed_at",
                opportunity.get(
                    "opportunity_time",
                    opportunity.get(
                        "created_at"
                    ),
                ),
            )
        )
    )

    if (
        now is None
        or observed_at is None
    ):

        return None

    return max(
        0.0,
        (
            now
            - observed_at
        ).total_seconds(),
    )


# ============================================================
# STALE SIGNAL CHECK
# ============================================================


def passes_age_gate(
    opportunity: Dict[str, Any],
    now=None,
    max_age_seconds: int = DEFAULT_MAX_SIGNAL_AGE_SECONDS,
) -> Dict[str, Any]:

    age = (
        calculate_signal_age_seconds(
            opportunity,
            now=now,
        )
    )

    # Missing timestamp is not automatically rejected here.
    # Validation/integration can decide whether timestamps
    # become mandatory later.

    if age is None:

        return {

            "passed":
            True,

            "age_seconds":
            None,

            "reason":
            None,
        }

    if age > max_age_seconds:

        return {

            "passed":
            False,

            "age_seconds":
            round(
                age,
                2,
            ),

            "reason":
            (
                f"Opportunity is stale "
                f"({age:.0f}s old)"
            ),
        }

    return {

        "passed":
        True,

        "age_seconds":
        round(
            age,
            2,
        ),

        "reason":
        None,
    }


# ============================================================
# DUPLICATE KEY
#
# LONG and SHORT are intentionally different keys.
# ============================================================


def build_signal_key(
    opportunity: Dict[str, Any],
) -> str:

    symbol = normalize_symbol(
        opportunity.get(
            "symbol"
        )
    )

    direction = normalize_direction(
        opportunity.get(
            "direction"
        )
    )

    return (
        f"{symbol}:{direction}"
    )


# ============================================================
# COOLDOWN CHECK
#
# The final controller can give this function a dictionary
# containing the most recent signal time for each
# symbol/direction.
#
# No database connection is added here yet.
# ============================================================


def passes_cooldown_gate(
    opportunity: Dict[str, Any],
    recent_signal_times: Optional[
        Dict[str, Any]
    ] = None,
    now=None,
    cooldown_minutes: int = DEFAULT_SYMBOL_COOLDOWN_MINUTES,
) -> Dict[str, Any]:

    if not recent_signal_times:

        return {

            "passed":
            True,

            "reason":
            None,

            "remaining_seconds":
            0,
        }

    if now is None:

        now = utc_now()

    now = ensure_datetime(
        now
    )

    key = build_signal_key(
        opportunity
    )

    previous = ensure_datetime(
        recent_signal_times.get(
            key
        )
    )

    if (
        now is None
        or previous is None
    ):

        return {

            "passed":
            True,

            "reason":
            None,

            "remaining_seconds":
            0,
        }

    cooldown_seconds = (
        max(
            0,
            int(
                cooldown_minutes
            ),
        )
        * 60
    )

    elapsed = (
        now
        - previous
    ).total_seconds()

    if elapsed < 0:

        elapsed = 0

    remaining = max(
        0.0,
        cooldown_seconds
        - elapsed,
    )

    if remaining > 0:

        return {

            "passed":
            False,

            "reason":
            (
                f"{key} is still in cooldown"
            ),

            "remaining_seconds":
            round(
                remaining,
                2,
            ),
        }

    return {

        "passed":
        True,

        "reason":
        None,

        "remaining_seconds":
        0,
    }


# ============================================================
# OPPORTUNITY RANKING SCORE
#
# IMPORTANT:
#
# This does NOT replace final confidence.
#
# Every selected signal must already be >= 75.
#
# Ranking is only used when several eligible opportunities
# exist at the same time.
# ============================================================


def calculate_selection_score(
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:

    confidence_result = (
        get_confidence_result(
            opportunity
        )
    )

    confidence = clamp(
        safe_float(
            confidence_result.get(
                "final_confidence"
            ),
            0.0,
        ),
        0.0,
        100.0,
    )

    data_quality = clamp(
        safe_float(
            confidence_result.get(
                "overall_data_quality"
            ),
            0.0,
        ),
        0.0,
        1.0,
    )

    evidence_agreement = (
        confidence_result.get(
            "evidence_agreement",
            {}
        )
        or {}
    )

    agreement = clamp(
        safe_float(
            evidence_agreement.get(
                "agreement"
            ),
            0.5,
        ),
        0.0,
        1.0,
    )

    # Confidence remains dominant.
    #
    # Quality and agreement only help order opportunities
    # that have already passed 75.

    selection_score = (

        confidence
        * 0.80

        +

        (
            data_quality
            * 100.0
        )
        * 0.10

        +

        (
            agreement
            * 100.0
        )
        * 0.10
    )

    return {

        "selection_score":
        round(
            clamp(
                selection_score,
                0.0,
                100.0,
            ),
            2,
        ),

        "confidence":
        round(
            confidence,
            2,
        ),

        "data_quality":
        round(
            data_quality,
            4,
        ),

        "agreement":
        round(
            agreement,
            4,
        ),
    }


# ============================================================
# EVALUATE ONE OPPORTUNITY
# ============================================================


def evaluate_opportunity(
    opportunity: Dict[str, Any],
    recent_signal_times: Optional[
        Dict[str, Any]
    ] = None,
    now=None,
    max_age_seconds: int = DEFAULT_MAX_SIGNAL_AGE_SECONDS,
    cooldown_minutes: int = DEFAULT_SYMBOL_COOLDOWN_MINUTES,
) -> Dict[str, Any]:

    if now is None:

        now = utc_now()

    validation = (
        validate_opportunity(
            opportunity
        )
    )

    if not validation[
        "valid"
    ]:

        return {

            "selected":
            False,

            "status":
            "REJECTED",

            "reason":
            "; ".join(
                validation[
                    "reasons"
                ]
            ),

            "confidence":
            None,

            "selection_score":
            None,
        }

    confidence_gate = (
        passes_confidence_gate(
            opportunity
        )
    )

    if not confidence_gate[
        "passed"
    ]:

        return {

            "selected":
            False,

            "status":
            "REJECTED",

            "reason":
            confidence_gate[
                "reason"
            ],

            "confidence":
            confidence_gate[
                "confidence"
            ],

            "selection_score":
            None,
        }

    age_gate = (
        passes_age_gate(
            opportunity,
            now=now,
            max_age_seconds=max_age_seconds,
        )
    )

    if not age_gate[
        "passed"
    ]:

        return {

            "selected":
            False,

            "status":
            "REJECTED",

            "reason":
            age_gate[
                "reason"
            ],

            "confidence":
            confidence_gate[
                "confidence"
            ],

            "selection_score":
            None,
        }

    cooldown_gate = (
        passes_cooldown_gate(
            opportunity,
            recent_signal_times=recent_signal_times,
            now=now,
            cooldown_minutes=cooldown_minutes,
        )
    )

    if not cooldown_gate[
        "passed"
    ]:

        return {

            "selected":
            False,

            "status":
            "REJECTED",

            "reason":
            cooldown_gate[
                "reason"
            ],

            "confidence":
            confidence_gate[
                "confidence"
            ],

            "selection_score":
            None,
        }

    ranking = (
        calculate_selection_score(
            opportunity
        )
    )

    return {

        "selected":
        True,

        "status":
        "ELIGIBLE",

        "reason":
        None,

        "confidence":
        ranking[
            "confidence"
        ],

        "selection_score":
        ranking[
            "selection_score"
        ],

        "data_quality":
        ranking[
            "data_quality"
        ],

        "agreement":
        ranking[
            "agreement"
        ],

        "age_seconds":
        age_gate[
            "age_seconds"
        ],
    }


# ============================================================
# SELECT SIGNALS FROM A BATCH
# ============================================================


def select_signals(
    opportunities: List[Dict[str, Any]],
    recent_signal_times: Optional[
        Dict[str, Any]
    ] = None,
    now=None,
    max_signals: int = DEFAULT_MAX_SIGNALS_PER_BATCH,
    max_age_seconds: int = DEFAULT_MAX_SIGNAL_AGE_SECONDS,
    cooldown_minutes: int = DEFAULT_SYMBOL_COOLDOWN_MINUTES,
) -> Dict[str, Any]:

    if now is None:

        now = utc_now()

    if not isinstance(
        opportunities,
        list,
    ):

        opportunities = []

    evaluated = []

    eligible = []

    rejected = []

    for index, opportunity in enumerate(
        opportunities
    ):

        result = (
            evaluate_opportunity(
                opportunity=opportunity,
                recent_signal_times=recent_signal_times,
                now=now,
                max_age_seconds=max_age_seconds,
                cooldown_minutes=cooldown_minutes,
            )
        )

        record = {

            "index":
            index,

            "symbol":
            normalize_symbol(
                opportunity.get(
                    "symbol"
                )
                if isinstance(
                    opportunity,
                    dict,
                )
                else ""
            ),

            "direction":
            normalize_direction(
                opportunity.get(
                    "direction"
                )
                if isinstance(
                    opportunity,
                    dict,
                )
                else ""
            ),

            "evaluation":
            result,

            "opportunity":
            opportunity,
        }

        evaluated.append(
            record
        )

        if result.get(
            "selected"
        ):

            eligible.append(
                record
            )

        else:

            rejected.append(
                record
            )

    # --------------------------------------------------------
    # SORT BEST FIRST
    # --------------------------------------------------------

    eligible.sort(
        key=lambda item: (
            safe_float(
                item[
                    "evaluation"
                ].get(
                    "selection_score"
                ),
                0.0,
            ),
            safe_float(
                item[
                    "evaluation"
                ].get(
                    "confidence"
                ),
                0.0,
            ),
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # REMOVE DUPLICATES WITHIN SAME BATCH
    #
    # Keep the highest-ranked version.
    # --------------------------------------------------------

    unique_eligible = []

    duplicate_rejections = []

    seen_keys = set()

    for record in eligible:

        key = build_signal_key(
            record[
                "opportunity"
            ]
        )

        if key in seen_keys:

            duplicate_record = dict(
                record
            )

            duplicate_record[
                "evaluation"
            ] = {

                **record[
                    "evaluation"
                ],

                "selected":
                False,

                "status":
                "REJECTED",

                "reason":
                (
                    "Lower-ranked duplicate "
                    "in same selection batch"
                ),
            }

            duplicate_rejections.append(
                duplicate_record
            )

            continue

        seen_keys.add(
            key
        )

        unique_eligible.append(
            record
        )

    # --------------------------------------------------------
    # BATCH LIMIT
    # --------------------------------------------------------

    safe_max_signals = max(
        1,
        int(
            max_signals
        ),
    )

    selected = (
        unique_eligible[
            :safe_max_signals
        ]
    )

    overflow = (
        unique_eligible[
            safe_max_signals:
        ]
    )

    overflow_rejections = []

    for record in overflow:

        overflow_record = dict(
            record
        )

        overflow_record[
            "evaluation"
        ] = {

            **record[
                "evaluation"
            ],

            "selected":
            False,

            "status":
            "NOT_SELECTED",

            "reason":
            (
                "Eligible but ranked below "
                "batch selection limit"
            ),
        }

        overflow_rejections.append(
            overflow_record
        )

    all_rejected = (

        rejected

        + duplicate_rejections

        + overflow_rejections
    )

    # --------------------------------------------------------
    # CLEAN SELECTED OUTPUT
    # --------------------------------------------------------

    selected_opportunities = []

    for rank, record in enumerate(
        selected,
        start=1,
    ):

        opportunity = dict(
            record[
                "opportunity"
            ]
        )

        opportunity[
            "selection_rank"
        ] = rank

        opportunity[
            "selection_score"
        ] = record[
            "evaluation"
        ].get(
            "selection_score"
        )

        opportunity[
            "selector_status"
        ] = "SELECTED"

        opportunity[
            "selector_version"
        ] = SIGNAL_SELECTOR_VERSION

        selected_opportunities.append(
            opportunity
        )

    return {

        "selector_version":
        SIGNAL_SELECTOR_VERSION,

        "threshold":
        MIN_CONFIDENCE,

        "total_opportunities":
        len(
            opportunities
        ),

        "eligible_before_batch_limit":
        len(
            unique_eligible
        ),

        "selected_count":
        len(
            selected_opportunities
        ),

        "rejected_count":
        len(
            all_rejected
        ),

        "selected":
        selected_opportunities,

        "rejected":
        all_rejected,

        "evaluated":
        evaluated,
    }


# ============================================================
# MEMORY DECISION RECORD
#
# This allows us to store WHY an opportunity was:
#
# - selected
# - rejected below 75
# - stale
# - cooldown blocked
# - duplicate
# - eligible but not selected
#
# That will be useful when we later analyse whether the
# selector itself is helping or hurting performance.
# ============================================================


def build_selector_memory_record(
    opportunity: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> Dict[str, Any]:

    return {

        "signal_selector_version":
        SIGNAL_SELECTOR_VERSION,

        "symbol":
        normalize_symbol(
            opportunity.get(
                "symbol"
            )
        ),

        "direction":
        normalize_direction(
            opportunity.get(
                "direction"
            )
        ),

        "status":
        evaluation.get(
            "status"
        ),

        "selected":
        evaluation.get(
            "selected",
            False,
        ),

        "reason":
        evaluation.get(
            "reason"
        ),

        "confidence":
        evaluation.get(
            "confidence"
        ),

        "selection_score":
        evaluation.get(
            "selection_score"
        ),

        "data_quality":
        evaluation.get(
            "data_quality"
        ),

        "agreement":
        evaluation.get(
            "agreement"
        ),

        "age_seconds":
        evaluation.get(
            "age_seconds"
        ),
    }


# ============================================================
# SIMPLE HELPER
# ============================================================


def has_selected_signals(
    selection_result: Dict[str, Any],
) -> bool:

    if not isinstance(
        selection_result,
        dict,
    ):

        return False

    return bool(
        selection_result.get(
            "selected"
        )
    )


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- SIGNAL SELECTOR",
        flush=True,
    )

    print(
        "HARD MINIMUM CONFIDENCE:",
        MIN_CONFIDENCE,
        flush=True,
    )

    print(
        "0-74.99: NEVER SELECTED",
        flush=True,
    )

    print(
        "75-100: ELIGIBLE FOR SELECTION",
        flush=True,
    )

    print(
        "STALE SIGNAL PROTECTION: READY",
        flush=True,
    )

    print(
        "DUPLICATE PROTECTION: READY",
        flush=True,
    )

    print(
        "COOLDOWN STRUCTURE: READY",
        flush=True,
    )

    print(
        "MULTI-SIGNAL RANKING: READY",
        flush=True,
    )

    print(
        "REJECTED OPPORTUNITY MEMORY: READY",
        flush=True,
    )

    print(
        "NO TELEGRAM CODE",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )
