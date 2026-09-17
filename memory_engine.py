import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


# ============================================================
# BRAD'S SIGNALS BOT 2.0
# LONG-TERM MEMORY ENGINE
#
# PURPOSE:
# Build a permanent historical brain.
#
# Stores:
# - EVERY analysed opportunity
# - sent signals
# - rejected opportunities
# - technical fingerprints
# - market context
# - confidence information
# - AI analysis
# - future price outcomes
# - MFE / MAE
#
# THIS FILE:
# - DOES NOT PLACE TRADES
# - DOES NOT SEND TELEGRAM
# - DOES NOT USE BITGET API KEYS
# ============================================================


DATABASE_URL = (
    os.getenv("SIGNALS2_DATABASE_URL")
    or ""
).strip()


# ============================================================
# TIME HELPERS
# ============================================================


def utc_now():
    return datetime.now(
        timezone.utc
    )


def utc_iso():
    return utc_now().isoformat()


# ============================================================
# JSON HELPERS
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
# DATABASE CONNECTION
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

    # --------------------------------------------------------
    # MAIN OPPORTUNITY MEMORY
    # --------------------------------------------------------

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

            outcome_status TEXT
                NOT NULL
                DEFAULT 'PENDING',

            outcome_updated_at
                TIMESTAMPTZ
        )
        """
    )

    # --------------------------------------------------------
    # FUTURE OUTCOME MEMORY
    #
    # Stores what ACTUALLY happened after each opportunity.
    # --------------------------------------------------------

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

            price_10m
                DOUBLE PRECISION,

            price_30m
                DOUBLE PRECISION,

            price_1h
                DOUBLE PRECISION,

            price_4h
                DOUBLE PRECISION,

            price_12h
                DOUBLE PRECISION,

            price_24h
                DOUBLE PRECISION,

            return_10m_pct
                DOUBLE PRECISION,

            return_30m_pct
                DOUBLE PRECISION,

            return_1h_pct
                DOUBLE PRECISION,

            return_4h_pct
                DOUBLE PRECISION,

            return_12h_pct
                DOUBLE PRECISION,

            return_24h_pct
                DOUBLE PRECISION,

            max_favorable_excursion_pct
                DOUBLE PRECISION,

            max_adverse_excursion_pct
                DOUBLE PRECISION,

            highest_price
                DOUBLE PRECISION,

            lowest_price
                DOUBLE PRECISION,

            direction_correct_10m
                BOOLEAN,

            direction_correct_30m
                BOOLEAN,

            direction_correct_1h
                BOOLEAN,

            direction_correct_4h
                BOOLEAN,

            direction_correct_12h
                BOOLEAN,

            direction_correct_24h
                BOOLEAN,

            outcome_complete
                BOOLEAN
                NOT NULL
                DEFAULT FALSE,

            last_updated
                TIMESTAMPTZ
        )
        """
    )

    # --------------------------------------------------------
    # MARKET SNAPSHOT MEMORY
    #
    # Allows us to keep market conditions even when there
    # was no qualifying signal.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # AI / MODEL VERSION HISTORY
    #
    # Important later when testing whether a new model
    # actually improved results.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # INDEXES
    # --------------------------------------------------------

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

    if created_at is None:
        created_at = utc_now()

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
            strategy_version
        )

        VALUES (

            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,
            %s::jsonb,%s::jsonb,%s::jsonb,
            %s::jsonb,%s::jsonb,%s::jsonb,
            %s,%s
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
        ),
    )

    # --------------------------------------------------------
    # Every opportunity also gets an outcome record.
    #
    # Even rejected opportunities are tracked.
    #
    # This is important because later we can discover:
    #
    # "The bot rejected this setup, but what actually happened?"
    #
    # That prevents selection bias.
    # --------------------------------------------------------

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
        INSERT INTO
        signals2_market_snapshots (

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
# GET ONE OPPORTUNITY
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
# RECENT HISTORICAL OPPORTUNITIES
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

            r.return_10m_pct,
            r.return_30m_pct,
            r.return_1h_pct,
            r.return_4h_pct,
            r.return_12h_pct,
            r.return_24h_pct,

            r.max_favorable_excursion_pct,
            r.max_adverse_excursion_pct,

            r.direction_correct_10m,
            r.direction_correct_30m,
            r.direction_correct_1h,
            r.direction_correct_4h,
            r.direction_correct_12h,
            r.direction_correct_24h,

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
# GET PENDING OUTCOMES
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

        "price_10m",
        "price_30m",
        "price_1h",
        "price_4h",
        "price_12h",
        "price_24h",

        "return_10m_pct",
        "return_30m_pct",
        "return_1h_pct",
        "return_4h_pct",
        "return_12h_pct",
        "return_24h_pct",

        "max_favorable_excursion_pct",
        "max_adverse_excursion_pct",

        "highest_price",
        "lowest_price",

        "direction_correct_10m",
        "direction_correct_30m",
        "direction_correct_1h",
        "direction_correct_4h",
        "direction_correct_12h",
        "direction_correct_24h",

        "outcome_complete",
    }

    updates = []
    params = []

    for key, value in (
        fields.items()
    ):

        if key not in allowed:
            continue

        updates.append(
            f"{key} = %s"
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
# MARK OUTCOME COMPLETE
# ============================================================


def mark_outcome_complete(
    conn,
    opportunity_id: str,
):

    update_outcome(
        conn,
        opportunity_id,
        outcome_complete=True,
    )

    cur = conn.cursor()

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


def memory_statistics(conn):

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

    result = cur.fetchone()

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
        "- LONG-TERM MEMORY ENGINE",
        flush=True,
    )

    print(
        "EVERY OPPORTUNITY MEMORY: READY",
        flush=True,
    )

    print(
        "REJECTED SETUP MEMORY: READY",
        flush=True,
    )

    print(
        "MULTI-HORIZON OUTCOME MEMORY: READY",
        flush=True,
    )

    print(
        "MODEL VERSION HISTORY: READY",
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
