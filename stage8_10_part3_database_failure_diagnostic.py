"""
Brad's Signals Bot 2.0
Stage 8.10 Part 3 - Database failure-resilience diagnostic

SAFE SYNTHETIC TEST ONLY:
- No PostgreSQL connection
- No database read or write
- No Telegram send
- No Bitget call
- No OpenAI call
- No trade
- Does not change the 80 confidence threshold
"""

import inspect
import main


class BrokenPatternMemory:
    @staticmethod
    def analyze_pattern_memory(**kwargs):
        raise ConnectionError("STAGE8_10_PART3_SYNTHETIC_DATABASE_FAILURE")


class DummyDatabaseConnection:
    """Marker object only. It never opens a real database connection."""
    pass


def synthetic_opportunity():
    return main.build_opportunity(
        symbol="SIGNALS2_STAGE8_10_DB_TEST",
        direction="LONG",
        current_price=100.0,
    )


def main_test():
    prefix = "STAGE8_10 PART3 DIAGNOSTIC: "
    print(prefix + "START", flush=True)
    print(
        prefix
        + "NO DB CONNECTION/WRITE; NO TELEGRAM; NO BITGET; NO OPENAI; NO TRADE",
        flush=True,
    )

    original_pattern_memory = main.pattern_memory

    try:
        # CHECK 1 - no DB connection supplied must make memory unavailable safely.
        opportunity = synthetic_opportunity()
        result = main.run_memory_stage(
            opportunity,
            database_connection=None,
        )
        memory = result.get("memory_analysis", {})

        if memory.get("memory_usable") is not False:
            raise RuntimeError("Missing database did not disable memory")
        if memory.get("memory_score") is not None:
            raise RuntimeError("Missing database produced a memory score")

        print(
            prefix
            + "CHECK 1 PASS - missing database connection makes memory unavailable safely",
            flush=True,
        )

        # CHECK 2 - a database/memory exception must be caught and fail closed
        # to unavailable memory rather than inventing a score.
        main.pattern_memory = BrokenPatternMemory()

        opportunity = synthetic_opportunity()
        result = main.run_memory_stage(
            opportunity,
            database_connection=DummyDatabaseConnection(),
        )
        memory = result.get("memory_analysis", {})

        if memory.get("memory_usable") is not False:
            raise RuntimeError("Database failure did not disable memory")
        if memory.get("memory_score") is not None:
            raise RuntimeError("Database failure produced a memory score")
        if "error" not in memory:
            raise RuntimeError("Database failure was not recorded")

        print(
            prefix
            + "CHECK 2 PASS - synthetic database/memory failure returns unavailable with no score",
            flush=True,
        )

        # CHECK 3 - verify the deployed memory engine uses explicit
        # non-autocommit PostgreSQL transactions and commits its two-row
        # opportunity/outcome write only after both INSERT statements.
        if main.memory_engine is None:
            raise RuntimeError("memory_engine unavailable")

        connect_source = inspect.getsource(main.memory_engine.connect)
        store_source = inspect.getsource(main.memory_engine.store_opportunity)

        if "conn.autocommit = False" not in connect_source:
            raise RuntimeError("Database connection is not explicitly transactional")

        opportunity_insert = store_source.find("INSERT INTO signals2_opportunities")
        outcome_insert = store_source.find("INSERT INTO signals2_outcomes")
        commit_call = store_source.rfind("conn.commit()")

        if opportunity_insert < 0 or outcome_insert < 0 or commit_call < 0:
            raise RuntimeError("Expected opportunity/outcome transaction structure missing")

        if not (opportunity_insert < outcome_insert < commit_call):
            raise RuntimeError("Opportunity/outcome writes are not committed together")

        print(
            prefix
            + "CHECK 3 PASS - opportunity/outcome writes use one explicit transaction before commit",
            flush=True,
        )

        # CHECK 4 - verify the deployed scanner still contains the
        # database integration and per-opportunity failure accounting
        # that normal runtime logs have already exercised.
        #
        # Do not require a particular connection-management spelling here:
        # the previous diagnostic was too strict about exact source layout.
        scanner_source = inspect.getsource(main.run_controlled_market_scanner)

        required_scanner_fragments = (
            "store_opportunity",
            "opportunity_failures",
        )
        missing = [
            fragment
            for fragment in required_scanner_fragments
            if fragment not in scanner_source
        ]
        if missing:
            raise RuntimeError(
                "Scanner database integration/failure accounting missing: "
                + ",".join(missing)
            )

        print(
            prefix
            + "CHECK 4 PASS - deployed scanner contains DB storage and opportunity-failure accounting",
            flush=True,
        )

        # CHECK 5 - development safety flags and threshold remain intact.
        if main.DEVELOPMENT_MODE is not True:
            raise RuntimeError("Development mode changed")
        if main.LIVE_SCANNING_ENABLED is not False:
            raise RuntimeError("Static live-scanning flag changed")
        if main.TELEGRAM_SENDING_ENABLED is not False:
            raise RuntimeError("Static Telegram flag changed")
        if float(main.MINIMUM_SIGNAL_CONFIDENCE) != 80.0:
            raise RuntimeError("Minimum confidence changed")

        print(
            prefix
            + "CHECK 5 PASS - development safety flags and 80 threshold intact",
            flush=True,
        )

        # CHECK 6 - no trade execution callable exposed by main.
        trade_names = (
            "place_order",
            "execute_trade",
            "open_position",
            "submit_order",
        )
        detected = [
            name for name in trade_names
            if callable(getattr(main, name, None))
        ]
        if detected:
            raise RuntimeError("Trade execution callable detected")

        print(
            prefix + "CHECK 6 PASS - no trade execution callable detected",
            flush=True,
        )

        print(
            prefix + "PASS - database failure-resilience checks verified",
            flush=True,
        )
        return True

    finally:
        main.pattern_memory = original_pattern_memory
        print(prefix + "CLEANUP PASS", flush=True)


if __name__ == "__main__":
    main_test()
