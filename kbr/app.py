import os
import json
import streamlit as st
from neo4j import GraphDatabase

# --- OpenAI for Q6 ---
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

st.set_page_config(page_title="DocLabs — Knowledge Graph Q&A", layout="centered")

# ===============================
# Secrets / config helpers
# ===============================
def _get(key, *alt_keys, default=None):
    if isinstance(st.secrets, dict):
        for k in (key,) + alt_keys:
            if k in st.secrets:
                return st.secrets[k]
    for k in (key,) + alt_keys:
        v = os.getenv(k)
        if v:
            return v
    return default

# Aura creds (compatible with older names too)
NEO4J_URI = _get("NEO4J_URI", "AURA_URI", "NEO4J_URL", default="neo4j+s://PLACEHOLDER.databases.neo4j.io")
NEO4J_USER = _get("NEO4J_USER", "AURA_USER", "NEO4J_USERNAME", default="neo4j")
NEO4J_PASSWORD = _get("NEO4J_PASSWORD", "AURA_PASSWORD", "NEO4J_PASS", default="PLACEHOLDER")

if "PLACEHOLDER" in NEO4J_URI or "PLACEHOLDER" in NEO4J_PASSWORD:
    st.error("Neo4j credentials are missing or using placeholders. Check `.streamlit/secrets.toml`.")
    st.stop()

masked_uri = NEO4J_URI.replace("neo4j+s://", "neo4j+s://•••.")
st.sidebar.caption(f"DB: {masked_uri}")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
try:
    with driver.session() as s:
        s.run("RETURN 1 AS ok").single()
    st.sidebar.success("Neo4j connected")
except Exception as e:
    st.sidebar.error(f"Neo4j connection failed: {e}")
    st.stop()

# ===============================
# Cypher templates (Q1–Q5)
# ===============================
Q1 = """
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:REFERS_TO]->(art)
WITH co, collect(DISTINCT art) AS artifacts
OPTIONAL MATCH (co)-[:HAS_EVIDENCE]->(ev:Evidence)
OPTIONAL MATCH (ev)-[:EVIDENCE_FROM]->(evch:Chunk)
WITH co, artifacts,
     collect(DISTINCT {id:ev.id, supports:ev.supports, confidence:ev.confidence, reason:ev.reason}) AS evidence,
     collect(DISTINCT {id:evch.id, section:evch.section, text:substring(evch.text,0,140)+'...'}) AS evidenceChunks
OPTIONAL MATCH (ctDoc:Document {type:'Contract'})-[:HAS_CHUNK]->(ctch:Chunk)
WHERE ctch.section IN ['SOW','Exclusions']
WITH co, artifacts, evidence, evidenceChunks,
     collect(DISTINCT {id:ctch.id, section:ctch.section, text:substring(ctch.text,0,140)+'...'}) AS contractClauses
OPTIONAL MATCH (co)-[:REFERS_TO]->(db:DesignBasis)
OPTIONAL MATCH (db)-[:HAS_DOCUMENT]->(dbdoc:Document)-[:HAS_CHUNK]->(dbch:Chunk)
WITH co, artifacts, evidence, evidenceChunks, contractClauses,
     collect(DISTINCT {id:dbch.id, section:coalesce(dbch.section,'(n/a)'), text:substring(dbch.text,0,140)+'...'}) AS designBasisClauses
OPTIONAL MATCH (co)-[:AFFECTS]->(wa:WorkArea)
OPTIONAL MATCH (co)-[:MODIFIES]->(sys:System)
WITH co, artifacts, evidence, evidenceChunks, contractClauses, designBasisClauses,
     collect(DISTINCT wa.name) AS workAreas,
     collect(DISTINCT sys.name) AS systems
OPTIONAL MATCH (co)-[:COVERED_BY]->(al:Allowance)
WITH co, artifacts, evidence, evidenceChunks, contractClauses, designBasisClauses, workAreas, systems,
     collect(DISTINCT {id:al.id, name:al.name, amount:al.amount}) AS allowances
RETURN
  co.id      AS changeOrder,
  co.title   AS title,
  co.status  AS status,
  [a IN artifacts WHERE a IS NOT NULL | labels(a)[0] + ':' + coalesce(a.id,a.number)] AS referencedArtifacts,
  contractClauses,
  designBasisClauses,
  evidence,
  evidenceChunks,
  workAreas,
  systems,
  allowances
LIMIT 1
"""

Q2 = """
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:REFERS_TO]->(a0)
OPTIONAL MATCH (co)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(w0:WBS)
OPTIONAL MATCH (co)-[:MODIFIES]->(s0:System)
OPTIONAL MATCH (co)-[:AFFECTS]->(wa0:WorkArea)
WITH co,
     collect(DISTINCT a0) AS arts0,
     collect(DISTINCT w0.code) AS wbs0,
     collect(DISTINCT s0.id) AS sys0,
     collect(DISTINCT wa0.id) AS wa0

MATCH (other:ChangeOrder)
WHERE other.id <> co.id
OPTIONAL MATCH (other)-[:REFERS_TO]->(a1)
OPTIONAL MATCH (other)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(w1:WBS)
OPTIONAL MATCH (other)-[:MODIFIES]->(s1:System)
OPTIONAL MATCH (other)-[:AFFECTS]->(wa1:WorkArea)
WITH co, other,
     collect(DISTINCT a1) AS arts1,
     collect(DISTINCT w1.code) AS wbs1,
     collect(DISTINCT s1.id) AS sys1,
     collect(DISTINCT wa1.id) AS wa1,
     arts0, wbs0, sys0, wa0

WITH co, other,
     [x IN arts1 WHERE x IN arts0] AS artMatch,
     [x IN wbs1 WHERE x IN wbs0] AS wbsMatch,
     [x IN sys1 WHERE x IN sys0] AS sysMatch,
     [x IN wa1 WHERE x IN wa0] AS areaMatch

WHERE coalesce(size(artMatch),0) > 0
   OR coalesce(size(wbsMatch),0) > 0
   OR coalesce(size(sysMatch),0) > 0
   OR coalesce(size(areaMatch),0) > 0

RETURN
  co.id       AS targetCO,
  other.id    AS similarCO,
  other.title AS title,
  other.status AS status,
  CASE WHEN size(artMatch) > 0 THEN artMatch ELSE [] END AS matchedArtifacts,
  CASE WHEN size(wbsMatch) > 0 THEN wbsMatch ELSE [] END AS matchedWBS,
  CASE WHEN size(sysMatch) > 0 THEN sysMatch ELSE [] END AS matchedSystems,
  CASE WHEN size(areaMatch) > 0 THEN areaMatch ELSE [] END AS matchedWorkAreas
ORDER BY other.status
LIMIT 10
"""

Q3 = """
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:HAS_COST_ITEM]->(ci:CostItem)-[:CODED_AS]->(wbs:WBS)
WITH co,
     sum(coalesce(ci.amount,0)) AS totalCost,
     collect(DISTINCT {type:ci.type, code:ci.code, amount:ci.amount, wbs:coalesce(wbs.name,wbs.code)}) AS costs
OPTIONAL MATCH (co)-[:IMPACTS]->(act:Activity)-[:BELONGS_TO]->(sch:Schedule)
WITH co, totalCost, costs,
     collect(DISTINCT {activity:act.name, duration:act.durationDays, critical:act.isCritical, schedule:sch.version}) AS scheduleImpact
OPTIONAL MATCH (co)-[:REQUESTED_BY]->(req:Person)
OPTIONAL MATCH (co)-[:PARTY_TO]->(ven:Vendor)
WITH co, totalCost, costs, scheduleImpact,
     coalesce(req.name,'(unknown)') AS requestedBy,
     coalesce(ven.name,'(unspecified)') AS vendorName
OPTIONAL MATCH (co)-[:AFFECTS]->(wa:WorkArea)
OPTIONAL MATCH (co)-[:MODIFIES]->(sys:System)
WITH co, totalCost, costs, scheduleImpact, requestedBy, vendorName,
     collect(DISTINCT wa.name) AS workAreas,
     collect(DISTINCT sys.name) AS systems
OPTIONAL MATCH (ct:Contract)-[:HAS_ALLOWANCE]->(al:Allowance)
OPTIONAL MATCH (ct)-[:HAS_CONTINGENCY]->(ctg:Contingency)
OPTIONAL MATCH (ct)-[:HAS_UNIT_PRICE]->(upi:UnitPriceItem)
OPTIONAL MATCH (co)-[:COVERED_BY]->(al2:Allowance)
WITH co, totalCost, costs, scheduleImpact, requestedBy, vendorName, workAreas, systems,
     collect(DISTINCT {id:al.id, name:al.name, amount:al.amount}) AS contractAllowances,
     collect(DISTINCT {id:ctg.id, name:ctg.name, percent:ctg.percent}) AS contingencies,
     collect(DISTINCT {id:upi.id, name:upi.name, unit:upi.unit, rate:upi.rate}) AS unitPrices,
     collect(DISTINCT {id:al2.id, name:al2.name, amount:al2.amount}) AS coAllowances
OPTIONAL MATCH (co)-[:HAS_ANALYSIS]->(ar:AnalysisRun)
WITH co, totalCost, costs, scheduleImpact, requestedBy, vendorName, workAreas, systems,
     contractAllowances, contingencies, unitPrices, coAllowances,
     ar
ORDER BY ar.timestamp DESC
WITH co, totalCost, costs, scheduleImpact, requestedBy, vendorName, workAreas, systems,
     contractAllowances, contingencies, unitPrices, coAllowances,
     collect(ar)[0] AS latestAR
OPTIONAL MATCH (latestAR)-[:HAS_METRIC]->(m:Metric)
OPTIONAL MATCH (latestAR)-[:RECOMMENDS]->(rec:Recommendation)
WITH co, totalCost, costs, scheduleImpact, requestedBy, vendorName, workAreas, systems,
     contractAllowances, contingencies, unitPrices, coAllowances,
     latestAR, m, rec
RETURN
  co.id AS changeOrder,
  co.title AS title,
  co.status AS status,
  requestedBy,
  vendorName,
  workAreas,
  systems,
  totalCost,
  costs,
  scheduleImpact,
  contractAllowances,
  coAllowances,
  contingencies,
  unitPrices,
  CASE WHEN latestAR IS NULL THEN NULL ELSE
    { id: latestAR.id,
      at: toString(latestAR.timestamp),
      determination: latestAR.determination,
      confidence: latestAR.confidence_overall,
      metrics: CASE WHEN m IS NULL THEN NULL ELSE
                  {coverage:m.coverage, clarity:m.clarity, consistency:m.consistency, precedent:m.precedentScore}
                END,
      recommendation: CASE WHEN rec IS NULL THEN NULL ELSE
                  {action:rec.action, reason:rec.reason}
                END
    }
  END AS analysis
LIMIT 1
"""

Q4 = """
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:COVERED_BY]->(alCO:Allowance)
OPTIONAL MATCH (ct:Contract)
OPTIONAL MATCH (ct)-[:HAS_ALLOWANCE]->(al:Allowance)
OPTIONAL MATCH (ct)-[:HAS_CONTINGENCY]->(ctg:Contingency)
OPTIONAL MATCH (ct)-[:HAS_UNIT_PRICE]->(upi:UnitPriceItem)
RETURN
  co.id AS changeOrder,
  co.title AS title,
  co.status AS status,
  collect(DISTINCT {id:alCO.id, name:alCO.name, amount:alCO.amount}) AS directAllowances,
  collect(DISTINCT {id:al.id, name:al.name, amount:al.amount}) AS contractAllowances,
  collect(DISTINCT {id:ctg.id, name:ctg.name, percent:ctg.percent}) AS contingencies,
  collect(DISTINCT {id:upi.id, name:upi.name, unit:upi.unit, rate:upi.rate}) AS unitPrices
LIMIT 1
"""

Q5 = """
MATCH (co:ChangeOrder {id:$co_id})
OPTIONAL MATCH (co)-[:HAS_ANALYSIS]->(ar:AnalysisRun)
WITH co, ar ORDER BY ar.timestamp DESC
WITH co, head(collect(ar)) AS latestAR
OPTIONAL MATCH (latestAR)-[:HAS_METRIC]->(m:Metric)
WITH co, latestAR, head(collect(m)) AS metric
OPTIONAL MATCH (latestAR)-[:RECOMMENDS]->(rec:Recommendation)
WITH co, latestAR, metric, head(collect(rec)) AS recommendation
OPTIONAL MATCH (latestAR)-[:USES_EVIDENCE]->(ev:Evidence)
OPTIONAL MATCH (ev)-[:EVIDENCE_FROM]->(ch:Chunk)
WITH co, latestAR, metric, recommendation,
     collect(DISTINCT {
       id: ev.id, supports: ev.supports, confidence: ev.confidence, reason: ev.reason,
       chunk: CASE WHEN ch IS NULL THEN NULL ELSE {id:ch.id, section:ch.section, text:substring(ch.text,0,160)+'...'} END
     }) AS evidence
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
      metrics: CASE WHEN metric IS NULL THEN NULL ELSE
                 {coverage:metric.coverage, clarity:metric.clarity, consistency:metric.consistency, precedent:metric.precedentScore}
               END,
      recommendation: CASE WHEN recommendation IS NULL THEN NULL ELSE
                 {action:recommendation.action, reason:recommendation.reason}
               END,
      evidence: evidence
    }
  END AS analysis
LIMIT 1
"""

# ===============================
# Query runner
# ===============================
def run_query(query, params=None):
    with driver.session() as s:
        res = s.run(query, params or {})
        return [r.data() for r in res]

# ===============================
# Summaries (Q1–Q6)
# ===============================
def summarize_q1(rows):
    if not rows:
        return "No entitlement evidence found."
    d = rows[0]
    title = d.get("title", "(untitled)")
    status = d.get("status", "(unknown)")
    systems = ", ".join(d.get("systems") or ["unspecified systems"])
    areas = ", ".join(d.get("workAreas") or ["unspecified areas"])
    n_contract = len(d.get("contractClauses") or [])
    n_db = len(d.get("designBasisClauses") or [])
    al = d.get("allowances") or []
    al_txt = f"{al[0]['name']} (₹{al[0]['amount']})" if al and al[0].get("name") else "None"
    evid = d.get("evidence") or []
    avg_conf = round(sum([e.get("confidence") or 0 for e in evid]) / len(evid), 2) if evid else "N/A"
    return (
        f"**Change Order:** {d['changeOrder']} – {title}\n"
        f"**Status:** {status}\n"
        f"**Systems Affected:** {systems}\n"
        f"**Work Areas:** {areas}\n"
        f"**Contract Clauses Referenced:** {n_contract}\n"
        f"**Design Basis References:** {n_db}\n"
        f"**Average Evidence Confidence:** {avg_conf}\n"
        f"**Allowance Coverage:** {al_txt}"
    )

def summarize_q2(rows):
    if not rows:
        return (
            "**Query Type:** Precedent Change Orders\n"
            "**Description:** Looks for COs sharing artifacts, WBS, systems, or work areas.\n"
            "**Results:** None found."
        )
    lines = []
    for r in rows:
        matches = []
        if r.get("matchedArtifacts"): matches.append("artifacts")
        if r.get("matchedWBS"):       matches.append("WBS codes")
        if r.get("matchedSystems"):   matches.append("systems")
        if r.get("matchedWorkAreas"): matches.append("work areas")
        match_list = ", ".join(matches) or "no overlap"
        lines.append(f"- {r['similarCO']} ({r.get('status','')}) → {match_list}")
    formatted = "\n".join(lines)
    return (
        f"**Query Type:** Precedent Change Orders\n"
        f"**Description:** Looks for COs sharing artifacts, WBS, systems, or work areas.\n"
        f"**Results:**\n{formatted}"
    )

def summarize_q3(rows):
    if not rows:
        return "No executive summary available."
    d = rows[0]
    title = d.get("title", "(untitled)")
    areas = ", ".join(d.get("workAreas") or ["unspecified areas"])
    systems = ", ".join(d.get("systems") or ["unspecified systems"])
    total = d.get("totalCost") or 0
    ar = d.get("analysis") or {}
    det = ar.get("determination", "Unknown")
    conf = ar.get("confidence", "N/A")
    rec = ar.get("recommendation") or {}
    return (
        f"**Change Order:** {d['changeOrder']} – {title}\n"
        f"**Total Estimated Cost:** ₹{total:,.0f}\n"
        f"**Work Areas:** {areas}\n"
        f"**Systems:** {systems}\n"
        f"**AI Determination:** {det} (confidence {conf})\n"
        f"**Recommendation:** {rec.get('action','—')}\n"
        f"{rec.get('reason','')}"
    )

def summarize_q4(rows):
    if not rows:
        return "No commercial coverage information found."
    d = rows[0]
    da = d.get("directAllowances") or []
    ca = d.get("contractAllowances") or []
    cg = d.get("contingencies") or []
    up = d.get("unitPrices") or []
    da_txt = f"{da[0]['name']} (₹{da[0]['amount']})" if da and da[0].get("name") else "None"
    ca_txt = f"{len(ca)} contract allowance(s)" if ca else "None"
    cg_txt = f"{cg[0]['name']} ({cg[0]['percent']}%)" if cg else "None"
    up_txt = f"{up[0]['name']} ({up[0]['unit']} @ ₹{up[0]['rate']})" if up else "None"
    return (
        f"**Change Order:** {d['changeOrder']} – {d.get('title','')}\n"
        f"**Direct Allowance:** {da_txt}\n"
        f"**Contract Allowances:** {ca_txt}\n"
        f"**Contingency Coverage:** {cg_txt}\n"
        f"**Unit Price Items:** {up_txt}"
    )

def summarize_q5(rows):
    if not rows:
        return "No analysis run found."
    d = rows[0]
    a = d.get("analysis")
    if not a:
        return "No analysis run recorded yet."
    det = a.get("determination", "Unknown")
    conf = a.get("confidence", "N/A")
    rec = a.get("recommendation") or {}
    action = rec.get("action", "No recommendation")
    reason = rec.get("reason", "")
    n_evid = len(a.get("evidence") or [])
    return (
        f"**Analysis:**\n"
        f"**Entitlement:** {det} (confidence {conf})\n"
        f"**Recommendation:** {action}\n"
        f"{reason}\n"
        f"**Evidence Items Linked:** {n_evid}"
    )

# ===============================
# Q6: NL → Cypher (OpenAI) + robust fallback
# ===============================
def _get_openai_client():
    if not _OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI SDK not installed. Add `openai` package.")
    api_key = _get("OPENAI_API_KEY", "OPENAI_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing in secrets/env.")
    return OpenAI(api_key=api_key)

Q6_SYSTEM_PROMPT = (
    "You are an expert Neo4j Cypher assistant for a construction entitlement knowledge graph.\n"
    "Translate the user's English question into a single Cypher query for Neo4j 5.x.\n"
    "Labels you may use: ChangeOrder, Spec, RFI, Document, Chunk, System, WorkArea, WBS, CostItem, "
    "Allowance, AnalysisRun, Metric, Recommendation, Evidence, Person, Vendor.\n"
    "Relationships: REFERS_TO, HAS_COST_ITEM, CODED_AS, MODIFIES, AFFECTS, COVERED_BY, HAS_EVIDENCE, "
    "EVIDENCE_FROM, HAS_CHUNK, CITES, HAS_ANALYSIS, HAS_METRIC, RECOMMENDS, IMPACTS.\n"
    "Interpret 'pending/open' broadly: statuses matching (?i)^pending.*|^open$|^in review$.\n"
    "When checking existence of a pattern with a predicate, ALWAYS use the Cypher 5 form:\n"
    "  EXISTS { MATCH ... WHERE ... }\n"
    "Do NOT write 'EXISTS((...)) WHERE ...' and do NOT use SQL constructs like SELECT or MAX().\n"
    "To select the latest AnalysisRun per CO:\n"
    "  MATCH (co)-[:HAS_ANALYSIS]->(ar)\n"
    '  WITH co, ar ORDER BY ar.timestamp DESC\n'
    "  WITH co, collect(ar)[0] AS lastAR\n"
    "Return simple aliases like id, title, status. Only output Cypher."
)

def generate_cypher_from_english(prompt: str, co_id_hint: str | None):
    client = _get_openai_client()
    user_msg = prompt
    if ("this" in prompt.lower() or "current" in prompt.lower()) and co_id_hint:
        user_msg += f"\n\n(Current CO id is '{co_id_hint}'. Use it if relevant.)"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": Q6_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.1
    )
    cypher = resp.choices[0].message.content.strip()
    if "```" in cypher:
        cypher = cypher.replace("```cypher", "").replace("```", "").strip()
    return cypher

def robust_q6_fallback(prompt: str, co_id_hint: str | None) -> str:
    p = prompt.lower()
    pending_regex = "(?i)^pending.*|^open$|^in review$"

    # A) Verified: "pending ... modular (wall)"
    if "pending" in p and ("modular" in p or "modular wall" in p or "modular walls" in p):
        return f"""
        MATCH (co:ChangeOrder)
        WHERE co.status =~ '{pending_regex}'
        OPTIONAL MATCH (co)-[:MODIFIES]->(s:System)
        OPTIONAL MATCH (co)-[:REFERS_TO]->(sp:Spec)
        OPTIONAL MATCH (co)-[:HAS_EVIDENCE]->(:Evidence)-[:EVIDENCE_FROM]->(ch:Chunk)
        WITH co,
             collect(DISTINCT toLower(s.id))     AS s_ids,
             collect(DISTINCT toLower(sp.title)) AS sp_titles,
             collect(DISTINCT toLower(ch.text))  AS texts
        WHERE any(x IN s_ids     WHERE x CONTAINS 'modular')
           OR any(t IN sp_titles WHERE t CONTAINS 'modular')
           OR any(tx IN texts    WHERE tx CONTAINS 'modular wall')
        RETURN co.id AS id, co.title AS title, co.status AS status
        ORDER BY id
        """

    # B) “last AI analysis … not entitled”
    if ("last" in p or "most recent" in p) and ("analysis" in p) and ("not entitled" in p or "not-entitled" in p):
        return """
        MATCH (co:ChangeOrder)-[:HAS_ANALYSIS]->(ar:AnalysisRun)
        WITH co, ar
        ORDER BY ar.timestamp DESC
        WITH co, collect(ar)[0] AS lastAR
        WHERE toLower(lastAR.determination) CONTAINS 'not entitled'
        RETURN co.id AS id, co.title AS title, lastAR.determination AS determination,
               lastAR.confidence_overall AS confidence
        ORDER BY confidence DESC, id
        """

    # C) Generic "show something" fallback
    return """
    MATCH (co:ChangeOrder)
    RETURN co.id AS id, co.title AS title, co.status AS status
    ORDER BY co.id LIMIT 10
    """

def run_q6_with_fallback(nl_prompt: str, co_id_hint: str | None):
    """
    Try LLM-generated Cypher. If it returns 0 rows OR raises an error,
    run the robust fallback.
    """
    try:
        gen_cypher = generate_cypher_from_english(nl_prompt, co_id_hint=co_id_hint)
        rows = run_query(gen_cypher)
        if rows:
            return gen_cypher, rows, False
        fb = robust_q6_fallback(nl_prompt, co_id_hint)
        rows_fb = run_query(fb)
        return fb, rows_fb, True
    except Exception:
        fb = robust_q6_fallback(nl_prompt, co_id_hint)
        rows_fb = run_query(fb)
        return fb, rows_fb, True

def summarize_q6(question: str, rows: list):
    if not rows:
        return f"**Question:** {question}\n**Result Count:** 0\n**Details:** No records found."
    lines = []
    for i, r in enumerate(rows[:10], 1):
        id_   = r.get("id") or r.get("changeOrder") or "—"
        title = r.get("title", "")
        status = r.get("status")
        det = r.get("determination"); conf = r.get("confidence")
        tail = ""
        if det is not None or conf is not None:
            bits = []
            if det is not None:  bits.append(f"determination: {det}")
            if conf is not None: bits.append(f"confidence: {conf}")
            tail = f" *({'; '.join(bits)})*"
        elif status:
            tail = f" *({status})*"
        lines.append(f"{i}. **{id_}** — {title}{tail}")
    return f"**Question:** {question}\n\n **Result Count:** {len(rows)}\n**Details:**\n" + "\n".join(lines)

# ===============================
# UI helpers
# ===============================
def display_summary(title: str, summary_text: str):
    st.markdown(f"### 🗣️ {title}")
    st.markdown(summary_text)

QUERY_OPTIONS = {
    "Entitlement (Q1)": (Q1, summarize_q1),
    "Precedent (Q2)": (Q2, summarize_q2),
    "Executive Summary (Q3)": (Q3, summarize_q3),
    "Coverage (Q4)": (Q4, summarize_q4),
    "Analysis & Evidence (Q5)": (Q5, summarize_q5),
    "Generic (Q6)": (None, None),  # handled separately
}

# ===============================
# UI
# ===============================
st.markdown("## DocLabs — Knowledge Graph Q&A")
st.caption("Ask in English, run Cypher on Neo4j, and get an evidence-based explanation for Kevin.")

choice = st.selectbox("Query Type", list(QUERY_OPTIONS.keys()), index=0)
co_id = st.text_input("CO id", "CO-042")
free_text = st.text_area("Kevin’s question (optional free text)", placeholder="e.g., Show me all pending change orders affecting modular wall systems.")

if st.button("Run", type="primary"):
    params = {"co_id": co_id}
    summary_text = ""
    cypher_for_display = ""
    rows = []

    try:
        if choice != "Generic (Q6)":
            query, summarizer = QUERY_OPTIONS[choice]
            rows = run_query(query, params)
            summary_text = summarizer(rows)
            cypher_for_display = query.replace("$co_id", f"'{co_id}'")
        else:
            if not free_text.strip():
                st.warning("Please type a question in plain English first.")
            else:
                cypher_used, rows, used_fallback = run_q6_with_fallback(free_text.strip(), co_id_hint=co_id)
                cypher_for_display = cypher_used
                summary_text = summarize_q6(free_text.strip(), rows)
                if used_fallback and rows:
                    st.info("Returned results using robust fallback logic (model’s first query had zero matches or errored).")
    except Exception as e:
        st.error(f"Query failed: {e}")
        rows = []
        if choice == "Generic (Q6)":
            summary_text = (
                f"**Question:** {free_text.strip()}\n"
                f"**Result Count:** 0\n"
                f"**Details:** Error generating or running Cypher."
            )
        else:
            summary_text = "No results."

    # 1) Summary
    st.subheader("🗣️ Plain-English Summary")
    display_summary(choice, summary_text)

    # 2) Cypher
    st.subheader("🧪 Cypher used")
    st.code(cypher_for_display or "-- no cypher generated --", language="cypher")

    # 3) Raw Results
    st.subheader("📦 Raw results")
    st.json(rows, expanded=False)
