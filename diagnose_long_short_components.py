import os, math
from collections import defaultdict
from statistics import mean, median
import psycopg2

MODEL_VERSION="SIGNALS2_AI_INTEGRATED_V1"
LOOKBACK_HOURS=24
THRESHOLD=65.0

def num(v):
    try:
        v=float(v)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):
        return None

def summary(vs):
    x=[v for v in vs if v is not None]
    return (len(x), mean(x) if x else None, median(x) if x else None)

def f(v):
    return "N/A" if v is None else f"{v:.2f}"

def main():
    url=os.getenv("SIGNALS2_DATABASE_URL")
    if not url:
        raise RuntimeError("SIGNALS2_DATABASE_URL is not configured")
    print("="*84)
    print("LONG vs SHORT COMPONENT DIAGNOSTIC — READ ONLY")
    print("NO WRITES | NO TELEGRAM | NO TRADES | NO PRODUCTION CHANGES")
    print("="*84)
    conn=psycopg2.connect(url)
    try:
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol,direction,final_confidence,technical_confidence,
                       market_confidence,memory_confidence,ai_confidence,ai_analysis
                FROM signals2_opportunities
                WHERE created_at >= NOW()-(%s*INTERVAL '1 hour')
                  AND model_version=%s
                  AND direction IN ('LONG','SHORT')
                  AND symbol NOT LIKE 'SIGNALS2%%'
                ORDER BY created_at,symbol,direction
            """,(LOOKBACK_HOURS,MODEL_VERSION))
            rows=cur.fetchall()
        print(f"ROWS READ: {len(rows)}")
        d={"LONG":defaultdict(list),"SHORT":defaultdict(list)}
        genuine={"LONG":0,"SHORT":0}
        above={"LONG":0,"SHORT":0}
        for symbol,direction,final,tech,market,memory,ai,ai_analysis in rows:
            direction=str(direction).upper()
            if direction not in d: continue
            vals={"final":num(final),"technical":num(tech),"market":num(market),
                  "memory":num(memory),"ai":num(ai)}
            for k,v in vals.items(): d[direction][k].append(v)
            if vals["final"] is not None and vals["final"]>=THRESHOLD: above[direction]+=1
            a=ai_analysis if isinstance(ai_analysis,dict) else {}
            if vals["ai"] is not None and a.get("available") is True and num(a.get("ai_score")) is not None:
                genuine[direction]+=1
        print("\nCOMPONENT COMPARISON")
        for key,label in [("technical","TECHNICAL"),("market","MARKET"),("memory","MEMORY"),
                          ("final","FINAL STORED"),("ai","AI WHEN PRESENT")]:
            ln,lm,lmed=summary(d["LONG"][key]); sn,sm,smed=summary(d["SHORT"][key])
            delta=(lm-sm) if lm is not None and sm is not None else None
            print(f"{label:<18} LONG mean={f(lm):>6} med={f(lmed):>6} n={ln:<5} | "
                  f"SHORT mean={f(sm):>6} med={f(smed):>6} n={sn:<5} | delta={f(delta)}")
        print("\nCOUNTS")
        print(f"LONG rows: {len(d['LONG']['final'])} | SHORT rows: {len(d['SHORT']['final'])}")
        print(f"Stored final >=65: LONG={above['LONG']} SHORT={above['SHORT']}")
        print(f"Genuine AI rows:   LONG={genuine['LONG']} SHORT={genuine['SHORT']}")
        print("\nNOTE: stored final_confidence may be POST-AI for genuine AI rows; it is not always pre_ai_confidence.")
        print("DIAGNOSTIC COMPLETE")
    finally:
        try: conn.rollback()
        except Exception: pass
        conn.close()

if __name__=="__main__":
    main()
