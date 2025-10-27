CREATE RANGE INDEX FOR (n:ChangeOrder) ON (n.reason);
CREATE RANGE INDEX FOR (n:ChangeOrder) ON (n.status);
CREATE RANGE INDEX FOR (n:Spec) ON (n.section);
CREATE RANGE INDEX FOR (n:Vendor) ON (n.name);
CREATE CONSTRAINT activity_id FOR (node:Activity) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT allow_id FOR (node:Allowance) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT ar_id FOR (node:AnalysisRun) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT chunk_id FOR (node:Chunk) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT co_id FOR (node:ChangeOrder) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT cont_id FOR (node:Contingency) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT contract_id FOR (node:Contract) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT costitem_id FOR (node:CostItem) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT db_id FOR (node:DesignBasis) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT document_id FOR (node:Document) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT drawing_id FOR (node:Drawing) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT ev_id FOR (node:Evidence) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT fd_id FOR (node:FieldDirective) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT keyword_text FOR (node:Keyword) REQUIRE (node.text) IS UNIQUE;
CREATE CONSTRAINT met_id FOR (node:Metric) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT mm_id FOR (node:MeetingMinutes) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT pco_id FOR (node:PotentialCO) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT person_id FOR (node:Person) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT project_id FOR (node:Project) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT rec_id FOR (node:Recommendation) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT rfi_id FOR (node:RFI) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT schedule_id FOR (node:Schedule) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT scn_id FOR (node:Scenario) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT spec_id FOR (node:Spec) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT submittal_id FOR (node:Submittal) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT system_id FOR (node:System) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT term_name FOR (node:Term) REQUIRE (node.name) IS UNIQUE;
CREATE CONSTRAINT upi_id FOR (node:UnitPriceItem) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT vendor_id FOR (node:Vendor) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT wbs_code FOR (node:WBS) REQUIRE (node.code) IS UNIQUE;
CREATE CONSTRAINT workarea_id FOR (node:WorkArea) REQUIRE (node.id) IS UNIQUE;
CREATE CONSTRAINT UNIQUE_IMPORT_NAME FOR (node:`UNIQUE IMPORT LABEL`) REQUIRE (node.`UNIQUE IMPORT ID`) IS UNIQUE;
UNWIND [{id:"UPI-Firestop-LF", properties:{unit:"LF", rate:12.5, name:"Firestopping per linear foot"}}] AS row
CREATE (n:UnitPriceItem{id: row.id}) SET n += row.properties;
UNWIND [{id:"EV-CO042-SPEC", properties:{reason:"Contract Exclusion for modular systems", confidence:0.85, supports:"OutOfScope"}}, {id:"EV-CO042-RFI", properties:{reason:"Owner directive to use UL-listed systems", confidence:0.75, supports:"OutOfScope"}}] AS row
CREATE (n:Evidence{id: row.id}) SET n += row.properties;
UNWIND [{id:"SUB-001", properties:{title:"Firestopping Test Reports (ASTM E2174)", required:true}}] AS row
CREATE (n:Submittal{id: row.id}) SET n += row.properties;
UNWIND [{id:"ALLOW-Firestopping", properties:{amount:15000.0, name:"Firestopping Allowance", basis:"Lump Sum"}}] AS row
CREATE (n:Allowance{id: row.id}) SET n += row.properties;
UNWIND [{id:"PCO-001", properties:{createdAt:datetime('2025-10-23T00:22:18.314Z'), name:"Field discovery: new modular wall penetrations"}}] AS row
CREATE (n:PotentialCO{id: row.id}) SET n += row.properties;
UNWIND [{id:"RFI-123", properties:{number:"123", question:"Firestopping rating at modular wall penetrations?", answer:"Use UL-listed systems at all new penetrations", status:"Answered"}}] AS row
CREATE (n:RFI{id: row.id}) SET n += row.properties;
UNWIND [{id:"ACT-FIRESTOP", properties:{durationDays:5, code:"A-FS-01", name:"Install Firestopping", isCritical:true}}] AS row
CREATE (n:Activity{id: row.id}) SET n += row.properties;
UNWIND [{name:"Firestopping", properties:{definition:"Systems maintaining fire-resistance where penetrations occur."}}, {name:"UL-listed", properties:{definition:"Certified by Underwriters Laboratories."}}] AS row
CREATE (n:Term{name: row.name}) SET n += row.properties;
UNWIND [{id:"SYS-ModularWall", properties:{name:"Modular Wall Assembly", discipline:"Architectural"}}] AS row
CREATE (n:System{id: row.id}) SET n += row.properties;
UNWIND [{id:"CONT-Owner", properties:{name:"Owner Contingency", percent:5.0}}] AS row
CREATE (n:Contingency{id: row.id}) SET n += row.properties;
UNWIND [{id:"CT-001.pdf", properties:{issuedDate:date('2025-10-01'), sourceSystem:"Box", source:"Box:/contracts/CT-001.pdf", type:"Contract", revision:"Rev-1"}}, {id:"SPEC-07-21-00.pdf", properties:{issuedDate:date('2025-10-01'), sourceSystem:"Box", source:"Box:/specs/SPEC-07-21-00.pdf", type:"Spec", revision:"Rev-1"}}, {id:"CO-042.pdf", properties:{issuedDate:date('2025-10-01'), sourceSystem:"Box", source:"Box:/CO/CO-042.pdf", type:"CO", revision:"Rev-1"}}, {id:"RFI-123.pdf", properties:{issuedDate:date('2025-10-01'), sourceSystem:"Box", source:"Box:/rfis/RFI-123.pdf", type:"RFI", revision:"Rev-1"}}, {id:"DB-CO042-Firestopping.pdf", properties:{source:"Box:/design-basis/DB-CO042-Firestopping.pdf", type:"DesignBasis", revision:"Rev-1"}}] AS row
CREATE (n:Document{id: row.id}) SET n += row.properties;
UNWIND [{id:"DRW-A101", properties:{sheet:"A-101", title:"Level 1 Plan – Walls & Details"}}] AS row
CREATE (n:Drawing{id: row.id}) SET n += row.properties;
UNWIND [{id:"WA-L1-OpenOffice", properties:{name:"Level 1 – Open Office", floor:"L1"}}] AS row
CREATE (n:WorkArea{id: row.id}) SET n += row.properties;
UNWIND [{id:"MET-AR-CO042-001", properties:{coverage:0.9, precedentScore:0.75, clarity:0.8, consistency:0.85}}] AS row
CREATE (n:Metric{id: row.id}) SET n += row.properties;
UNWIND [{id:"DB-CO042-Firestopping", properties:{issuedDate:date('2025-10-01'), notes:"UL-listed systems required at all new modular wall penetrations; follow Spec 07 21 00", name:"Design Basis — Firestopping for Modular Wall Penetrations", version:"v1"}}] AS row
CREATE (n:DesignBasis{id: row.id}) SET n += row.properties;
UNWIND [{id:"P-KEVIN", properties:{role:"Project Director", name:"Kevin"}}, {id:"P-ANITA", properties:{role:"Contracts Lead", name:"Anita"}}, {id:"P-RAVI", properties:{role:"Project Engineer", name:"Ravi"}}] AS row
CREATE (n:Person{id: row.id}) SET n += row.properties;
UNWIND [{id:"CT-001", properties:{number:"CT-001", title:"Prime Contract – Building 100"}}] AS row
CREATE (n:Contract{id: row.id}) SET n += row.properties;
UNWIND [{id:"SPEC-07-21-00", properties:{division:"07", section:"07 21 00", title:"Thermal Insulation and Firestopping"}}, {id:"SPEC-09-90-00", properties:{division:"09", section:"09 90 00", title:"Painting"}}] AS row
CREATE (n:Spec{id: row.id}) SET n += row.properties;
UNWIND [{id:"PARAGON-100", properties:{name:"Paragon / Building 100"}}] AS row
CREATE (n:Project{id: row.id}) SET n += row.properties;
UNWIND [{code:"07.21.00", properties:{name:"Firestopping"}}, {code:"09.90.00", properties:{name:"Painting"}}] AS row
CREATE (n:WBS{code: row.code}) SET n += row.properties;
UNWIND [{id:"SCH-BASE", properties:{version:"Baseline v1"}}] AS row
CREATE (n:Schedule{id: row.id}) SET n += row.properties;
UNWIND [{_id:11, properties:{}}, {_id:16, properties:{}}, {_id:17, properties:{}}, {_id:18, properties:{}}, {_id:19, properties:{}}, {_id:20, properties:{}}, {_id:21, properties:{}}, {_id:22, properties:{}}, {_id:27, properties:{}}, {_id:28, properties:{}}, {_id:35, properties:{}}, {_id:36, properties:{}}, {_id:40, properties:{}}, {_id:42, properties:{}}, {_id:47, properties:{}}, {_id:52, properties:{}}, {_id:53, properties:{}}, {_id:54, properties:{}}, {_id:55, properties:{}}] AS row
CREATE (n:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row._id}) SET n += row.properties;
UNWIND [{id:"CO-042", properties:{reason:"Owner-Directed", number:"CO-042", createdAt:datetime('2025-10-18T10:00:00Z'), title:"Add UL-listed firestopping at new modular wall penetrations", status:"Pending Exec Approval"}}, {id:"CO-017", properties:{reason:"Owner-Directed", number:"CO-017", createdAt:datetime('2025-08-12T10:00:00Z'), title:"Additional firestopping at lab risers", status:"Approved"}}, {id:"CO-029", properties:{reason:"Design Omission", number:"CO-029", createdAt:datetime('2025-09-10T10:00:00Z'), title:"Sealant/firestop upgrade near corridor", status:"Approved"}}] AS row
CREATE (n:ChangeOrder{id: row.id}) SET n += row.properties;
UNWIND [{id:"AR-CO042-001", properties:{determination:"Not Entitled", confidence_overall:0.83, timestamp:datetime('2025-10-20T09:00:00Z')}}] AS row
CREATE (n:AnalysisRun{id: row.id}) SET n += row.properties;
UNWIND [{id:"MM-2025-10-10", properties:{date:date('2025-10-10'), title:"Coordination – penetrations & firestopping"}}] AS row
CREATE (n:MeetingMinutes{id: row.id}) SET n += row.properties;
UNWIND [{id:"V-ACME", properties:{name:"ACME Fire Protection"}}] AS row
CREATE (n:Vendor{id: row.id}) SET n += row.properties;
UNWIND [{id:"SCN-CO042-Base", properties:{name:"Base Case", assumption:"New modular wall penetrations not in base drawings"}}] AS row
CREATE (n:Scenario{id: row.id}) SET n += row.properties;
UNWIND [{id:"REC-CO042-001", properties:{reason:"Contract Exclusion + Owner directive + no baseline scope coverage", action:"Convert to Change Order (Owner-funded)"}}] AS row
CREATE (n:Recommendation{id: row.id}) SET n += row.properties;
UNWIND [{id:"CT-001#SOW", properties:{section:"SOW", text:"Scope limited to items shown in base drawings. Penetrations added after bid are excluded unless noted.", embedding:[0.11, 0.02, 0.03, 0.4, 0.12, 0.08, 0.05, 0.21], page:5}}, {id:"CT-001#EXCLUSIONS", properties:{section:"Exclusions", text:"Excludes firestopping for new modular systems not indicated on base drawings.", embedding:[0.1, 0.01, 0.05, 0.39, 0.11, 0.1, 0.06, 0.2], page:14}}, {id:"SPEC-07-21-00#§3.2", properties:{section:"3.2", text:"Provide UL-listed firestopping at all penetrations through fire-rated assemblies.", embedding:[0.05, 0.33, 0.44, 0.02, 0.12, 0.17, 0.09, 0.03], page:12}}, {id:"SPEC-07-21-00#§3.3", properties:{section:"3.3", text:"Inspection and testing per ASTM E2174; submit testing reports to Owner.", embedding:[0.04, 0.3, 0.41, 0.02, 0.11, 0.16, 0.08, 0.03], page:13}}, {id:"CO-042#Scope", properties:{section:"Scope", text:"Add UL-listed firestopping per Spec 07 21 00 §3.2 at new modular wall penetrations.", embedding:[0.06, 0.31, 0.4, 0.03, 0.13, 0.15, 0.09, 0.04], page:2}}, {id:"RFI-123#Answer", properties:{section:"Answer", text:"Owner directs use of UL-listed systems for all new penetrations in modular walls.", embedding:[0.07, 0.29, 0.39, 0.04, 0.14, 0.14, 0.08, 0.05], page:2}}, {id:"DB-CO042#UL-Requirement", properties:{section:"UL-Requirement", text:"Provide UL-listed firestopping systems for all new penetrations at modular wall assemblies.", page:1}}] AS row
CREATE (n:Chunk{id: row.id}) SET n += row.properties;
UNWIND [{id:"FD-2025-10-12", properties:{date:date('2025-10-12'), note:"Proceed with modular wall penetrations; firestopping to follow"}}] AS row
CREATE (n:FieldDirective{id: row.id}) SET n += row.properties;
UNWIND [{id:"CI-042-1", properties:{amount:32000, code:"07.21.00", type:"Labor"}}, {id:"CI-042-2", properties:{amount:18000, code:"07.21.00", type:"Material"}}] AS row
CREATE (n:CostItem{id: row.id}) SET n += row.properties;
UNWIND [{text:"firestopping", properties:{}}, {text:"ul-listed", properties:{}}] AS row
CREATE (n:Keyword{text: row.text}) SET n += row.properties;
UNWIND [{start: {id:"AR-CO042-001"}, end: {id:"EV-CO042-SPEC"}, properties:{}}, {start: {id:"AR-CO042-001"}, end: {id:"EV-CO042-RFI"}, properties:{}}] AS row
MATCH (start:AnalysisRun{id: row.start.id})
MATCH (end:Evidence{id: row.end.id})
CREATE (start)-[r:USES_EVIDENCE]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"ALLOW-Firestopping"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Allowance{id: row.end.id})
CREATE (start)-[r:COVERED_BY]->(end) SET r += row.properties;
UNWIND [{start: {id:"CT-001"}, end: {id:"CT-001.pdf"}, properties:{}}] AS row
MATCH (start:Contract{id: row.start.id})
MATCH (end:Document{id: row.end.id})
CREATE (start)-[r:HAS_DOCUMENT]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"SCN-CO042-Base"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Scenario{id: row.end.id})
CREATE (start)-[r:HAS_SCENARIO]->(end) SET r += row.properties;
UNWIND [{start: {id:"PARAGON-100"}, end: {id:"CT-001"}, properties:{}}] AS row
MATCH (start:Project{id: row.start.id})
MATCH (end:Contract{id: row.end.id})
CREATE (start)-[r:HAS_CONTRACT]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"CI-042-1"}, properties:{}}, {start: {id:"CO-042"}, end: {id:"CI-042-2"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:CostItem{id: row.end.id})
CREATE (start)-[r:HAS_COST_ITEM]->(end) SET r += row.properties;
UNWIND [{start: {_id:28}, end: {id:"DRW-A101"}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:Drawing{id: row.end.id})
CREATE (start)-[r:ADDRESSES]->(end) SET r += row.properties;
UNWIND [{start: {_id:36}, end: {_id:36}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:NEXT]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042#Scope"}, end: {id:"SPEC-07-21-00#§3.2"}, properties:{}}, {start: {id:"CO-042#Scope"}, end: {id:"RFI-123#Answer"}, properties:{}}] AS row
MATCH (start:Chunk{id: row.start.id})
MATCH (end:Chunk{id: row.end.id})
CREATE (start)-[r:CITES]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"SUB-001"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Submittal{id: row.end.id})
CREATE (start)-[r:REFERS_TO]->(end) SET r += row.properties;
UNWIND [{start: {id:"CT-001.pdf"}, end: {id:"CT-001#SOW"}, properties:{}}, {start: {id:"CT-001.pdf"}, end: {id:"CT-001#EXCLUSIONS"}, properties:{}}, {start: {id:"SPEC-07-21-00.pdf"}, end: {id:"SPEC-07-21-00#§3.2"}, properties:{}}, {start: {id:"CO-042.pdf"}, end: {id:"CO-042#Scope"}, properties:{}}, {start: {id:"RFI-123.pdf"}, end: {id:"RFI-123#Answer"}, properties:{}}, {start: {id:"DB-CO042-Firestopping.pdf"}, end: {id:"DB-CO042#UL-Requirement"}, properties:{}}] AS row
MATCH (start:Document{id: row.start.id})
MATCH (end:Chunk{id: row.end.id})
CREATE (start)-[r:HAS_CHUNK]->(end) SET r += row.properties;
UNWIND [{start: {id:"AR-CO042-001"}, end: {id:"REC-CO042-001"}, properties:{}}] AS row
MATCH (start:AnalysisRun{id: row.start.id})
MATCH (end:Recommendation{id: row.end.id})
CREATE (start)-[r:RECOMMENDS]->(end) SET r += row.properties;
UNWIND [{start: {id:"MM-2025-10-10"}, end: {id:"SYS-ModularWall"}, properties:{}}] AS row
MATCH (start:MeetingMinutes{id: row.start.id})
MATCH (end:System{id: row.end.id})
CREATE (start)-[r:MENTIONS]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"WA-L1-OpenOffice"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:WorkArea{id: row.end.id})
CREATE (start)-[r:AFFECTS]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"EV-CO042-SPEC"}, properties:{}}, {start: {id:"CO-042"}, end: {id:"EV-CO042-RFI"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Evidence{id: row.end.id})
CREATE (start)-[r:HAS_EVIDENCE]->(end) SET r += row.properties;
UNWIND [{start: {_id:47}, end: {text:"firestopping"}, properties:{}}, {start: {_id:47}, end: {text:"ul-listed"}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:Keyword{text: row.end.text})
CREATE (start)-[r:HAS_KEYWORD]->(end) SET r += row.properties;
UNWIND [{start: {id:"RFI-123"}, end: {id:"DRW-A101"}, properties:{}}] AS row
MATCH (start:RFI{id: row.start.id})
MATCH (end:Drawing{id: row.end.id})
CREATE (start)-[r:ADDRESSES]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"SYS-ModularWall"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:System{id: row.end.id})
CREATE (start)-[r:MODIFIES]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"ACT-FIRESTOP"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Activity{id: row.end.id})
CREATE (start)-[r:IMPACTS]->(end) SET r += row.properties;
UNWIND [{start: {id:"MM-2025-10-10"}, end: {id:"WA-L1-OpenOffice"}, properties:{}}] AS row
MATCH (start:MeetingMinutes{id: row.start.id})
MATCH (end:WorkArea{id: row.end.id})
CREATE (start)-[r:MENTIONS]->(end) SET r += row.properties;
UNWIND [{start: {_id:52}, end: {_id:53}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:AFFECTS]->(end) SET r += row.properties;
UNWIND [{start: {id:"SPEC-07-21-00#§3.2"}, end: {name:"Firestopping"}, properties:{}}, {start: {id:"CO-042#Scope"}, end: {name:"Firestopping"}, properties:{}}, {start: {id:"RFI-123#Answer"}, end: {name:"Firestopping"}, properties:{}}] AS row
MATCH (start:Chunk{id: row.start.id})
MATCH (end:Term{name: row.end.name})
CREATE (start)-[r:HAS_TERM]->(end) SET r += row.properties;
UNWIND [{start: {id:"DB-CO042-Firestopping"}, end: {id:"SPEC-07-21-00"}, properties:{}}] AS row
MATCH (start:DesignBasis{id: row.start.id})
MATCH (end:Spec{id: row.end.id})
CREATE (start)-[r:SETS_REQUIREMENT_FOR]->(end) SET r += row.properties;
UNWIND [{start: {id:"CT-001"}, end: {id:"CO-042"}, properties:{}}] AS row
MATCH (start:Contract{id: row.start.id})
MATCH (end:ChangeOrder{id: row.end.id})
CREATE (start)-[r:HAS_CO]->(end) SET r += row.properties;
UNWIND [{start: {_id:36}, end: {_id:40}, properties:{}}, {start: {_id:42}, end: {_id:36}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:CITES]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"RFI-123"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:RFI{id: row.end.id})
CREATE (start)-[r:REFERS_TO]->(end) SET r += row.properties;
UNWIND [{start: {id:"PCO-001"}, end: {id:"CO-042"}, properties:{}}] AS row
MATCH (start:PotentialCO{id: row.start.id})
MATCH (end:ChangeOrder{id: row.end.id})
CREATE (start)-[r:EVOLVES_TO]->(end) SET r += row.properties;
UNWIND [{start: {_id:47}, end: {name:"Firestopping"}, properties:{}}, {start: {_id:47}, end: {name:"UL-listed"}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:Term{name: row.end.name})
CREATE (start)-[r:HAS_TERM]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"DB-CO042-Firestopping"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:DesignBasis{id: row.end.id})
CREATE (start)-[r:REFERS_TO]->(end) SET r += row.properties;
UNWIND [{start: {id:"FD-2025-10-12"}, end: {id:"PCO-001"}, properties:{}}] AS row
MATCH (start:FieldDirective{id: row.start.id})
MATCH (end:PotentialCO{id: row.end.id})
CREATE (start)-[r:TRIGGERS]->(end) SET r += row.properties;
UNWIND [{start: {id:"CI-042-1"}, end: {_id:21}, properties:{}}, {start: {id:"CI-042-1"}, end: {_id:22}, properties:{}}, {start: {id:"CI-042-2"}, end: {_id:21}, properties:{}}, {start: {id:"CI-042-2"}, end: {_id:22}, properties:{}}] AS row
MATCH (start:CostItem{id: row.start.id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:CODED_AS]->(end) SET r += row.properties;
UNWIND [{start: {id:"EV-CO042-SPEC"}, end: {id:"SPEC-07-21-00#§3.2"}, properties:{}}, {start: {id:"EV-CO042-RFI"}, end: {id:"RFI-123#Answer"}, properties:{}}] AS row
MATCH (start:Evidence{id: row.start.id})
MATCH (end:Chunk{id: row.end.id})
CREATE (start)-[r:EVIDENCE_FROM]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"V-ACME"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Vendor{id: row.end.id})
CREATE (start)-[r:PARTY_TO]->(end) SET r += row.properties;
UNWIND [{start: {id:"ACT-FIRESTOP"}, end: {id:"SCH-BASE"}, properties:{}}] AS row
MATCH (start:Activity{id: row.start.id})
MATCH (end:Schedule{id: row.end.id})
CREATE (start)-[r:BELONGS_TO]->(end) SET r += row.properties;
UNWIND [{start: {id:"DB-CO042-Firestopping"}, end: {id:"DB-CO042-Firestopping.pdf"}, properties:{}}] AS row
MATCH (start:DesignBasis{id: row.start.id})
MATCH (end:Document{id: row.end.id})
CREATE (start)-[r:HAS_DOCUMENT]->(end) SET r += row.properties;
UNWIND [{start: {_id:28}, end: {_id:28}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:ADDRESSES]->(end) SET r += row.properties;
UNWIND [{start: {id:"SPEC-07-21-00#§3.2"}, end: {text:"ul-listed"}, properties:{}}] AS row
MATCH (start:Chunk{id: row.start.id})
MATCH (end:Keyword{text: row.end.text})
CREATE (start)-[r:HAS_KEYWORD]->(end) SET r += row.properties;
UNWIND [{start: {_id:27}, end: {_id:28}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:REFERS_TO]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"SPEC-07-21-00"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Spec{id: row.end.id})
CREATE (start)-[r:REFERS_TO]->(end) SET r += row.properties;
UNWIND [{start: {_id:35}, end: {_id:36}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:HAS_CHUNK]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-017"}, end: {_id:19}, properties:{}}, {start: {id:"CO-029"}, end: {_id:20}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:PARTY_TO]->(end) SET r += row.properties;
UNWIND [{start: {_id:16}, end: {id:"ACT-FIRESTOP"}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:Activity{id: row.end.id})
CREATE (start)-[r:IMPACTS]->(end) SET r += row.properties;
UNWIND [{start: {_id:54}, end: {_id:55}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:MODIFIES]->(end) SET r += row.properties;
UNWIND [{start: {id:"DRW-A101"}, end: {id:"WA-L1-OpenOffice"}, properties:{}}] AS row
MATCH (start:Drawing{id: row.start.id})
MATCH (end:WorkArea{id: row.end.id})
CREATE (start)-[r:SHOWS]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"AR-CO042-001"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:AnalysisRun{id: row.end.id})
CREATE (start)-[r:HAS_ANALYSIS]->(end) SET r += row.properties;
UNWIND [{start: {id:"AR-CO042-001"}, end: {id:"MET-AR-CO042-001"}, properties:{}}] AS row
MATCH (start:AnalysisRun{id: row.start.id})
MATCH (end:Metric{id: row.end.id})
CREATE (start)-[r:HAS_METRIC]->(end) SET r += row.properties;
UNWIND [{start: {id:"CI-042-1"}, end: {code:"07.21.00"}, properties:{}}, {start: {id:"CI-042-2"}, end: {code:"07.21.00"}, properties:{}}] AS row
MATCH (start:CostItem{id: row.start.id})
MATCH (end:WBS{code: row.end.code})
CREATE (start)-[r:CODED_AS]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-042"}, end: {id:"P-KEVIN"}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:Person{id: row.end.id})
CREATE (start)-[r:REQUESTED_BY]->(end) SET r += row.properties;
UNWIND [{start: {id:"CT-001"}, end: {id:"UPI-Firestop-LF"}, properties:{}}] AS row
MATCH (start:Contract{id: row.start.id})
MATCH (end:UnitPriceItem{id: row.end.id})
CREATE (start)-[r:HAS_UNIT_PRICE]->(end) SET r += row.properties;
UNWIND [{start: {_id:11}, end: {id:"CO-042"}, properties:{}}, {start: {_id:11}, end: {id:"CO-017"}, properties:{}}, {start: {_id:11}, end: {id:"CO-029"}, properties:{}}] AS row
MATCH (start:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.start._id})
MATCH (end:ChangeOrder{id: row.end.id})
CREATE (start)-[r:HAS_CO]->(end) SET r += row.properties;
UNWIND [{start: {id:"CT-001"}, end: {id:"ALLOW-Firestopping"}, properties:{}}] AS row
MATCH (start:Contract{id: row.start.id})
MATCH (end:Allowance{id: row.end.id})
CREATE (start)-[r:HAS_ALLOWANCE]->(end) SET r += row.properties;
UNWIND [{start: {id:"CO-017"}, end: {_id:17}, properties:{}}, {start: {id:"CO-029"}, end: {_id:18}, properties:{}}] AS row
MATCH (start:ChangeOrder{id: row.start.id})
MATCH (end:`UNIQUE IMPORT LABEL`{`UNIQUE IMPORT ID`: row.end._id})
CREATE (start)-[r:REQUESTED_BY]->(end) SET r += row.properties;
UNWIND [{start: {id:"CT-001"}, end: {id:"CONT-Owner"}, properties:{}}] AS row
MATCH (start:Contract{id: row.start.id})
MATCH (end:Contingency{id: row.end.id})
CREATE (start)-[r:HAS_CONTINGENCY]->(end) SET r += row.properties;
UNWIND [{start: {id:"DB-CO042-Firestopping"}, end: {id:"SYS-ModularWall"}, properties:{}}] AS row
MATCH (start:DesignBasis{id: row.start.id})
MATCH (end:System{id: row.end.id})
CREATE (start)-[r:DEFINES_CRITERIA_FOR]->(end) SET r += row.properties;
UNWIND [{start: {id:"RFI-123"}, end: {id:"SPEC-07-21-00"}, properties:{}}] AS row
MATCH (start:RFI{id: row.start.id})
MATCH (end:Spec{id: row.end.id})
CREATE (start)-[r:ADDRESSES]->(end) SET r += row.properties;
MATCH (n:`UNIQUE IMPORT LABEL`)  WITH n LIMIT 20000 REMOVE n:`UNIQUE IMPORT LABEL` REMOVE n.`UNIQUE IMPORT ID`;
DROP CONSTRAINT UNIQUE_IMPORT_NAME;