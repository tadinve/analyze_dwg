# 🧠 DocLabs Construction Knowledge Graph

## Overview
The DocLabs Knowledge Graph unifies **Change Orders**, **Contracts**, **Documents**, and **AI analyses** into a single connected reasoning framework.  
It provides explainable insights into entitlement, coverage, and impact — allowing users to trace every CO to its contractual and evidentiary roots.

---

## 🏗️ Project Core Nodes

### **Project**
The `Project` node anchors all construction activity within a defined scope and timeline.  
It connects to contracts, schedules, and design documents, acting as the contextual root for entitlement reasoning and analysis.

---

### **ChangeOrder**
`ChangeOrder` nodes represent approved or proposed modifications to project scope, cost, or schedule.  
They are central to the graph, linking to systems, cost items, vendors, documents, and AI analyses to provide end-to-end traceability of each change.

---

### **Contract**
`Contract` defines the binding legal and commercial framework of the project.  
It connects to allowances, contingencies, and unit-price items that determine entitlement coverage for a given CO.

---

### **Document**
A `Document` node represents an authoritative source such as a specification, RFI, or submittal.  
Each document connects to its type, category, and individual `Chunk` nodes containing clause-level content used for evidence retrieval.

---

### **DocType / DocCategory / DocumentLibrary**
These nodes form the classification hierarchy for the document ecosystem.  
`DocType` defines functional types (e.g., “Specification”, “RFI”), while `DocCategory` groups them by theme (e.g., “Design Documents”), all linked under a global `DocumentLibrary`.

---

## 📑 Technical Context Nodes

### **RFI (Request for Information)**
`RFI` nodes capture clarification requests or field queries between project participants.  
They serve as direct evidence for entitlement when linked to Change Orders through the `REFERS_TO` relationship.

---

### **Spec (Specification)**
`Spec` nodes define the technical and quality standards for project execution.  
They are cited in COs to establish whether proposed work falls inside or outside baseline requirements.

---

### **System**
`System` nodes represent functional groupings such as HVAC, Modular Walls, or Electrical systems.  
They provide a technical structure to cluster related Change Orders and enable system-level impact analysis.

---

### **Allowance / Contingency / UnitPriceItem**
These commercial nodes represent predefined contractual buffers or pricing structures.  
They allow Q4 queries to check if a CO is covered by allowance, contingency, or unit-price terms within the main contract.

---

### **Design Basis**
`DesignBasis` defines the design intent and performance criteria used at project initiation.  
It helps evaluate alignment or deviation of a CO against original design expectations.

---

## 🧩 Analytical and AI Nodes

### **AnalysisRun**
Represents a timestamped AI evaluation of a Change Order.  
It links to evidence, metrics, and recommendations, storing the logic used to derive the AI’s determination.

---

### **Evidence**
`Evidence` nodes contain the factual or textual support used in entitlement analysis.  
They link to `Chunk` nodes, showing exactly which document sections justify each determination.

---

### **Metric**
`Metric` nodes quantify analytical parameters such as coverage, clarity, consistency, and precedent similarity.  
These metrics allow quantitative comparison between multiple analyses and projects.

---

### **Recommendation**
`Recommendation` nodes store the AI’s decision and reasoning narrative (e.g., “Not Entitled – owner directive”).  
They provide human-readable output that can be reviewed and audited by project managers.

---

### **PotentialCO**
`PotentialCO` represents early observations or unconfirmed changes prior to formalization.  
It evolves into a `ChangeOrder` node through the `EVOLVES_TO` relationship, maintaining a record of change progression.

---

### **FieldDirective**
`FieldDirective` captures on-site instructions issued by the owner or engineer.  
They often trigger CO creation and serve as strong entitlement indicators, especially when linked to Design Basis or Contract clauses.

---

## 🧱 Contextual and Execution Nodes

### **WorkArea / Drawing / MeetingMinutes**
These nodes provide spatial and procedural context.  
`WorkArea` localizes scope, `Drawing` defines geometry or details, and `MeetingMinutes` record project decisions that influence COs.

---

### **CostItem / WBS / Vendor / Person**
This group captures financial accountability and project roles.  
`CostItem` nodes represent billable items; `WBS` encodes schedule or budget hierarchy; `Vendor` and `Person` provide accountability and provenance.

---

### **Chunk / Term / Keyword**
These nodes support semantic analysis and search.  
`Chunk` represents paragraph-level text; `Term` captures domain concepts; `Keyword` indexes frequently queried terms for retrieval and clustering.

---

### **Activity / Schedule**
`Activity` nodes represent granular project tasks, while `Schedule` defines macro-phase timelines.  
They link Change Orders to execution and delay impact assessments.

---

## 🔗 Relationship Types and Descriptions

| Relationship | Description |
|---------------|--------------|
| **HAS_CONTRACT** | Links a Project to its governing Contract. This relationship defines which agreement governs entitlement, providing the reference baseline for all commercial analysis. |
| **REFERS_TO** | Connects a Change Order to any referenced document (RFI, Spec, Drawing, etc.). It captures the justification trail behind a scope change or claim. |
| **HAS_DOCUMENT** | Associates a Contract or Activity with its relevant Document set. It ensures traceability between governing rules and executed work artifacts. |
| **HAS_CHUNK** | Links a Document to its paragraph-level Chunks. This enables fine-grained evidence retrieval for AI and RAG systems. |
| **CITES / EVIDENCE_FROM** | Links Evidence or AnalysisRun to the source text (Chunk) from which justification was derived. It underpins explainable AI reasoning by showing the textual basis for each decision. |
| **HAS_METRIC / HAS_RECOMMENDATION** | Associates an AnalysisRun with its outcome metrics and AI recommendation. Together, they form the structured analytical result for entitlement classification. |
| **USES_EVIDENCE** | Connects an AnalysisRun to the set of Evidence nodes it relied upon. It allows traceability of analytical inputs and confidence factors. |
| **COVERED_BY / HAS_ALLOWANCE / HAS_CONTINGENCY / HAS_UNIT_PRICE** | Represents financial coverage links between a Change Order and contractual instruments. These relationships enable automated entitlement validation under Q4. |
| **EVOLVES_TO** | Connects a PotentialCO to the formalized ChangeOrder it became. This captures issue lifecycle from early observation to commercial documentation. |
| **TRIGGERS** | Indicates that a FieldDirective directly caused or influenced a ChangeOrder. It highlights owner-driven change origins for entitlement evaluation. |
| **PARTY_TO / REQUESTED_BY / ADDRESSES** | Describe the human and organizational roles around a CO. They record initiators, requesters, and affected parties for audit traceability. |
| **CODED_AS** | Links a CostItem to a WBS element or classification code. This enables aggregation and cost reporting aligned with enterprise ERP systems. |
| **BELONGS_TO** | Groups nodes such as Document, DocType, or Activity under a library or collection. It preserves organizational structure and supports document taxonomy. |
| **HAS_SYSTEM / IMPACTS / AFFECTS** | Connect a CO to Systems, WorkAreas, or other affected entities. These relationships power system-level and spatial impact visualizations. |
| **HAS_ANALYSIS** | Associates a Change Order with its performed AI analysis runs. It links manual workflows with automated reasoning history. |
| **HAS_EVIDENCE** | Directly connects a Change Order to its supporting Evidence nodes. This ensures every decision is backed by verifiable source material. |
| **HAS_TYPE / IN_CATEGORY** | Maps each Document to its DocType and DocCategory. This maintains consistent classification for efficient search and filtering. |

---

# Knowledge Graph Summary

## Central node types
- ChangeOrder — central domain entity (unique `id`). Indexes on `status`, `reason`.
- Document — documents (unique `id`) with relationship to DocType / DocCategory and HAS_CHUNK -> Chunk.
- Chunk — document/fragment nodes (unique `id`) with `embedding` index (used for semantic search).
- Evidence — evidence bundles (unique `id`) linked to Chunks via EVIDENCE_FROM.
- AnalysisRun / Recommendation / Metric — AI analysis results and recommendations linked to ChangeOrder via HAS_ANALYSIS → AnalysisRun and RECOMMENDS → Recommendation.
- Spec, RFI, Submittal, DesignBasis, Contract, Project, Vendor, Person, System, WorkArea, Schedule, CostItem, WBS, Allowance, Contingency, UnitPriceItem, Scenario, etc.

## Important constraints & indexes
- Most domain nodes enforce uniqueness on `id` (e.g. `ChangeOrder.id`, `Document.id`, `Chunk.id`, etc.).
- Chunk has an `embedding` index for vector/semantic lookup.
- WBS (`code`), Spec (`section`), Vendor (`name`), DocType/DocCategory (`name`) have uniqueness/indexes as appropriate.

## Common relationship patterns
- ChangeOrder → REFERS_TO → Spec / RFI / Submittal / Document (artifacts)
- Document → HAS_CHUNK → Chunk
- Evidence → EVIDENCE_FROM → Chunk
- ChangeOrder → HAS_EVIDENCE → Evidence
- ChangeOrder → HAS_COST_ITEM → CostItem → CODED_AS → WBS
- ChangeOrder → MODIFIES → System
- ChangeOrder → HAS_ANALYSIS → AnalysisRun → HAS_METRIC / USES_EVIDENCE → Evidence → EVIDENCE_FROM → Chunk
- AnalysisRun → RECOMMENDS → Recommendation
- DocType → IN_CATEGORY → DocCategory ; Document → IS_A → DocType

## How to answer typical questions (example Cypher)
- Fetch entitlement evidence for a CO:
  MATCH (co:ChangeOrder {id:$co_id})-[:HAS_EVIDENCE]->(ev:Evidence)-[:EVIDENCE_FROM]->(ch:Chunk)
  RETURN co.id AS changeOrder, collect(ch.id) AS chunkIds

- Find precedent COs sharing artifacts / WBS / systems:
  (match target CO artifacts/WBS/systems, then find other COs with overlaps and return matched items)

- Latest analysis + recommendation for a CO:
  MATCH (co:ChangeOrder {id:$co_id})-[:HAS_ANALYSIS]->(ar:AnalysisRun)
  WITH co, ar ORDER BY ar.timestamp DESC LIMIT 1
  OPTIONAL MATCH (ar)-[:RECOMMENDS]->(rec:Recommendation)
  RETURN co.id, ar.id, ar.determination, rec.action

- List documents in a category / doc type (used by UI):
  MATCH (d:Document)-[:IS_A]->(t:DocType)-[:IN_CATEGORY]->(c:DocCategory {name:$category})
  RETURN d.id AS id, coalesce(d.title,'') AS title LIMIT 100

## Notes & recommendations
- The model is well-normalized with ChangeOrder as the hub for entitlement/precedent analysis.
- Keep the Chunk embedding index and ensure the vector/semantic pipeline updates embeddings when chunks change.
- Ensure the CA/TLS certs are trusted when connecting to cloud Neo4j instances (avoid disabling verification in production).
- Add small helper indexes if queries show hotspots (e.g., Document.title text index for search).

---
