import os
import json
import hashlib
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# LONG-TERM MEMORY ENGINE V2
#
# MEMORY HORIZONS:
# 30 sec
# 1 min
# 5 min
# 10 min
# 30 min
# 1 hour
# 4 hours
# 12 hours
# 24 hours
#
# Stores BOTH:
# - signals eventually sent
# - opportunities eventually rejected
#
# THIS FILE DOES NOT:
# - Place trades
# - Modify positions
# - Send Telegram messages
# - Use Bitget credentials
# ============================================================


DATABASE_URL = (
    os.getenv("SIGNALS2_DATABASE_URL")
    or ""
).strip()


MEMORY_SCHEMA_VERSION = "2.0"


# ============================================================
# TIME
# ============================================================


def utc_now():
    return datetime.now(
        timezone.utc
    )


# ============================================================
# JSON
# ============================================================


def safe_json(value):

    try:
        return json.dumps(
            value,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

    except Exception:
        return "{}"


def parse_json(value):

    if value is None:
        return {}

    if isinstance(
        value,
        (dict, list),
    ):
        return value

    try:
        return json.loads(value)

    except Exception:
        return {}


# ============================================================
# UNIQUE OPPORTUNITY ID
# ============================================================


def build_opportunity_id(
    symbol: str,
    direction: str,
    timestamp,
) -> str:

    raw = (
        f"{symbol.upper()}|"
        f"{direction.upper()}|"
        f"{timestamp}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# DATABASE
# ============================================================


def database_configured():

    return bool(
        DATABASE_URL
    )


def connect():

    if not database_configured():

        raise RuntimeError(
            "SIGNALS2_DATABASE_URL "
            "is not configured."
        )

    conn = psycopg2.connect(
        DATABASE_URL
    )

    conn.autocommit = False

    return conn


# ============================================================
# DATABASE SCHEMA
# ============================================================


def ensure_schema(conn):

    cur = conn.cursor()

    # ========================================================
    # OPPORTUNITIES
    # ========================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS
        signals2_opportunities (

            id BIGSERIAL PRIMARY KEY,

            opportunity_id TEXT
                UNIQUE NOT NULL,

            created_at TIMESTAMPTZ
                NOT NULL,

            symbol TEXT
                NOT NULL,

            direction TEXT
                NOT NULL,

            entry_price
                DOUBLE PRECISION,

            final_confidence
                DOUBLE PRECISION,

            technical_confidence
                DOUBLE PRECISION,

            memory_confidence
                DOUBLE PRECISION,

            ai_confidence
                DOUBLE PRECISION,

            market_confidence
                DOUBLE PRECISION,

            decision TEXT
                NOT NULL,

            rejection_reason TEXT,

            signal_sent BOOLEAN
                NOT NULL DEFAULT FALSE,

            technical_features
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            market_features
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            combined_features
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            raw_analysis
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            raw_market_context
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            ai_analysis
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            model_version TEXT,

            strategy_version TEXT,

            memory_schema_version TEXT,

            outcome_status TEXT
                NOT NULL
                DEFAULT 'PENDING',

            outcome_updated_at
                TIMESTAMPTZ
        )
        """
    )

    # ========================================================
    # OUTCOMES
    # ========================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS
        signals2_outcomes (

            id BIGSERIAL PRIMARY KEY,

            opportunity_id TEXT
                UNIQUE NOT NULL,

            symbol TEXT
                NOT NULL,

            direction TEXT
                NOT NULL,

            entry_price
                DOUBLE PRECISION
                NOT NULL,

            opportunity_time
                TIMESTAMPTZ
                NOT NULL,

            -- ================================================
            -- EXACT PRICE CHECKPOINTS
            -- ================================================

            price_30s DOUBLE PRECISION,
            price_1m DOUBLE PRECISION,
            price_5m DOUBLE PRECISION,
            price_10m DOUBLE PRECISION,
            price_30m DOUBLE PRECISION,
            price_1h DOUBLE PRECISION,
            price_4h DOUBLE PRECISION,
            price_12h DOUBLE PRECISION,
            price_24h DOUBLE PRECISION,

            -- ================================================
            -- DIRECTION-ADJUSTED RETURNS
            --
            -- Positive = predicted direction was profitable.
            -- Negative = market moved against prediction.
            -- ================================================

            return_30s_pct DOUBLE PRECISION,
            return_1m_pct DOUBLE PRECISION,
            return_5m_pct DOUBLE PRECISION,
            return_10m_pct DOUBLE PRECISION,
            return_30m_pct DOUBLE PRECISION,
            return_1h_pct DOUBLE PRECISION,
            return_4h_pct DOUBLE PRECISION,
            return_12h_pct DOUBLE PRECISION,
            return_24h_pct DOUBLE PRECISION,

            -- ================================================
            -- WAS DIRECTION CORRECT?
            -- ================================================

            direction_correct_30s BOOLEAN,
            direction_correct_1m BOOLEAN,
            direction_correct_5m BOOLEAN,
            direction_correct_10m BOOLEAN,
            direction_correct_30m BOOLEAN,
            direction_correct_1h BOOLEAN,
            direction_correct_4h BOOLEAN,
            direction_correct_12h BOOLEAN,
            direction_correct_24h BOOLEAN,

            -- ================================================
            -- EXCURSION MEMORY
            --
            -- MFE = best move in predicted direction.
            -- MAE = worst move against predicted direction.
            -- ================================================

            max_favorable_excursion_pct
                DOUBLE PRECISION,

            max_adverse_excursion_pct
                DOUBLE PRECISION,

            highest_price
                DOUBLE PRECISION,

            lowest_price
                DOUBLE PRECISION,

            -- ================================================
            -- SHORT-TERM BEHAVIOUR
            --
            -- These fields help the future learning system
            -- understand HOW a setup developed, rather than
            -- only where price finished.
            -- ================================================

            immediate_move_pct
                DOUBLE PRECISION,

            early_momentum_pct
                DOUBLE PRECISION,

            momentum_5m_pct
                DOUBLE PRECISION,

            momentum_10m_pct
                DOUBLE PRECISION,

            momentum_30m_pct
                DOUBLE PRECISION,

            early_reversal BOOLEAN,

            early_continuation BOOLEAN,

            -- ================================================
            -- COMPLETION
            -- ================================================

            outcome_complete BOOLEAN
                NOT NULL
                DEFAULT FALSE,

            last_updated
                TIMESTAMPTZ
        )
        """
    )

    # ========================================================
    # MARKET SNAPSHOTS
    # ========================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS
        signals2_market_snapshots (

            id BIGSERIAL PRIMARY KEY,

            created_at
                TIMESTAMPTZ NOT NULL,

            market_regime TEXT,

            btc_price
                DOUBLE PRECISION,

            eth_price
                DOUBLE PRECISION,

            btc_alignment
                DOUBLE PRECISION,

            eth_alignment
                DOUBLE PRECISION,

            bullish_market_pct
                DOUBLE PRECISION,

            bearish_market_pct
                DOUBLE PRECISION,

            market_volatility TEXT,

            market_stress TEXT,

            market_stress_score
                DOUBLE PRECISION,

            snapshot
                JSONB NOT NULL
                DEFAULT '{}'::jsonb
        )
        """
    )

    # ========================================================
    # MODEL VERSION HISTORY
    # ========================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS
        signals2_model_versions (

            id BIGSERIAL PRIMARY KEY,

            version TEXT
                UNIQUE NOT NULL,

            created_at
                TIMESTAMPTZ NOT NULL,

            model_type TEXT,

            description TEXT,

            configuration
                JSONB NOT NULL
                DEFAULT '{}'::jsonb,

            active BOOLEAN
                NOT NULL
                DEFAULT FALSE
        )
        """
    )

    # ========================================================
    # INDEXES
    # ========================================================

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_opp_symbol_direction

        ON signals2_opportunities
        (symbol, direction)
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_opp_created

        ON signals2_opportunities
        (created_at DESC)
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_opp_decision

        ON signals2_opportunities
        (decision)
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_opp_confidence

        ON signals2_opportunities
        (final_confidence)
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_outcome_complete

        ON signals2_outcomes
        (outcome_complete)
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_outcome_symbol

        ON signals2_outcomes
        (symbol, direction)
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_signals2_market_created

        ON signals2_market_snapshots
        (created_at DESC)
        """
    )

    conn.commit()


# ============================================================
# INITIALIZE DATABASE
# ============================================================


def initialize_database():

    conn = connect()

    try:

        ensure_schema(
            conn
        )

        print(
            "SIGNALS BOT 2.0 MEMORY DATABASE: READY",
            flush=True,
        )

        print(
            "MEMORY SCHEMA:",
            MEMORY_SCHEMA_VERSION,
            flush=True,
        )

    finally:

        conn.close()


# ============================================================
# STORE EVERY OPPORTUNITY
# ============================================================


def store_opportunity(
    conn,
    symbol: str,
    direction: str,
    entry_price: float,
    decision: str,
    technical_features: Dict[str, Any],
    market_features: Dict[str, Any],
    raw_analysis: Dict[str, Any],
    raw_market_context: Dict[str, Any],
    final_confidence: Optional[float] = None,
    technical_confidence: Optional[float] = None,
    memory_confidence: Optional[float] = None,
    ai_confidence: Optional[float] = None,
    market_confidence: Optional[float] = None,
    rejection_reason: Optional[str] = None,
    signal_sent: bool = False,
    ai_analysis: Optional[Dict[str, Any]] = None,
    model_version: Optional[str] = None,
    strategy_version: Optional[str] = None,
    created_at=None,
):

    # Invalid observations must never enter the learning database.
    symbol = str(symbol).strip().upper()
    direction = str(direction).strip().upper()
    if not symbol or direction not in ("LONG", "SHORT"):
        raise ValueError("A valid symbol and LONG/SHORT direction are required")
    entry_price = float(entry_price)
    if not math.isfinite(entry_price) or entry_price <= 0:
        raise ValueError("A finite, positive entry price is required")

    if created_at is None:

        created_at = utc_now()
    elif isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    created_at = created_at.astimezone(timezone.utc)

    if isinstance(
        created_at,
        str,
    ):

        timestamp_for_id = (
            created_at
        )

    else:

        timestamp_for_id = (
            created_at.isoformat()
        )

    opportunity_id = (
        build_opportunity_id(
            symbol=symbol,
            direction=direction,
            timestamp=timestamp_for_id,
        )
    )

    combined_features = {}

    combined_features.update(
        technical_features or {}
    )

    combined_features.update(
        market_features or {}
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO signals2_opportunities (

            opportunity_id,
            created_at,
            symbol,
            direction,
            entry_price,

            final_confidence,
            technical_confidence,
            memory_confidence,
            ai_confidence,
            market_confidence,

            decision,
            rejection_reason,
            signal_sent,

            technical_features,
            market_features,
            combined_features,

            raw_analysis,
            raw_market_context,
            ai_analysis,

            model_version,
            strategy_version,
            memory_schema_version
        )

        VALUES (

            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,
            %s::jsonb,%s::jsonb,%s::jsonb,
            %s::jsonb,%s::jsonb,%s::jsonb,
            %s,%s,%s
        )

        ON CONFLICT (opportunity_id)
        DO NOTHING
        """,

        (
            opportunity_id,
            created_at,
            symbol.upper(),
            direction.upper(),
            entry_price,

            final_confidence,
            technical_confidence,
            memory_confidence,
            ai_confidence,
            market_confidence,

            decision,
            rejection_reason,
            bool(signal_sent),

            safe_json(
                technical_features
            ),

            safe_json(
                market_features
            ),

            safe_json(
                combined_features
            ),

            safe_json(
                raw_analysis
            ),

            safe_json(
                raw_market_context
            ),

            safe_json(
                ai_analysis or {}
            ),

            model_version,
            strategy_version,
            MEMORY_SCHEMA_VERSION,
        ),
    )

    # ========================================================
    # EVERY opportunity gets tracked.
    #
    # This includes opportunities eventually rejected.
    #
    # This is essential because otherwise the bot only learns
    # from signals it chose to send and develops selection bias.
    # ========================================================

    cur.execute(
        """
        INSERT INTO signals2_outcomes (

            opportunity_id,
            symbol,
            direction,
            entry_price,
            opportunity_time,
            last_updated
        )

        VALUES (
            %s,%s,%s,%s,%s,%s
        )

        ON CONFLICT (opportunity_id)
        DO NOTHING
        """,

        (
            opportunity_id,
            symbol.upper(),
            direction.upper(),
            entry_price,
            created_at,
            utc_now(),
        ),
    )

    conn.commit()

    return opportunity_id


# ============================================================
# STORE MARKET SNAPSHOT
# ============================================================


def store_market_snapshot(
    conn,
    market_context: Dict[str, Any],
    btc_price=None,
    eth_price=None,
):

    major = (
        market_context.get(
            "major_context",
            {}
        )
        or {}
    )

    breadth = (
        market_context.get(
            "breadth",
            {}
        )
        or {}
    )

    volatility = (
        market_context.get(
            "volatility",
            {}
        )
        or {}
    )

    stress = (
        market_context.get(
            "stress",
            {}
        )
        or {}
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO signals2_market_snapshots (

            created_at,
            market_regime,

            btc_price,
            eth_price,

            btc_alignment,
            eth_alignment,

            bullish_market_pct,
            bearish_market_pct,

            market_volatility,

            market_stress,
            market_stress_score,

            snapshot
        )

        VALUES (
            %s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s::jsonb
        )
        """,

        (
            utc_now(),

            major.get(
                "regime"
            ),

            btc_price,
            eth_price,

            major.get(
                "btc_alignment"
            ),

            major.get(
                "eth_alignment"
            ),

            breadth.get(
                "bullish_pct"
            ),

            breadth.get(
                "bearish_pct"
            ),

            volatility.get(
                "market_volatility"
            ),

            stress.get(
                "state"
            ),

            stress.get(
                "stress_score"
            ),

            safe_json(
                market_context
            ),
        ),
    )

    conn.commit()


# ============================================================
# UPDATE AI ANALYSIS
# ============================================================


def update_ai_analysis(
    conn,
    opportunity_id: str,
    ai_analysis: Dict[str, Any],
    ai_confidence: Optional[float] = None,
):

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE signals2_opportunities

        SET
            ai_analysis = %s::jsonb,
            ai_confidence = %s

        WHERE opportunity_id = %s
        """,

        (
            safe_json(
                ai_analysis
            ),

            ai_confidence,

            opportunity_id,
        ),
    )

    conn.commit()


# ============================================================
# UPDATE FINAL DECISION
# ============================================================


def update_final_decision(
    conn,
    opportunity_id: str,
    decision: str,
    final_confidence: float,
    signal_sent: bool,
    rejection_reason: Optional[str] = None,
):

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE signals2_opportunities

        SET
            decision = %s,
            final_confidence = %s,
            signal_sent = %s,
            rejection_reason = %s

        WHERE opportunity_id = %s
        """,

        (
            decision,
            final_confidence,
            bool(signal_sent),
            rejection_reason,
            opportunity_id,
        ),
    )

    conn.commit()


# ============================================================
# GET OPPORTUNITY
# ============================================================


def get_opportunity(
    conn,
    opportunity_id: str,
):

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    cur.execute(
        """
        SELECT *
        FROM signals2_opportunities
        WHERE opportunity_id = %s
        """,

        (
            opportunity_id,
        ),
    )

    row = cur.fetchone()

    if not row:
        return None

    return dict(row)


# ============================================================
# HISTORICAL MEMORY
# ============================================================


def get_recent_opportunities(
    conn,
    limit: int = 1000,
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    completed_only: bool = False,
):

    conditions = []
    params = []

    if symbol:

        conditions.append(
            "o.symbol = %s"
        )

        params.append(
            symbol.upper()
        )

    if direction:

        conditions.append(
            "o.direction = %s"
        )

        params.append(
            direction.upper()
        )

    if completed_only:

        conditions.append(
            "r.outcome_complete = TRUE"
        )

    where_clause = ""

    if conditions:

        where_clause = (
            "WHERE "
            + " AND ".join(
                conditions
            )
        )

    query = f"""
        SELECT

            o.*,

            r.price_30s,
            r.price_1m,
            r.price_5m,
            r.price_10m,
            r.price_30m,
            r.price_1h,
            r.price_4h,
            r.price_12h,
            r.price_24h,

            r.return_30s_pct,
            r.return_1m_pct,
            r.return_5m_pct,
            r.return_10m_pct,
            r.return_30m_pct,
            r.return_1h_pct,
            r.return_4h_pct,
            r.return_12h_pct,
            r.return_24h_pct,

            r.direction_correct_30s,
            r.direction_correct_1m,
            r.direction_correct_5m,
            r.direction_correct_10m,
            r.direction_correct_30m,
            r.direction_correct_1h,
            r.direction_correct_4h,
            r.direction_correct_12h,
            r.direction_correct_24h,

            r.max_favorable_excursion_pct,
            r.max_adverse_excursion_pct,

            r.highest_price,
            r.lowest_price,

            r.immediate_move_pct,
            r.early_momentum_pct,
            r.momentum_5m_pct,
            r.momentum_10m_pct,
            r.momentum_30m_pct,

            r.early_reversal,
            r.early_continuation,

            r.outcome_complete

        FROM signals2_opportunities o

        LEFT JOIN signals2_outcomes r

        ON
            o.opportunity_id
            =
            r.opportunity_id

        {where_clause}

        ORDER BY
            o.created_at DESC

        LIMIT %s
    """

    params.append(
        max(
            1,
            min(
                int(limit),
                10000,
            ),
        )
    )

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    cur.execute(
        query,
        tuple(params),
    )

    return [
        dict(row)
        for row in cur.fetchall()
    ]


# ============================================================
# PENDING OUTCOMES
# ============================================================


def get_pending_outcomes(
    conn,
    limit: int = 500,
):

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    cur.execute(
        """
        SELECT *
        FROM signals2_outcomes

        WHERE
            outcome_complete = FALSE

        ORDER BY
            opportunity_time ASC

        LIMIT %s
        """,

        (
            max(
                1,
                min(
                    int(limit),
                    5000,
                ),
            ),
        ),
    )

    return [
        dict(row)
        for row in cur.fetchall()
    ]


# ============================================================
# UPDATE OUTCOME
# ============================================================


def update_outcome(
    conn,
    opportunity_id: str,
    **fields,
):

    allowed = {

        "price_30s",
        "price_1m",
        "price_5m",
        "price_10m",
        "price_30m",
        "price_1h",
        "price_4h",
        "price_12h",
        "price_24h",

        "return_30s_pct",
        "return_1m_pct",
        "return_5m_pct",
        "return_10m_pct",
        "return_30m_pct",
        "return_1h_pct",
        "return_4h_pct",
        "return_12h_pct",
        "return_24h_pct",

        "direction_correct_30s",
        "direction_correct_1m",
        "direction_correct_5m",
        "direction_correct_10m",
        "direction_correct_30m",
        "direction_correct_1h",
        "direction_correct_4h",
        "direction_correct_12h",
        "direction_correct_24h",

        "max_favorable_excursion_pct",
        "max_adverse_excursion_pct",

        "highest_price",
        "lowest_price",

        "immediate_move_pct",
        "early_momentum_pct",
        "momentum_5m_pct",
        "momentum_10m_pct",
        "momentum_30m_pct",

        "early_reversal",
        "early_continuation",

        "outcome_complete",
    }

    updates = []
    params = []

    for key, value in (
        fields.items()
    ):

        if key not in allowed or value is None:
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        # Keep the first recorded checkpoint. A later re-run must not
        # silently rewrite history with a different candle or quote.
        updates.append(
            f"{key} = COALESCE({key}, %s)" if key != "outcome_complete"
            else "outcome_complete = outcome_complete OR %s"
        )

        params.append(
            value
        )

    if not updates:
        return False

    updates.append(
        "last_updated = %s"
    )

    params.append(
        utc_now()
    )

    params.append(
        opportunity_id
    )

    query = f"""
        UPDATE signals2_outcomes

        SET
            {", ".join(updates)}

        WHERE
            opportunity_id = %s
    """

    cur = conn.cursor()

    cur.execute(
        query,
        tuple(params),
    )

    conn.commit()

    return True


# ============================================================
# COMPLETE OUTCOME
# ============================================================


def mark_outcome_complete(
    conn,
    opportunity_id: str,
):

    cur = conn.cursor()
    cur.execute("""
        SELECT price_1m, price_5m, price_10m, price_30m,
               price_1h, price_4h, price_12h, price_24h
        FROM signals2_outcomes WHERE opportunity_id = %s
        FOR UPDATE
    """, (opportunity_id,))
    row = cur.fetchone()
    if row is None or any(value is None for value in row):
        raise ValueError("Cannot complete an outcome with missing checkpoints")
    cur.execute("""
        UPDATE signals2_outcomes
        SET outcome_complete = TRUE, last_updated = %s
        WHERE opportunity_id = %s
    """, (utc_now(), opportunity_id))


    cur.execute(
        """
        UPDATE signals2_opportunities

        SET
            outcome_status = 'COMPLETE',
            outcome_updated_at = %s

        WHERE
            opportunity_id = %s
        """,

        (
            utc_now(),
            opportunity_id,
        ),
    )

    conn.commit()


# ============================================================
# MODEL VERSIONING
# ============================================================


def register_model_version(
    conn,
    version: str,
    model_type: str,
    description: str,
    configuration: Dict[str, Any],
    active: bool = False,
):

    cur = conn.cursor()

    if active:

        cur.execute(
            """
            UPDATE signals2_model_versions
            SET active = FALSE
            """
        )

    cur.execute(
        """
        INSERT INTO signals2_model_versions (

            version,
            created_at,
            model_type,
            description,
            configuration,
            active
        )

        VALUES (
            %s,%s,%s,%s,%s::jsonb,%s
        )

        ON CONFLICT (version)

        DO UPDATE SET

            model_type =
                EXCLUDED.model_type,

            description =
                EXCLUDED.description,

            configuration =
                EXCLUDED.configuration,

            active =
                EXCLUDED.active
        """,

        (
            version,
            utc_now(),
            model_type,
            description,

            safe_json(
                configuration
            ),

            bool(active),
        ),
    )

    conn.commit()


# ============================================================
# MEMORY STATISTICS
# ============================================================


def memory_statistics(
    conn,
):

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    cur.execute(
        """
        SELECT

            COUNT(*)
                AS total_opportunities,

            COUNT(*) FILTER (
                WHERE signal_sent = TRUE
            )
                AS signals_sent,

            COUNT(*) FILTER (
                WHERE signal_sent = FALSE
            )
                AS rejected_or_not_sent,

            COUNT(*) FILTER (
                WHERE outcome_status = 'COMPLETE'
            )
                AS completed_outcomes

        FROM signals2_opportunities
        """
    )

    result = (
        cur.fetchone()
    )

    return (
        dict(result)
        if result
        else {}
    )


# ============================================================
# SELF TEST
# ============================================================


if __name__ == "__main__":

    print(
        "BRAD'S SIGNALS BOT 2.0 "
        "- LONG-TERM MEMORY ENGINE V2",
        flush=True,
    )

    print(
        "30 SECOND MEMORY: READY",
        flush=True,
    )

    print(
        "1 MINUTE MEMORY: READY",
        flush=True,
    )

    print(
        "5 MINUTE MEMORY: READY",
        flush=True,
    )

    print(
        "10 MINUTE MEMORY: READY",
        flush=True,
    )

    print(
        "30 MINUTE MEMORY: READY",
        flush=True,
    )

    print(
        "1H / 4H / 12H / 24H MEMORY: READY",
        flush=True,
    )

    print(
        "MFE / MAE MEMORY: READY",
        flush=True,
    )

    print(
        "EARLY MOMENTUM / REVERSAL MEMORY: READY",
        flush=True,
    )

    print(
        "UNSENT OPPORTUNITY MEMORY: SCHEMA DEFINED",
        flush=True,
    )

    print(
        "MODEL VERSIONING: SCHEMA DEFINED",
        flush=True,
    )

    print(
        "NO TRADE EXECUTION CODE",
        flush=True,
    )

    if database_configured():

        print(
            "DATABASE VARIABLE PRESENT",
            flush=True,
        )

    else:

        print(
            "DATABASE NOT CONNECTED YET "
            "(EXPECTED DURING BUILD)",
            flush=True,
        )
