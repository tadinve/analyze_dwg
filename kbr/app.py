# app.py
import json
import textwrap
from typing import Dict, Any, List, Optional
import os

import streamlit as st
import pandas as pd
from neo4j import GraphDatabase, basic_auth
from PIL import Image

# ─────────────────────────────────────────────────────────────
# Setup & Secrets
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="DocLabs — Knowledge Graph Q&A", layout="wide")

NEO4J_URI = st.secrets.get("NEO4J_URI")
NEO4J_USER = st.secrets.get("NEO4J_USER")
NEO4J_PASSWORD = st.secrets.get("NEO4J_PASS")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)  # optional for Q6

driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))

# ─────────────────────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────────────────────
def run_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    with driver.session() as session:
        result = session.run(query, params or {})
        data = [r.data() for r in result]
    return data

def safe_md(label: str, val: str) -> str:
    return f"**{label}:** {val}"

def show_summary(md_lines: List[str]):
    st.markdown("\n".join(md_lines))

def is_write_query(q: str) -> bool:
    ql = q.lower()
    forbidden = [" merge ", " create ", " delete ", " detach ", " set ", " remove ", " load csv", " call db.", " apoc.", " yield "]
    return any(tok in ql for tok in forbidden)

# ─────────────────────────────────────────────────────────────
# Q1–Q5 Cypher
# ─────────────────────────────────────────────────────────────

Q1 = """
// Q1: Entitlement evidence bundle for a CO
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:REFERS_TO]->(ref)
WITH co, collect(DISTINCT ref) AS refs

// Any CO chunks that cite evidence (specs/RFIs/etc.)
OPTIONAL MATCH (coChunk:Chunk)
WHERE coChunk.id STARTS WITH co.id + '#'
OPTIONAL MATCH (coChunk)-[:CITES]->(ev:Chunk)
WITH co, refs, collect(DISTINCT ev) AS citedChunks

// Contract clauses (SOW/Exclusions) across any Contract doc
OPTIONAL MATCH (ctDoc:Document)-[:IS_A]->(:DocType)-[:IN_CATEGORY]->(:DocCategory {name:'Contract Documents'})
OPTIONAL MATCH (ctDoc)-[:HAS_CHUNK]->(ctch:Chunk)
WHERE ctch.section IN ['SOW','Exclusions']
WITH co, refs, citedChunks, collect(DISTINCT ctch) AS contractChunks

RETURN
  co.id       AS changeOrder,
  co.title    AS title,
  co.status   AS status,
  [r IN refs WHERE r IS NOT NULL |
     labels(r)[0] + ':' + coalesce(r.id, r.number, r.title, '')]              AS referencedArtifacts,
  [e IN citedChunks WHERE e IS NOT NULL |
     { id:e.id, section:e.section, text:substring(e.text,0,160)+'...' }]       AS citedEvidence,
  [e IN contractChunks WHERE e IS NOT NULL |
     { id:e.id, section:e.section, text:substring(e.text,0,160)+'...' }]       AS contractClauses
LIMIT 1;
"""

# Q2 without APOC (portable)
Q2 = """
// Q2: Precedent COs similar to this CO (shared artifacts / WBS / systems)
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:REFERS_TO]->(art)
WITH co, collect(DISTINCT coalesce(art.id, art.number, art.title)) AS artIds

OPTIONAL MATCH (co)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(wbs:WBS)
WITH co, artIds, collect(DISTINCT wbs.code) AS wbsCodes

OPTIONAL MATCH (co)-[:MODIFIES]->(sys:System)
WITH co, artIds, wbsCodes, collect(DISTINCT sys.id) AS systems

MATCH (other:ChangeOrder) WHERE other.id <> co.id

OPTIONAL MATCH (other)-[:REFERS_TO]->(a)
WITH co, other, artIds, wbsCodes, systems,
     collect(DISTINCT coalesce(a.id, a.number, a.title)) AS oArtIds

OPTIONAL MATCH (other)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(ow:WBS)
WITH co, other, artIds, wbsCodes, systems, oArtIds,
     collect(DISTINCT ow.code) AS oWbs

OPTIONAL MATCH (other)-[:MODIFIES]->(os:System)
WITH co, other, artIds, wbsCodes, systems, oArtIds, oWbs,
     collect(DISTINCT os.id) AS oSys

WITH co, other,
     [x IN oArtIds WHERE x IS NOT NULL AND x IN artIds] AS sharedArtIds,
     [x IN oWbs    WHERE x IS NOT NULL AND x IN wbsCodes] AS sharedWbs,
     [x IN oSys    WHERE x IS NOT NULL AND x IN systems] AS sharedSys

WHERE size(sharedArtIds) > 0 OR size(sharedWbs) > 0 OR size(sharedSys) > 0

OPTIONAL MATCH (other)-[:REFERS_TO]->(ra)
WHERE coalesce(ra.id, ra.number, ra.title) IN sharedArtIds
WITH co, other, sharedWbs, sharedSys,
     collect(DISTINCT labels(ra)[0] + ':' + coalesce(ra.id, ra.number, ra.title,'')) AS matchedArtifacts

RETURN
  co.id          AS targetCO,
  other.id       AS similarCO,
  other.title    AS title,
  other.status   AS status,
  sharedWbs      AS matchedWBS,
  matchedArtifacts AS matchedArtifacts,
  sharedSys      AS matchedSystems
ORDER BY other.id
LIMIT 10;
"""

Q3 = """
// Q3: Impact summary – what this CO touches
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:MODIFIES]->(sys:System)
OPTIONAL MATCH (co)-[:AFFECTS]->(wa:WorkArea)
OPTIONAL MATCH (co)-[:IMPACTS]->(sch:Schedule)
RETURN
  co.id AS changeOrder,
  co.title AS title,
  co.status AS status,
  collect(DISTINCT sys.id) AS systems,
  collect(DISTINCT wa.id)  AS workAreas,
  collect(DISTINCT sch.id) AS schedules
LIMIT 1;
"""

Q4 = """
// Q4: Commercial coverage (Allowance / Contingency / Unit Price)
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:COVERED_BY]->(alCO:Allowance)
OPTIONAL MATCH (ct:Contract)
OPTIONAL MATCH (ct)-[:HAS_ALLOWANCE]->(al:Allowance)
OPTIONAL MATCH (ct)-[:HAS_CONTINGENCY]->(ctg:Contingency)
OPTIONAL MATCH (ct)-[:HAS_UNIT_PRICE]->(upi:UnitPriceItem)
WITH co,
     [x IN collect(DISTINCT alCO) WHERE x IS NOT NULL |
        {id:x.id, name:x.name, amount:x.amount, currency:coalesce(x.currency,'USD')}] AS directAllowances,
     [x IN collect(DISTINCT al) WHERE x IS NOT NULL |
        {id:x.id, name:x.name, amount:x.amount, currency:coalesce(x.currency,'USD')}] AS contractAllowances,
     [x IN collect(DISTINCT ctg) WHERE x IS NOT NULL |
        {id:x.id, name:x.name, percent:x.percent}] AS contingencies,
     [x IN collect(DISTINCT upi) WHERE x IS NOT NULL |
        {id:x.id, name:x.name, unit:x.unit, rate:x.rate, currency:coalesce(x.currency,'USD')}] AS unitPrices
RETURN
  co.id    AS changeOrder,
  co.title AS title,
  co.status AS status,
  directAllowances,
  contractAllowances,
  contingencies,
  unitPrices
LIMIT 1;
"""

Q5 = """
// Q5: Latest analysis run with evidence + metrics + recommendation
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:HAS_ANALYSIS]->(ar:AnalysisRun)
WITH co, ar ORDER BY ar.timestamp DESC
WITH co, collect(ar)[0] AS latestAR
OPTIONAL MATCH (latestAR)-[:HAS_METRIC]->(m:Metric)
OPTIONAL MATCH (latestAR)-[:RECOMMENDS]->(rec:Recommendation)
OPTIONAL MATCH (latestAR)-[:USES_EVIDENCE]->(ev:Evidence)
OPTIONAL MATCH (ev)-[:EVIDENCE_FROM]->(ch:Chunk)
WITH co, latestAR, m, rec,
     collect(DISTINCT { id: ev.id,
                        supports: ev.supports,
                        confidence: ev.confidence,
                        reason: ev.reason,
                        chunk: CASE WHEN ch IS NULL THEN NULL ELSE {id:ch.id, section:ch.section, text:substring(ch.text,0,160)+'...'} END }) AS evidence
RETURN
  co.id AS changeOrder,
  co.title AS title,
  co.status AS status,
  CASE WHEN latestAR IS NULL THEN NULL ELSE
    {
      id: latestAR.id,
      at: toString(latestAR.timestamp),
      determination: latestAR.determination,
      confidence: latestAR.confidence_overall,
      metrics: CASE WHEN m IS NULL THEN NULL ELSE
                 {coverage:m.coverage, clarity:m.clarity, consistency:m.consistency, precedent:m.precedentScore}
               END,
      recommendation: CASE WHEN rec IS NULL THEN NULL ELSE
                 {action:rec.action, reason:rec.reason}
               END,
      evidence: evidence
    }
  END AS analysis
LIMIT 1;
"""

# ─────────────────────────────────────────────────────────────
# Q6: English → Cypher (read-only)
# ─────────────────────────────────────────────────────────────
def robust_q6_fallback(nl: str, co_id: Optional[str]) -> Optional[str]:
    p = (nl or "").lower().strip()
    if ("pending" in p) and ("modular" in p):
        return textwrap.dedent("""
        MATCH (co:ChangeOrder)
        WHERE toLower(co.status) CONTAINS 'pending'
        OPTIONAL MATCH (co)-[:MODIFIES]->(s:System)
        OPTIONAL MATCH (co)-[:REFERS_TO]->(sp:Spec)
        OPTIONAL MATCH (co)-[:HAS_EVIDENCE]->(:Evidence)-[:EVIDENCE_FROM]->(ch:Chunk)
        WITH co,
             collect(DISTINCT toLower(coalesce(s.id,'')))     AS s_ids,
             collect(DISTINCT toLower(coalesce(sp.title,''))) AS sp_titles,
             collect(DISTINCT toLower(coalesce(ch.text,'')))  AS texts
        WHERE any(x IN s_ids WHERE x CONTAINS 'modular')
           OR any(t IN sp_titles WHERE t CONTAINS 'modular')
           OR any(tx IN texts WHERE tx CONTAINS 'modular')
        RETURN co.id AS id, co.title AS title, co.status AS status
        ORDER BY id
        """)
    if ("not entitled" in p) and ("last" in p or "latest" in p):
        return textwrap.dedent("""
        MATCH (ar:AnalysisRun {status:'completed'})
        WITH ar ORDER BY ar.timestamp DESC LIMIT 1
        MATCH (ar)-[:RECOMMENDS]->(rec:Recommendation {determination:'Not Entitled'})
        MATCH (rec)<-[:HAS_RECOMMENDATION]-(co:ChangeOrder)
        RETURN co.id AS id, co.title AS title, rec.determination AS determination, rec.confidence_overall AS confidence
        ORDER BY id
        """)
    if ("rfi" in p) and (("this co" in p) or ("current co" in p) or co_id):
        cid = co_id or ""
        return f"""
        MATCH (co:ChangeOrder {{id:'{cid}'}})-[:REFERS_TO]->(d:Document)-[:IS_A]->(:DocType {{name:'RFIs'}})
        RETURN d.id AS id, coalesce(d.title,'') AS title, coalesce(d.status,'') AS status
        ORDER BY id
        """
    return None

def english_to_cypher(nl: str, co_id: Optional[str]) -> str:
    fallback = robust_q6_fallback(nl, co_id)
    if fallback:
        return fallback
    if not OPENAI_API_KEY:
        return "MATCH (co:ChangeOrder) RETURN co.id AS id, co.title AS title, co.status AS status ORDER BY id LIMIT 25;"
    import openai  # type: ignore
    openai.api_key = OPENAI_API_KEY
    system = """Translate English to READ-ONLY Cypher for Neo4j 5. Never use MERGE/CREATE/DELETE/SET/REMOVE/DETACH/LOAD/APOC.
Return tidy columns with stable names."""
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":system},
                  {"role":"user","content":f"English: {nl}\nCO hint: {co_id or ''}"}],
        temperature=0.1,
    )
    q = resp["choices"][0]["message"]["content"].strip()
    if is_write_query(" " + q + " "):
        return "MATCH (co:ChangeOrder) RETURN co.id AS id, co.title AS title, co.status AS status ORDER BY id LIMIT 25;"
    return q

# ─────────────────────────────────────────────────────────────
# Summaries
# ─────────────────────────────────────────────────────────────
def summarize_q1(rows):
    if not rows:
        return "\n".join([
            safe_md("Heading", "Entitlement (Q1)"),
            safe_md("Status", "No data returned"),
            safe_md("Details", "Check CO id or evidence wiring."),
        ])
    r = rows[0]
    return "\n\n".join([
        safe_md("Heading", "Entitlement (Q1)"),
        safe_md("Change Order", f"{r.get('changeOrder','')} — {r.get('title','')}"),
        safe_md("Status", r.get("status","")),
        safe_md("Referenced", ", ".join(r.get("referencedArtifacts",[])) or "—"),
        safe_md("Cited Evidence", f"{len(r.get('citedEvidence',[]))} items"),
        safe_md("Contract Clauses", f"{len(r.get('contractClauses',[]))} items"),
    ])

def summarize_q2(rows):
    if not rows:
        return "\n".join([
            safe_md("Heading", "Precedent (Q2)"),
            safe_md("Result", "No similar change orders found."),
            safe_md("Details", "Try broader matches (WBS/Systems/Artifacts)."),
        ])
    items = []
    for r in rows:
        parts = [r.get("similarCO","")]
        if r.get("title"): parts.append(r["title"])
        if r.get("status"): parts.append(f"[{r['status']}]")
        if r.get("matchedWBS"): parts.append("WBS:" + ",".join(r["matchedWBS"]))
        if r.get("matchedSystems"): parts.append("SYS:" + ",".join(r["matchedSystems"]))
        if r.get("matchedArtifacts"): parts.append("ART:" + ",".join(r["matchedArtifacts"]))
        items.append("• " + " ".join(parts))
    return "\n\n".join([
        safe_md("Heading", "Precedent (Q2)"),
        safe_md("Count", str(len(rows))),
        safe_md("Details", "\n" + "\n".join(items)),
    ])

def summarize_q3(rows):
    if not rows:
        return "\n".join([
            safe_md("Heading", "Impact Summary (Q3)"),
            safe_md("Result", "No systems/work areas/schedules linked."),
        ])
    r = rows[0]
    return "\n\n".join([
        safe_md("Heading", "Impact Summary (Q3)"),
        safe_md("Change Order", f"{r.get('changeOrder','')} — {r.get('title','')}"),
        safe_md("Status", r.get("status","")),
        safe_md("Systems", ", ".join(r.get("systems",[])) or "—"),
        safe_md("Work Areas", ", ".join(r.get("workAreas",[])) or "—"),
        safe_md("Schedules", ", ".join(r.get("schedules",[])) or "—"),
    ])

def summarize_q4(rows):
    if not rows:
        return "\n".join([
            "**Heading:** Cost Coverage (Q4)",
            "**Result:** No coverage found.",
            "**Details:** No Allowance/Contingency/Unit Price matched."
        ])
    r = rows[0]
    lines = ["**Heading:** Cost Coverage (Q4)"]
    lines.append(f"**Change Order:** {r.get('changeOrder','')} — {r.get('title','')}")
    da = r.get("directAllowances",[])
    ca = r.get("contractAllowances",[])
    cg = r.get("contingencies",[])
    up = r.get("unitPrices",[])
    def fmt_allow(a): return f"{a.get('id','')} ({a.get('name','')}): {a.get('amount','')} {a.get('currency','')}"
    def fmt_contg(c): return f"{c.get('id','')} ({c.get('name','')}): {c.get('percent','')}%"
    def fmt_upi(u):  return f"{u.get('id','')} ({u.get('name','')}): {u.get('rate','')}/{u.get('unit','')} {u.get('currency','')}"
    lines.append("**Direct Allowances:** " + ("\n" + "\n".join("• " + fmt_allow(a) for a in da) if da else "—"))
    lines.append("**Contract Allowances:** " + ("\n" + "\n".join("• " + fmt_allow(a) for a in ca) if ca else "—"))
    lines.append("**Contingency:** " + ("\n" + "\n".join("• " + fmt_contg(c) for c in cg) if cg else "—"))
    lines.append("**Unit Prices:** " + ("\n" + "\n".join("• " + fmt_upi(u) for u in up) if up else "—"))
    return "\n\n".join(lines)

def summarize_q5(rows):
    if not rows:
        return "\n".join([
            "**Heading:** Latest AI Analysis (Q5)",
            "**Result:** No analysis found."
        ])
    r = rows[0]
    if isinstance(r.get("analysis"), dict):
        a = r["analysis"]
        lines = [
            "**Heading:** Latest AI Analysis (Q5)",
            f"**Change Order:** {r.get('changeOrder','')} — {r.get('title','')}",
            f"**Determination:** {a.get('determination','—')}",
            f"**Confidence:** {a.get('confidence','—')}",
            f"**Analyzed At:** {a.get('at','—')}",
        ]
        m = a.get("metrics") or {}
        if m:
            lines.append(f"**Metrics:** coverage {m.get('coverage','—')}, clarity {m.get('clarity','—')}, consistency {m.get('consistency','—')}, precedent {m.get('precedent','—')}")
        rec = a.get("recommendation") or {}
        if rec:
            lines.append(f"**Recommendation:** {rec.get('action','—')}")
            if rec.get("reason"): lines.append(f"**Reason:** {rec['reason']}")
        ev = a.get("evidence") or []
        lines.append(f"**Evidence Items:** {len(ev)}")
        return "\n".join(lines)
    det = r.get("determination","—")
    conf = r.get("confidence","—")
    at   = r.get("analyzedAt","—")
    evc  = r.get("evidenceCount",0)
    return "\n\n".join([
        "**Heading:** Latest AI Analysis (Q5)",
        f"**Change Order:** {r.get('changeOrder','')} — {r.get('title','')}",
        f"**Determination:** {det}",
        f"**Confidence:** {conf}",
        f"**Evidence Items:** {evc}",
        f"**Analyzed At:** {at}"
    ])

def summarize_q6(nl: str, rows: List[Dict[str,Any]]) -> str:
    n = len(rows)
    if n == 0:
        return "\n".join([
            safe_md("Heading", "Generic (Q6)"),
            safe_md("Question", nl),
            safe_md("Result Count", "0"),
            safe_md("Details", "No records found."),
        ])
    details = []
    for i, r in enumerate(rows, 1):
        items = [f"{k}: {v}" for k, v in r.items()]
        details.append(f"{i}. " + ", ".join(items))
    return "\n".join([
        safe_md("Heading", "Generic (Q6)"),
        safe_md("Question", nl),
        safe_md("Result Count", str(n)),
        safe_md("Details", "\n" + "\n".join(details)),
    ])

# ─────────────────────────────────────────────────────────────
# Document Library helpers
# ─────────────────────────────────────────────────────────────
def q_docs_by_category():
    return run_query("""
    MATCH (c:DocCategory)
    RETURN
      c.name AS Category,
      count { (:DocType)-[:IN_CATEGORY]->(c) }  AS DocTypes,
      count { (:Document)-[:IN_CATEGORY]->(c) } AS Documents
    ORDER BY Category
    """)

def q_docs_by_type():
    return run_query("""
    MATCH (t:DocType)-[:IN_CATEGORY]->(c:DocCategory)
    RETURN
      c.name AS Category,
      t.name AS Type,
      count { (:Document)-[:IS_A]->(t) } AS Documents
    ORDER BY Category, Type
    """)

def q_doc_list(category=None, dtype=None, search=None, limit=100):
    where = []
    if category:
        safe_cat = category.replace("'", "\\'")
        where.append("c.name = '" + safe_cat + "'")
    if dtype:
        safe_dtype = dtype.replace("'", "\\'")
        where.append("t.name = '" + safe_dtype + "'")
    where_clause = "WHERE " + " AND ".join(where) if where else ""
    text_filter = ""
    if search:
        s = search.lower().replace("'", "\\'")
        text_filter = f" WHERE toLower(d.id) CONTAINS '{s}' OR toLower(coalesce(d.title,'')) CONTAINS '{s}' "
    cypher = f"""
    MATCH (d:Document)-[:IS_A]->(t:DocType)-[:IN_CATEGORY]->(c:DocCategory)
    {where_clause}
    OPTIONAL MATCH (d)-[:HAS_CHUNK]->(ch:Chunk)
    WITH d, t, c, count(ch) AS chunks
    {text_filter}
    RETURN
      d.id   AS id,
      coalesce(d.title,'') AS title,
      coalesce(d.type,'')  AS rawType,
      t.name AS docType,
      c.name AS category,
      coalesce(d.status,'') AS status,
      chunks AS chunks
    ORDER BY category, docType, id
    LIMIT {int(limit)}
    """
    return run_query(cypher)

# ─────────────────────────────────────────────────────────────
# UI — Two tabs
# ─────────────────────────────────────────────────────────────
st.title("DocLabs — Knowledge Graph Q&A")
st.caption("Ask in English, run Cypher on Neo4j, and get evidence-based explanations for Kevin.")

tab_query, tab_docs, tab_kbr, tab_nodes = st.tabs(["🔎 Query KB", "📚 Documents", "📊 KBR", "🧠 Nodes & Relations"])

with tab_query:
    QUERY_CHOICES = {
        "Entitlement (Q1)": Q1,
        "Precedent (Q2)": Q2,
        "Impact Summary (Q3)": Q3,
        "Cost Coverage (Q4)": Q4,
        "Latest AI Analysis (Q5)": Q5,
        "Generic (Q6)": "GENERIC",
    }

    with st.form("query_form"):
        qtype = st.selectbox("Query Type", list(QUERY_CHOICES.keys()), index=0)
        co_id = st.text_input("CO id", value="CO-042")
        kevin_q = st.text_input("Kevin’s question (for Q6)", value="")
        submitted = st.form_submit_button("Run")

    if submitted:
        try:
            if qtype == "Entitlement (Q1)":
                cypher = Q1
                rows = run_query(cypher, {"co_id": co_id})
                st.markdown("## 🗣️ Plain-English Summary")
                show_summary([summarize_q1(rows)])
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write(rows or [])

            elif qtype == "Precedent (Q2)":
                cypher = Q2
                rows = run_query(cypher, {"co_id": co_id})
                st.markdown("## 🗣️ Plain-English Summary")
                show_summary([summarize_q2(rows)])
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write(rows or [])

            elif qtype == "Impact Summary (Q3)":
                cypher = Q3
                rows = run_query(cypher, {"co_id": co_id})
                st.markdown("## 🗣️ Plain-English Summary")
                show_summary([summarize_q3(rows)])
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write(rows or [])

            elif qtype == "Cost Coverage (Q4)":
                cypher = Q4
                rows = run_query(cypher, {"co_id": co_id})
                st.markdown("## 🗣️ Plain-English Summary")
                st.markdown(summarize_q4(rows))
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write(rows or [])

            elif qtype == "Latest AI Analysis (Q5)":
                cypher = Q5
                rows = run_query(cypher, {"co_id": co_id})
                st.markdown("## 🗣️ Plain-English Summary")
                st.markdown(summarize_q5(rows))
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write(rows or [])

            else:  # Generic (Q6)
                cypher = english_to_cypher(kevin_q or "", co_id)
                rows = run_query(cypher)
                st.markdown("## 🗣️ Plain-English Summary")
                st.markdown(summarize_q6(kevin_q or "", rows))
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write(rows or [])

        except Exception as e:
            st.error(f"Query failed: {e}")

with tab_docs:
    st.subheader("Document Library")
    cols = st.columns(2)
    with cols[0]:
        try:
            cats = q_docs_by_category()
            st.metric("Categories", len(cats) if cats else 0)
        except Exception as e:
            cats = []
            st.caption(f"Counts by category unavailable: {e}")

    with cols[1]:
        try:
            types = q_docs_by_type()
            uniq_types = len({(r["Category"], r["Type"]) for r in types}) if types else 0
            st.metric("Doc Types", uniq_types)
        except Exception as e:
            types = []
            st.caption(f"Counts by type unavailable: {e}")

    with st.expander("Counts by Category & Type", expanded=False):
        if cats:
            st.markdown("**By Category**")
            st.dataframe(pd.DataFrame(cats))
        if types:
            st.markdown("**By Type**")
            st.dataframe(pd.DataFrame(types))

    st.markdown("### Browse")
    lcol, rcol = st.columns([2, 3])

    with lcol:
        cat_options = ["(any)"] + (sorted({r["Category"] for r in types}) if types else [])
        category = st.selectbox("Category", cat_options, index=0)
        if category != "(any)":
            type_options = ["(any)"] + [r["Type"] for r in types if r["Category"] == category]
        else:
            type_options = ["(any)"] + (sorted({r["Type"] for r in types}) if types else [])
        dtype = st.selectbox("Doc Type", type_options, index=0)
        search = st.text_input("Search (id/title contains)", value="")
        limit = st.number_input("Limit", min_value=10, max_value=500, value=100, step=10)
        browse = st.button("🔎 List documents")

    with rcol:
        if browse:
            cat_arg = None if category == "(any)" else category
            type_arg = None if dtype == "(any)" else dtype
            try:
                rows = q_doc_list(category=cat_arg, dtype=type_arg, search=search.strip() or None, limit=int(limit))
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
                else:
                    st.info("No documents matched your filters.")
            except Exception as e:
                st.error(f"Browse failed: {e}")

    with st.expander("Orphans (debug)"):
        try:
            orphans = run_query("""
            MATCH (c:DocCategory)
            WHERE NOT EXISTS { MATCH (:DocType)-[:IN_CATEGORY]->(c) }
              AND NOT EXISTS { MATCH (:Document)-[:IN_CATEGORY]->(c) }
            RETURN 'Orphan Category' AS kind, c.name AS name
            UNION ALL
            MATCH (t:DocType)
            WHERE NOT EXISTS { MATCH (t)-[:IN_CATEGORY]->(:DocCategory) }
            RETURN 'Orphan DocType' AS kind, t.name AS name
            """)
            if orphans:
                st.dataframe(pd.DataFrame(orphans))
            else:
                st.caption("No orphan categories or doctypes 🎉")
        except Exception as e:
            st.caption(f"Orphan check unavailable: {e}")

with tab_kbr:
    st.subheader("Knowledge Base Reference (KBR)")
    
    # Check if kbr.png exists
    img_path = os.path.join(os.path.dirname(__file__), "kbr.png")
    
    if os.path.exists(img_path):
        try:
            img = Image.open(img_path)
            st.image(img, use_container_width=True, caption="Knowledge Base Reference Diagram")
        except Exception as e:
            st.error(f"Could not load image: {e}")
    else:
        st.warning(f"Image not found at {img_path}")

with tab_nodes:
    st.subheader("🧠 Knowledge Graph Nodes & Relations")
    
    # Check if nodes.md exists
    md_path = os.path.join(os.path.dirname(__file__), "nodes.md")
    
    if os.path.exists(md_path):
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            st.markdown(md_content)
        except Exception as e:
            st.error(f"Could not load markdown file: {e}")
    else:
        st.warning(f"Markdown file not found at {md_path}")
