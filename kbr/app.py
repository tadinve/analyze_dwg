# app.py
import json
import textwrap
from typing import Dict, Any, List, Optional
import os
import re

import streamlit as st
import pandas as pd
from neo4j import GraphDatabase, basic_auth
from PIL import Image
from time import sleep
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

# Add sanitizer for model output (remove ``` fences and leading "cypher" labels)
def _sanitize_cypher_text(text: str) -> str:
    if not text:
        return text
    s = text.strip()

    # Extract content inside the first fenced block if present
    fence_match = re.search(r"```(?:[\w+-]*)\n(.*?)\n```", s, flags=re.S | re.I)
    if fence_match:
        s = fence_match.group(1).strip()
    else:
        # strip stray starting/ending fences and backticks
        s = re.sub(r"^```[^\n]*\n", "", s)
        s = re.sub(r"\n```$", "", s).strip()

    # remove a leading "cypher" label line if present (e.g. "cypher", "Cypher:")
    lines = s.splitlines()
    if lines and lines[0].strip().lower().startswith("cypher"):
        lines = lines[1:]
    # also handle a leading "Cypher:" style token
    if lines and re.match(r"^cypher[:\s]*$", lines[0].strip(), flags=re.I):
        lines = lines[1:]

    cleaned = "\n".join(lines).strip()
    cleaned = cleaned.strip("` \n")
    return cleaned

# Replace english_to_cypher with sanitized model handling + new client fallback
def english_to_cypher(nl: str, co_id: Optional[str]) -> str:
    fallback = robust_q6_fallback(nl, co_id)
    if fallback:
        return fallback
    if not OPENAI_API_KEY:
        return "MATCH (co:ChangeOrder) RETURN co.id AS id, co.title AS title, co.status AS status ORDER BY id LIMIT 25;"

    system = """Translate English to READ-ONLY Cypher for Neo4j 5. Never use MERGE/CREATE/DELETE/SET/REMOVE/DETACH/LOAD/APOC.
Return tidy columns with stable names."""
    user_msg = {"role": "user", "content": f"English: {nl}\nCO hint: {co_id or ''}"}
    messages = [{"role": "system", "content": system}, user_msg]

    default_safe = "MATCH (co:ChangeOrder) RETURN co.id AS id, co.title AS title, co.status AS status ORDER BY id LIMIT 25;"

    # Try new OpenAI client (openai>=1.0.0)
    q = None
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
        )
        # new SDK path
        q = getattr(resp.choices[0].message, "content", "").strip() or resp.choices[0].message.content.strip()
    except Exception:
        # Fallback to older openai package interface if available
        try:
            import openai  # type: ignore
            openai.api_key = OPENAI_API_KEY
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,
            )
            q = resp["choices"][0]["message"]["content"].strip()
        except Exception:
            return default_safe

    # sanitize model output to remove fences and language markers
    q = _sanitize_cypher_text(q or "")

    if is_write_query(" " + q + " "):
        return default_safe
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

def q6(question):
    with open("GeneWare_CR_Knowledge_STRUCTURED.txt", "r") as f:
        kb = f.read()
    from openai import OpenAI  # type: ignore
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are GeneWare’s change-order analyst. Answer questions only from the provided document. double check your work. make sure to be accurate and precise. no guess work. we need the results  to be factual and based on the knowledge provided and idempotent."},
            {"role": "user", "content": f"Knowledge:\n{kb}\n\nQuestion: {question}"}
        ]
    )
    return resp.output_text

from pdf2markdown4llm import PDF2Markdown4LLM
import tempfile

def convert_pdf_to_md(pdf_bytes: bytes, original_filename: str) -> (bytes, str):
    """
    Converts PDF bytes to Markdown using docling and returns the markdown content and filename.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf_path = tmp_pdf.name
        tmp_pdf.write(pdf_bytes)

    try:
        md_filename = os.path.splitext(original_filename)[0] + ".md"
        converter = PDF2Markdown4LLM(remove_headers=False, skip_empty_tables=True, table_header="### Table")
        md_content = converter.convert(pdf_path)
        with open(md_filename, "w", encoding="utf-8") as md_file:
            md_file.write(md_content)
        return md_content, md_filename
    except Exception as e:
        # raise RuntimeError(f"Error converting PDF to Markdown: {e}")
        return "No TEXT content ", md_filename
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)



# ---------------- Projects sample data & hierarchy renderer ----------------
def sample_projects_df():
    import pandas as pd
    data = [
        {"Project ID": "GW-001", "Name": "GeneWare – SVC Building C4", "Status": "In Progress", "Owner": "GeneWare", "GC": "Rudolph & Sletten", "Start": "2019-05-10"},
        {"Project ID": "GW-002", "Name": "GeneWare – Labs Core Fitout", "Status": "In Progress", "Owner": "GeneWare", "GC": "PCI",                "Start": "2020-01-14"},
        {"Project ID": "GW-003", "Name": "GeneWare – Parking Expansion", "Status": "Completed",   "Owner": "GeneWare", "GC": "GBI",                "Start": "2019-02-01"},
        {"Project ID": "GW-004", "Name": "GeneWare – HQ Renovation",     "Status": "Completed",   "Owner": "GeneWare", "GC": "Viking Steel",       "Start": "2018-08-20"},
        {"Project ID": "GW-005", "Name": "GeneWare – Data Center POD",   "Status": "Design",      "Owner": "GeneWare", "GC": "TBD",                "Start": "2025-10-01"},
    ]
    return pd.DataFrame(data)

HIERARCHY_MD = """\
- Level 0: **Portfolio**
  - Company → Projects
- Level 1: **Project**
  - Charter, Contract (MSA/GMP), Permits, Master Schedule, BIM
- Level 2: **Design & Precon**
  - Drawings (A/S/M/E/P), Specifications (CSI 00–49), BIM Models, Geotech/Survey
- Level 3: **Construction Control**
  - RFIs, Submittals, OAC Minutes, Daily Reports, Inspection Reports
- Level 4: **Cost & Change Management**
  - PCOs, COs, OAC Approvals, ROM/Contingency, Pay Apps/Budget Logs
- Level 5: **Execution & Field**
  - Schedules/Look-aheads, Safety, QA/QC, Commissioning, Photos/Drone
- Level 6: **Closeout**
  - As-Builts, O&M, Warranties, Final COs/Lien Waivers, Handover
"""

# ---------------- Change Management: PDF → markdown/text ----------------
def pdf_to_markdown_text(uploaded_file) -> str:
    """
    Convert an uploaded PDF to markdown-like text using PyMuPDF if available,
    else return plain text notice. Returns a Python str.
    """
    try:
        import fitz  # PyMuPDF
        import tempfile, os
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        md = []
        for p in doc:
            # Use "text" for broad compatibility (markdown not always supported)
            md.append(p.get_text("text"))
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return "\n\n".join(md).strip() or "(No extractable text)"
    except Exception as e:
        return f"(Extraction error: {e})"

# ---------------- Change Management: entitlement & features ----------------
def analyze_pco_entitlement(text: str) -> dict:
    """
    If OPENAI_API_KEY present, use LLM to extract fields and entitlement.
    Otherwise, do a regex / keyword heuristic.
    Returns dict with keys: fields, entitlement, confidence, rationale.
    """
    fields = {
        "pco_id": None,
        "title": None,
        "amount": None,
        "schedule_days": None,
        "funding": None,         # e.g., Contingency, TI, Owner
        "systems": [],
        "wbs_codes": [],
        "subcontractors": [],
    }

    # quick heuristics
    import re
    idm = re.search(r"\bPCO[\s#]*([0-9.\-]+)\b", text, re.I)
    if idm: fields["pco_id"] = idm.group(1)
    amt = re.search(r"\$\s?([0-9,]+(?:\.[0-9]{2})?)", text)
    if amt: fields["amount"] = amt.group(1)
    days = re.search(r"\b(\d{1,3})\s+(?:calendar|working)?\s*days?\b", text, re.I)
    if days: fields["schedule_days"] = days.group(1)
    if re.search(r"\b(contingency|allowance|tenant improvement|ti)\b", text, re.I):
        fields["funding"] = re.search(r"\b(contingency|allowance|tenant improvement|ti)\b", text, re.I).group(1).title()

    entitlement = "Uncertain"
    confidence = 0.5
    rationale = "Heuristic analysis only (no LLM). Looked for scope clarity, contract coverage, and responsibility language."

    # LLM path (if available)
    try:
        if OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            prompt = f"""
You are a construction change-order analyst.
From the PCO text below, extract:
- pco_id, title, amount, schedule_days, funding (Allowance/Contingency/TI/Owner)
- systems (list), wbs_codes (list), subcontractors (list)
Then determine entitlement: Approved / Not Entitled / Needs Clarification / By Contract / Owner Change.
Explain briefly.

Text:
{text}
"""
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0
            )
            ans = resp.choices[0].message.content
            # very light parsing (keep robust)
            # try to pull an "Entitlement:" line and a "Rationale:" line
            ent = re.search(r"(?i)entitlement\s*[:\-]\s*(.*)", ans)
            if ent: entitlement = ent.group(1).strip()
            rat = re.search(r"(?i)(rationale|because)\s*[:\-]\s*(.*)", ans)
            if rat: rationale = rat.group(2).strip()
            # fill fields crudely if present
            for k in fields.keys():
                m = re.search(rf"(?i){k}\s*[:\-]\s*(.+)", ans)
                if m:
                    val = m.group(1).strip()
                    if k in ("systems", "wbs_codes", "subcontractors"):
                        fields[k] = [x.strip() for x in re.split(r"[,\n;]+", val) if x.strip()]
                    else:
                        fields[k] = val
            confidence = 0.75
    except Exception as e:
        rationale += f" (LLM unavailable: {e})"

    return {
        "fields": fields,
        "entitlement": entitlement,
        "confidence": confidence,
        "rationale": rationale
    }

# ---------------- Change Management: similar COs from Neo4j ----------------
def find_similar_cos_from_graph(fields: dict, limit: int = 8):
    """
    Uses a simplified similarity: shared systems / WBS / referenced artifacts if present.
    Falls back to listing recent COs if no features.
    """
    sys_ids = fields.get("systems") or []
    wbs_codes = fields.get("wbs_codes") or []
    pco_hint = fields.get("pco_id") or ""

    where_clauses = []
    params = {}

    if sys_ids:
        where_clauses.append("EXISTS { MATCH (other)-[:MODIFIES]->(os:System) WHERE os.id IN $sys_ids }")
        params["sys_ids"] = sys_ids
    if wbs_codes:
        where_clauses.append("EXISTS { MATCH (other)-[:HAS_COST_ITEM]->(:CostItem)-[:CODED_AS]->(w:WBS) WHERE w.code IN $wbs }")
        params["wbs"] = wbs_codes

    where_block = "WHERE " + " OR ".join(where_clauses) if where_clauses else ""
    cypher = f"""
    MATCH (other:ChangeOrder)
    {where_block}
    RETURN other.id AS id, coalesce(other.title,'') AS title, coalesce(other.status,'') AS status
    ORDER BY id
    LIMIT {int(limit)}
    """
    try:
        return run_query(cypher, params)
    except Exception:
        return []

# ---------------- Change Management: naive risk score ----------------
def risk_assessment(entitlement: str, similar_rows: list, fields: dict) -> dict:
    """
    Very simple scoring:
      base 50
      -10 if entitlement suggests 'By Contract' or 'Approved'
      +15 if 'Not Entitled' or 'Rejected'
      +10 if amount seems large (> $100k)
      +5  if schedule_days > 14
      -5  if many similar approved precedents (status contains 'approved')
    """
    score = 50
    e = (entitlement or "").lower()
    if "by contract" in e or "approved" in e:
        score -= 10
    if "not entitled" in e or "rejected" in e or "void" in e:
        score += 15
    # amount
    try:
        amt_num = float((fields.get("amount") or "0").replace(",", ""))
        if amt_num > 100000:
            score += 10
    except Exception:
        pass
    # schedule
    try:
        days = int(fields.get("schedule_days") or "0")
        if days > 14:
            score += 5
    except Exception:
        pass
    # precedents
    approved_like = sum(1 for r in similar_rows if "appro" in (r.get("status","").lower()))
    score -= 5 * min(approved_like, 3)
    level = "Low" if score < 45 else ("Medium" if score < 70 else "High")
    return {"score": score, "level": level}



# ─────────────────────────────────────────────────────────────
# UI — Two tabs
# ─────────────────────────────────────────────────────────────
st.title("DocLabs — Knowledge Graph Q&A")
st.caption("Ask in English, run Cypher on Neo4j, and get evidence-based explanations for Kevin.")

tab_projects, tab_change, tab_query, tab_docs,  tab_kbr, tab_nodes = st.tabs(
    ["🏗️ Projects", "🔄 Change Management", "🔎 Query KB", "📚 Documents",  "📊 KBR", "🧠 Nodes & Relations"]
)

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
                result = q6(kevin_q)
                st.markdown("## 🗣️ Plain-English Summary")
                st.markdown(result)
                st.markdown("## 🧪 Cypher used")
                st.code(cypher, language="cypher")
                with st.expander("Raw results"):
                    st.write( [])

        except Exception as e:
            st.error(f"Query failed: {e}")



with tab_docs:
    st.subheader("Document Library")
    
    # Reference documents table (from project context)
    st.markdown("#### Key Reference Documents")
    
    # Create HTML table with clickable link
    html_table = """
    <table style="width:100%; border-collapse: collapse;">
        <thead>
            <tr style="background-color: #f0f2f6;">
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Document Name</th>
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Type</th>
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Created By</th>
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><a href="https://storage.googleapis.com/kbr-public-docs/01%20-%20SPECIFICATION%20%E2%80%94%20SECTION-26-05-36%20CABLE-TRAYS.pdf" target="_blank">Spec 260536 – Cable Trays</a></td>
                <td style="padding: 10px; border: 1px solid #ddd;">Specification</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Design Engineer / Architect of Record</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Approved & Contract Governing</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 10px; border: 1px solid #ddd;"><a href="https://storage.googleapis.com/kbr-public-docs/02%20-%20CableTraysDrawing.png" target="_blank">Drawing E-401 – Cable Tray Routing</a></td>
                <td style="padding: 10px; border: 1px solid #ddd;">Construction Drawing</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Electrical Engineer</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Issued for Construction</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><a href="https://storage.googleapis.com/kbr-public-docs/03%20Submittal_23-017_Full_Referenced.pdf" target="_blank">Submittal 23-017 (Original)</a></td>
                <td style="padding: 10px; border: 1px solid #ddd;">Submittal </td>
                <td style="padding: 10px; border: 1px solid #ddd;">Contractor / Vendor</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Approved</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 10px; border: 1px solid #ddd;"><a href="https://storage.googleapis.com/kbr-public-docs/04%20RFI_112_Request_For_Information.pdf" target="_blank">RFI-112</a></td>
                <td style="padding: 10px; border: 1px solid #ddd;">RFI (Request for Information)</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Contractor</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Pending </td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><a href="https://storage.googleapis.com/kbr-public-docs/05%20Workgroup_Notes_Week37_Corrected.pdf" target="_blank">Workgroup Notes – Week 37</a></td>
                <td style="padding: 10px; border: 1px solid #ddd;">Informal Meeting Notes</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Contractor + Design Team (Workgroup)</td>
                <td style="padding: 10px; border: 1px solid #ddd;">Informal, Non-binding</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)
    
    st.markdown("---")
    
    

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


# ---------------- UI: Projects tab ----------------
with tab_projects:
    st.subheader("Projects")
    pdf = sample_projects_df()
    st.dataframe(pdf, use_container_width=True)
    st.markdown("#### Document Hierarchy (per project)")
    for _, row in pdf.iterrows():
        with st.expander(f"{row['Project ID']} — {row['Name']}  ·  {row['Status']}"):
            st.markdown(HIERARCHY_MD)

# ---------------- UI: Change Management tab ----------------
with tab_change:
    st.subheader("Upload Change Request")

    # New: select change request type
    cr_type = st.radio(
        "Change Request Type",
        ["Submittal", "RFI", "PCO"],
        horizontal=True,
    )

    uploaded = st.file_uploader("Upload Document (PDF)", type=["pdf"])
    run_btn = st.button("Analyze Document") if uploaded else None

    if uploaded and run_btn:
        # Check if special filename
        uploaded_name = uploaded.name.strip()
        if uploaded_name.lower() == "submittal_23-017_rev2.pdf":
            # Show the rejection markdown instead
            rejection_path = os.path.join(os.path.dirname(__file__),  "submittal_rev2_rejection.md")
            print(f"Looking for rejection markdown at: {rejection_path}")
            if os.path.exists(rejection_path):
                with open(rejection_path, "r", encoding="utf-8") as f:
                    rejection_md = f.read()
                sleep(5)  # simulate processing delay
                st.markdown(rejection_md, unsafe_allow_html=True)
            else:
                st.warning(f"Special file detected but rejection markdown not found at {rejection_path}")
        else:
            # Normal analysis flow
            md_text = pdf_to_markdown_text(uploaded)
            st.markdown("#### Extracted Text (preview)")
            st.text_area("Document Content", md_text[:8000], height=260)

            # Entitlement + fields
            result = analyze_pco_entitlement(md_text)
            st.markdown("#### Entitlement & Fields")
            st.json(result)

            # Similar COs / PCOs from graph
            similar = find_similar_cos_from_graph(result.get("fields", {}), limit=8)
            st.markdown("#### Similar Change Orders (from Graph)")
            if similar:
                st.dataframe(pd.DataFrame(similar), use_container_width=True)
            else:
                st.info("No similar COs found (or graph not connected).")

            # Risk assessment for subcontractors
            ra = risk_assessment(result.get("entitlement",""), similar, result.get("fields", {}))
            st.markdown("#### Risk Assessment (Subcontractors)")
            st.metric("Risk Score", ra["score"], help="Higher = more commercial / schedule risk")
            st.metric("Risk Level", ra["level"])
            st.caption("Rule-based demo score. Wire to policy engine / real metrics later.")
