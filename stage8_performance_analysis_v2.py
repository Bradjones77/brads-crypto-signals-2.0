import json, os, psycopg2

DB=os.environ.get("SIGNALS2_DATABASE_URL","").strip()

def emit(label, value):
    print("STAGE 8 PERFORMANCE V2: "+label+" "+json.dumps(value,default=str,separators=(",",":")),flush=True)

def rows(cur, sql):
    cur.execute(sql)
    names=[d[0] for d in cur.description]
    return [dict(zip(names,r)) for r in cur.fetchall()]

def one(cur, sql):
    r=rows(cur,sql)
    return r[0] if r else {}

def main():
    print("STAGE 8 PERFORMANCE V2: START (read only; no writes; no sends; no trades)",flush=True)
    if not DB: raise RuntimeError("SIGNALS2_DATABASE_URL is not configured")
    conn=psycopg2.connect(DB); conn.autocommit=False
    try:
        cur=conn.cursor(); cur.execute("SET TRANSACTION READ ONLY")
        base="""FROM signals2_opportunities o JOIN signals2_outcomes x ON x.opportunity_id=o.opportunity_id
        WHERE x.outcome_complete=TRUE AND o.symbol NOT LIKE 'SIGNALS2%%' AND o.final_confidence IS NOT NULL"""

        emit("SAMPLE",one(cur,f"""SELECT COUNT(*) completed,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(x.return_24h_pct) avg_return_24h_pct,AVG(x.max_favorable_excursion_pct) avg_mfe_pct,
        AVG(x.max_adverse_excursion_pct) avg_mae_pct {base}"""))

        emit("CONFIDENCE_BUCKETS",rows(cur,f"""SELECT CASE
        WHEN o.final_confidence<40 THEN '00-39.99' WHEN o.final_confidence<50 THEN '40-49.99'
        WHEN o.final_confidence<60 THEN '50-59.99' WHEN o.final_confidence<65 THEN '60-64.99'
        WHEN o.final_confidence<70 THEN '65-69.99' WHEN o.final_confidence<75 THEN '70-74.99'
        WHEN o.final_confidence<80 THEN '75-79.99' ELSE '80-100' END band,
        COUNT(*) completed,COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(x.return_24h_pct) avg_return_24h_pct,AVG(x.max_favorable_excursion_pct) avg_mfe_pct,
        AVG(x.max_adverse_excursion_pct) avg_mae_pct {base} GROUP BY 1 ORDER BY MIN(o.final_confidence)"""))

        emit("DIRECTION",rows(cur,f"""SELECT o.direction,COUNT(*) completed,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(o.final_confidence) avg_confidence,AVG(x.return_24h_pct) avg_return_24h_pct
        {base} GROUP BY o.direction ORDER BY o.direction"""))

        emit("AI_AVAILABILITY",rows(cur,f"""SELECT CASE WHEN LOWER(COALESCE(o.ai_analysis->>'available',''))='true'
        THEN 'AI_AVAILABLE' ELSE 'AI_NOT_AVAILABLE' END ai_state,COUNT(*) completed,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(o.final_confidence) avg_final_confidence,AVG(o.ai_confidence) avg_ai_confidence,
        AVG(x.return_24h_pct) avg_return_24h_pct {base} GROUP BY 1 ORDER BY 1"""))

        emit("COMPONENTS",one(cur,f"""SELECT COUNT(*) completed,
        AVG(o.technical_confidence) avg_technical,AVG(o.market_confidence) avg_market,
        AVG(o.memory_confidence) avg_memory,AVG(o.ai_confidence) avg_ai,AVG(o.final_confidence) avg_final,
        AVG(o.technical_confidence) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_avg_technical,
        AVG(o.technical_confidence) FILTER(WHERE x.direction_correct_24h IS FALSE) incorrect_avg_technical,
        AVG(o.market_confidence) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_avg_market,
        AVG(o.market_confidence) FILTER(WHERE x.direction_correct_24h IS FALSE) incorrect_avg_market,
        AVG(o.memory_confidence) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_avg_memory,
        AVG(o.memory_confidence) FILTER(WHERE x.direction_correct_24h IS FALSE) incorrect_avg_memory,
        AVG(o.ai_confidence) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_avg_ai,
        AVG(o.ai_confidence) FILTER(WHERE x.direction_correct_24h IS FALSE) incorrect_avg_ai,
        AVG(o.final_confidence) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_avg_final,
        AVG(o.final_confidence) FILTER(WHERE x.direction_correct_24h IS FALSE) incorrect_avg_final {base}"""))

        emit("SYMBOLS_TOP20",rows(cur,f"""SELECT o.symbol,COUNT(*) completed,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(o.final_confidence) avg_confidence,AVG(x.return_24h_pct) avg_return_24h_pct
        {base} GROUP BY o.symbol ORDER BY COUNT(*) DESC,o.symbol LIMIT 20"""))

        emit("HORIZONS",one(cur,f"""SELECT
        COUNT(*) FILTER(WHERE x.direction_correct_5m IS NOT NULL) n_5m,ROUND(100.0*AVG((x.direction_correct_5m)::int),2) correct_5m_pct,AVG(x.return_5m_pct) avg_return_5m_pct,
        COUNT(*) FILTER(WHERE x.direction_correct_30m IS NOT NULL) n_30m,ROUND(100.0*AVG((x.direction_correct_30m)::int),2) correct_30m_pct,AVG(x.return_30m_pct) avg_return_30m_pct,
        COUNT(*) FILTER(WHERE x.direction_correct_1h IS NOT NULL) n_1h,ROUND(100.0*AVG((x.direction_correct_1h)::int),2) correct_1h_pct,AVG(x.return_1h_pct) avg_return_1h_pct,
        COUNT(*) FILTER(WHERE x.direction_correct_4h IS NOT NULL) n_4h,ROUND(100.0*AVG((x.direction_correct_4h)::int),2) correct_4h_pct,AVG(x.return_4h_pct) avg_return_4h_pct,
        COUNT(*) FILTER(WHERE x.direction_correct_12h IS NOT NULL) n_12h,ROUND(100.0*AVG((x.direction_correct_12h)::int),2) correct_12h_pct,AVG(x.return_12h_pct) avg_return_12h_pct,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS NOT NULL) n_24h,ROUND(100.0*AVG((x.direction_correct_24h)::int),2) correct_24h_pct,AVG(x.return_24h_pct) avg_return_24h_pct {base}"""))

        emit("MEMORY_BANDS",rows(cur,f"""SELECT CASE WHEN o.memory_confidence IS NULL THEN 'NULL'
        WHEN o.memory_confidence<40 THEN '00-39.99' WHEN o.memory_confidence<50 THEN '40-49.99'
        WHEN o.memory_confidence<60 THEN '50-59.99' WHEN o.memory_confidence<70 THEN '60-69.99'
        ELSE '70-100' END memory_band,COUNT(*) completed,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(x.return_24h_pct) avg_return_24h_pct {base} GROUP BY 1 ORDER BY 1"""))

        emit("AI_CONFIDENCE_BANDS",rows(cur,f"""SELECT CASE WHEN o.ai_confidence<40 THEN '00-39.99'
        WHEN o.ai_confidence<50 THEN '40-49.99' WHEN o.ai_confidence<60 THEN '50-59.99'
        WHEN o.ai_confidence<70 THEN '60-69.99' WHEN o.ai_confidence<80 THEN '70-79.99'
        ELSE '80-100' END ai_band,COUNT(*) completed,
        COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE) correct_24h,
        ROUND(100.0*COUNT(*) FILTER(WHERE x.direction_correct_24h IS TRUE)/NULLIF(COUNT(*),0),2) correct_24h_pct,
        AVG(o.final_confidence) avg_final_confidence,AVG(x.return_24h_pct) avg_return_24h_pct
        {base} AND LOWER(COALESCE(o.ai_analysis->>'available',''))='true' AND o.ai_confidence IS NOT NULL
        GROUP BY 1 ORDER BY MIN(o.ai_confidence)"""))

        emit("EARLY_BEHAVIOUR",one(cur,f"""SELECT
        COUNT(*) FILTER(WHERE x.early_continuation IS TRUE) early_continuation,
        COUNT(*) FILTER(WHERE x.early_reversal IS TRUE) early_reversal,
        AVG(x.immediate_move_pct) avg_immediate_move_pct,AVG(x.early_momentum_pct) avg_early_momentum_pct {base}"""))

        emit("VERSIONS",rows(cur,f"""SELECT o.model_version,o.strategy_version,o.memory_schema_version,
        COUNT(*) completed {base} GROUP BY o.model_version,o.strategy_version,o.memory_schema_version
        ORDER BY COUNT(*) DESC"""))

        conn.rollback()
        print("STAGE 8 PERFORMANCE V2: COMPLETE (descriptive historical evidence only; no writes; no sends; no trades)",flush=True)
    finally:
        conn.close()

if __name__=="__main__": main()
