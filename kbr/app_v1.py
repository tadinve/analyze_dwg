import json
import re
import streamlit as st
from neo4j import GraphDatabase

# ---------------------------
# Page setup
# ---------------------------
st.set_page_config(page_title="DocLabs KG Q&A", page_icon="🧭", layout="centered")
st.title("DocLabs — Knowledge Graph Q&A")
st.caption("Ask in English, run Cypher on Neo4j, and get an evidence-based explanation for Kevin.")

# ---------------------------
# Secrets / connection
# ---------------------------
NEO4J_URI = st.secrets.get("NEO4J_URI", st.sidebar.text_input("Neo4j URI", "neo4j+s://<your-auradb-uri>"))
NEO4J_USER = st.secrets.get("NEO4J_USER", st.sidebar.text_input("Neo4j user", "neo4j"))
NEO4J_PASS = st.secrets.get("NEO4J_PASS", st.sidebar.text_input("Neo4j password", type="password"))

# ---------------------------
# Connection helpers
# ---------------------------
@st.cache_resource(show_spinner=False)
def get_driver(uri, user, pwd):
    return GraphDatabase.driver(uri, auth=(user, pwd))

def run_cypher(query: str):
    driver = get_driver(NEO4J_URI, NEO4J_USER, NEO4J_PASS)
    with driver.session() as s:
        res = s.run(query)
        return [r.data() for r in res]

def sanitize_query(q: str) -> bool:
    """Block write queries for safety."""
    q_up = re.sub(r"\s+", " ", q.upper())
    forbidden = [
        " CREATE ", " MERGE ", " DELETE ", " DETACH ", " SET ",
        " REMOVE ", " DROP ", " LOAD CSV", " CALL DBMS", " CALL APOC", " CALL TX"
    ]
    return not any(tok in q_up for tok in forbidden)

# ---------------------------
# Q1: Entitlement Template
# ---------------------------
def q1_template_for_entitlement(co_id: str = "CO-042") -> str:
    return f"""
// Q1: Entitlement Evidence for {co_id}
MATCH (co:ChangeOrder {{id:'{co_id}'}})
OPTIONAL MATCH (co)-[:REFERS_TO]->(ref)
WITH co, collect(DISTINCT ref) AS referenced
OPTIONAL MATCH (coChunk:Chunk)
WHERE coChunk.id STARTS WITH co.id + '#'
OPTIONAL MATCH (coChunk)-[:CITES]->(ev:Chunk)
WITH co, referenced, collect(DISTINCT ev) AS citedChunks
OPTIONAL MATCH (ctDoc:Document)-[:HAS_CHUNK]->(ctch:Chunk)
WHERE (ctDoc.type = 'Contract' OR ctDoc.id STARTS WITH 'CT-001')
  AND ctch.section IN ['SOW','Exclusions']
RETURN
  co.number AS changeOrder,
  co.title  AS title,
  co.status AS status,
  [r IN referenced WHERE r IS NOT NULL |
     labels(r)[0] + ':' + coalesce(r.id, r.number)] AS referencedArtifacts,
  [e IN citedChunks WHERE e IS NOT NULL |
     {{ id:e.id, section:e.section, text:substring(e.text,0,140)+'...' }}] AS citedEvidence,
  [e IN collect(DISTINCT ctch) WHERE e IS NOT NULL |
     {{ id:e.id, section:e.section, text:substring(e.text,0,140)+'...' }}] AS contractClauses
""".strip()

def explain_entitlement(rows):
    if not rows:
        return "No results. Check CO id or data."
    r = rows[0]
    parts = [
        f"### {r.get('changeOrder','')} — {r.get('title','')}",
        f"**Status:** {r.get('status','')}"
    ]
    refs = r.get("referencedArtifacts") or []
    parts.append("**Referenced artifacts:** " + (", ".join(refs) if refs else "(none found)"))
    ev = r.get("citedEvidence") or []
    if ev:
        parts.append("**Cited evidence (snippets):**")
        for e in ev:
            parts.append(f"- {e.get('id','')} §{e.get('section','')}: “{e.get('text','')}”")
    cls = r.get("contractClauses") or []
    if cls:
        parts.append("**Contract clauses:**")
        for c in cls:
            parts.append(f"- {c.get('id','')} §{c.get('section','')}: “{c.get('text','')}”")
    # Verdict heuristic
    hint, txt = "Needs Clarification", "Evidence incomplete."
    if any((c.get("section") or "").lower() == "exclusions" for c in cls) and any(
        "owner directs" in (e.get("text","").lower()) for e in ev
    ):
        hint, txt = "Likely Out-of-Scope", "Exclusions + Owner directive detected."
    elif any((c.get("section") or "").lower() == "sow" for c in cls):
        hint, txt = "Possibly In-Scope", "SOW cited — review details."
    parts.append(f"**Verdict hint:** {hint} — {txt}")
    return "\n\n".join(parts)

# ---------------------------
# Q2: Precedent Template
# ---------------------------
def q2_template_for_precedent(co_id="CO-042") -> str:
    return f"""
// Q2: Precedent search for {co_id}
MATCH (co:ChangeOrder {{id:'{co_id}'}})
OPTIONAL MATCH (co)-[:REFERS_TO]->(art)
OPTIONAL MATCH (co)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(wbs:WBS)
WITH co, collect(DISTINCT art) AS artifacts, collect(DISTINCT wbs.code) AS wbsCodes
MATCH (other:ChangeOrder)
WHERE other.id <> co.id
OPTIONAL MATCH (other)-[:REFERS_TO]->(a)
OPTIONAL MATCH (other)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(w:WBS)
WHERE a IN artifacts OR w.code IN wbsCodes
WITH co, other, collect(DISTINCT a) AS sharedArtifacts, collect(DISTINCT w.code) AS sharedWBS
OPTIONAL MATCH (other)-[:REFERS_TO]->(ref)
OPTIONAL MATCH (other)-[:HAS_COST_ITEM]->(oci)-[:CODED_AS]->(owbs)
WITH co, other, sharedArtifacts, sharedWBS,
     collect(DISTINCT ref) AS refs,
     collect(DISTINCT owbs.code) AS codes
RETURN
  co.id AS targetCO,
  other.id AS similarCO,
  other.title AS title,
  other.status AS status,
  sharedWBS + codes AS matchedWBS,
  [r IN sharedArtifacts + refs WHERE r IS NOT NULL |
     labels(r)[0] + ':' + coalesce(r.id,r.number)] AS matchedArtifacts
ORDER BY other.status
LIMIT 10
""".strip()

def explain_precedent(rows):
    if not rows:
        return "No similar change orders found for this scope."
    parts = ["### Similar Change Orders (Precedents)"]
    for r in rows:
        parts.append(
            f"**{r['similarCO']}** — {r.get('title','(untitled)')} "
            f"→ *Status:* {r.get('status','Unknown')}"
        )
        if r.get('matchedWBS'):
            parts.append(f"• **WBS match:** `{', '.join([x for x in r['matchedWBS'] if x])}`")
        if r.get('matchedArtifacts'):
            parts.append(f"• **Shared artifacts:** {', '.join([x for x in r['matchedArtifacts'] if x])}")
        parts.append("---")
    return "\n".join(parts)

# ---------------------------
# Q3: Executive Summary Template
# ---------------------------
def q3_template_for_summary(co_id="CO-042") -> str:
    return f"""
// Q3: Executive summary & impact for {co_id}
MATCH (co:ChangeOrder {{id:'{co_id}'}})
OPTIONAL MATCH (co)-[:HAS_COST_ITEM]->(ci:CostItem)-[:CODED_AS]->(wbs:WBS)
WITH co,
     collect({{type:ci.type, code:ci.code, amount:ci.amount, wbs:wbs.name}}) AS costs,
     sum(coalesce(ci.amount,0)) AS totalCost
OPTIONAL MATCH (co)-[:IMPACTS]->(act:Activity)-[:BELONGS_TO]->(sched:Schedule)
WITH co, costs, totalCost,
     collect({{activity:act.name, duration:act.durationDays, critical:act.isCritical, schedule:sched.version}}) AS scheduleImpact
OPTIONAL MATCH (co)-[:REQUESTED_BY]->(req:Person)
OPTIONAL MATCH (co)-[:PARTY_TO]->(vendor:Vendor)
WITH co, costs, totalCost, scheduleImpact,
     coalesce(req.name,'(unknown)') AS requestedBy,
     coalesce(vendor.name,'(unspecified)') AS vendorName
OPTIONAL MATCH (ctDoc:Document {{type:'Contract'}})-[:HAS_CHUNK]->(ct:Chunk)
WHERE ct.section IN ['SOW','Exclusions']
WITH co, costs, totalCost, scheduleImpact, requestedBy, vendorName,
     collect({{section:ct.section, text:substring(ct.text,0,120)+'...'}}) AS contractRefs
RETURN
  co.id AS changeOrder,
  co.title AS title,
  co.status AS status,
  requestedBy,
  vendorName,
  totalCost,
  costs,
  scheduleImpact,
  contractRefs
LIMIT 1
""".strip()

def explain_executive_summary(rows):
    if not rows:
        return "No data available for this Change Order."
    r = rows[0]
    parts = [f"### Executive Summary for {r.get('changeOrder')} — {r.get('title','')}"]
    parts.append(f"**Status:** {r.get('status','')}")
    parts.append(f"**Requested by:** {r.get('requestedBy','')}")
    parts.append(f"**Vendor:** {r.get('vendorName','')}")
    total = r.get('totalCost', 0)
    parts.append(f"**Total Estimated Cost:** ${total:,.0f}")
    costs = r.get('costs', [])
    if costs:
        parts.append("**Cost Breakdown:**")
        for c in costs:
            parts.append(f"- {c.get('type','')} (${c.get('amount',0):,.0f}) — {c.get('wbs','')}")
    schedule = r.get('scheduleImpact', [])
    if schedule:
        parts.append("**Schedule Impact:**")
        for s in schedule:
            crit = " (Critical Path)" if s.get('critical') else ""
            parts.append(f"- {s.get('activity','')} — {s.get('duration',0)} days{crit}")
    crefs = r.get('contractRefs', [])
    if crefs:
        parts.append("**Relevant Contract Clauses:**")
        for c in crefs:
            parts.append(f"- {c['section']}: “{c['text']}”")
    return "\n\n".join(parts)

# ---------------------------
# UI
# ---------------------------
query_type = st.selectbox(
    "Query Type",
    ["Entitlement (Q1)", "Precedent (Q2)", "Executive Summary (Q3)"]
)
co_id = st.text_input("CO id", "CO-042")
question = st.text_area("Kevin’s question (optional free text)", "", height=70)

if st.button("Run"):
    if query_type.startswith("Entitlement"):
        cypher = q1_template_for_entitlement(co_id)
        explain_fn = explain_entitlement
    elif query_type.startswith("Precedent"):
        cypher = q2_template_for_precedent(co_id)
        explain_fn = explain_precedent
    else:
        cypher = q3_template_for_summary(co_id)
        explain_fn = explain_executive_summary

    st.subheader("Generated Cypher (read-only)")
    st.code(cypher, language="cypher")

    if not sanitize_query(cypher):
        st.error("Blocked: query contains write operations. Only read-only Cypher is allowed.")
    else:
        try:
            rows = run_cypher(cypher)
            with st.expander("Raw JSON result"):
                st.json(rows)
            st.subheader("Answer for Kevin")
            st.markdown(explain_fn(rows))
        except Exception as e:
            st.error(f"Query failed: {e}")
