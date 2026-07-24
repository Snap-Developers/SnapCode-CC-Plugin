# SnapLogic Programming Model — Practical Guide for Humans & LLMs
_Last verified: 2025‑09‑17_

> **Scope:** Core programming model only. This guide **does not** cover pipeline modes (Ultra, Triggered, ELT) or Agents. It focuses on **Snaps, Pipelines, the Expression Language, Expression Libraries**, native data types, and the **transformation/connector Snap Packs** relevant to ETL.

---

## 1) The Programming Model

### 1.1 Pipelines (the “program”)
A **Pipeline** is a directed flow of steps that read → transform → write data. Each step is a **Snap**. Pipelines are built visually in Designer by connecting Snaps in sequence or branches. Error paths can be attached to most Snaps to route failures without stopping the run.

*Official:* [Snaps reference](https://docs.snaplogic.com/snaps/snaps-about.html)

### 1.2 Snaps (the “operators”)
A **Snap** performs one function—read, write, transform, route, call an API, etc.—and is provided in **Snap Packs** (bundles). You configure a Snap’s settings and, where supported, add **expressions** to compute values at runtime.

*Official:* [Snap Packs (overview)](https://docs.snaplogic.com/snaps/snap-packs.html)

### 1.3 Native data types & views (Document vs Binary)
Data flows through Snaps as either:
- **Document** streams: structured, JSON-like objects used by most transformation Snaps.
- **Binary** streams: raw bytes used for files/media and for formatters/parsers.

You can **convert** between them with **Binary to Document** and **Document to Binary** Snaps when you need to switch modes (for example, parse a CSV file into JSON documents, or serialize JSON back to a file). In Designer, connection **shapes** and Snap **Views** indicate Document vs Binary streams, and many Snaps let you choose which view to use.
- Binary→Document: [Binary to Document](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438465/Binary%2Bto%2BDocument)
- Document→Binary: [Document to Binary](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438976/Document%2Bto%2BBinary)
- Views & connections: [Connecting Snaps (shapes, views)](https://docs.snaplogic.com/snaps/snaps-connecting-snaps.html)

### 1.4 The SnapLogic Expression Language (EL)
The **Expression Language** is available on “expression-enabled” fields (toggle with the `=` icon). It uses **JavaScript‑like syntax** with targeted capabilities and intentional restrictions:
- **Supported**: arithmetic, logical operators, ternary, spread, array/object helpers, date/time, base64, JSON helpers, etc.
- **Access document values** with `$` (for example, `$customer.name`, `$items[0]`).
- **Unsupported** (by design): variable assignment, `+=`, `++/--`, `===/!==` strict equality, etc.

**Essential references**
- Overview & operators: [Expression Language](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438042/Expression%2BLanguage%2BOverview)
- Examples & function catalogs: follow the **Using Expressions**, **JSONPath**, **String/Date/Array/Object** sections from the left nav on the page above.

**Mini examples**
```text
// Filter only adult customers
$age > 17

// Compute full name safely
($.first_name || '') + ' ' + ($.last_name || '')

// Map an array of amounts to USD cents
$amounts.map(x => parseInt(x * 100))
```

### 1.5 Expression Libraries (ELib)
An **Expression Library** is a project file (`.expr`) that exposes **reusable functions/constants** to pipelines via the `lib` global. Think of it as a **specialized, limited JS object literal** evaluated at run start—**not** a full JS module (no statements, no assignment at runtime). Write arrow‑function helpers and constants, then reference them from any Snap’s expression fields.

- Docs & examples: [Expression Libraries](https://docs-snaplogic.atlassian.net/wiki/x/nvEV)

**What to remember**
- Library content is evaluated once and exposed as `lib.<name>`; values are **static** for a run.
- Use object literals + arrow functions; reference other helpers via `this` inside the object.
- Good for date helpers, lookups, cleansing utilities, common calculations.

**Mini example (`helpers.expr`)**

> **WARNING:** `this.fn()` cross-references silently return null in `slpy exec`. Inline all logic per function.

```js
{
  iso: 'yyyy-MM-dd',

  to_ymd: d => (d || Date.now()).toString("yyyy-MM-dd"),

  prev_month_start_string: x => (x || Date.now()).minusMonths(1).withDayOfMonth(1).toString("yyyy-MM-dd"),
  prev_month_end_string:   x => (x || Date.now()).withDayOfMonth(1).minusSeconds(1).toString("yyyy-MM-dd")
}
```

Use from a Mapper target expression: `lib.helpers.prev_month_start_string()`.

---

## 2) Snap Packs by Category (with links)

Snap Packs are grouped into **Core**, **Data**, and **Enterprise** families. Below are the most relevant packs for ETL and their notable Snaps.

> Tip: The **Core** packs include the transformation and utility Snaps that everyone uses. **Data** packs cover databases, streaming, and data platforms. **Enterprise** packs cover SaaS/ERP/CRM and business systems.

### 2.1 Core Snaps (full lists)
Official index: [Core Snaps](https://docs-snaplogic.com/snaps/snaps-core/snaps-core-about.html)  
Legacy index (with enumerated items): [Core Snaps (Confluence)](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps)

#### Flow Snap Pack
[Flow Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Flow-Snap-Pack) — control and routing:
- **Copy**, **Binary Copy**, **Router**, **HTTP Router**, **Filter**, **Union**, **Gate**, **Head**, **Tail**, **Exit**, **Pipeline Execute**, **PipeLoop**; (deprecated: **ForEach**, **Task Execute**).

#### Transform Snap Pack
[Transform Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438327/Transform%2BSnap%2BPack) — conversions & reshaping (highlights):
- **Aggregate**, **Sort**, **Join**, **Pivot**, **Unique**, **Diff**, **Conditional**, **Sequence**, **In‑Memory Lookup**, **Structure**.
- **Mapper** (map/derive fields), **JSON/CSV/XML/Avro/Parquet Parser & Formatter**, **Excel Parser / (Multi‑Sheet) Formatter**.
- **Binary to Document**, **Document to Binary**, **Transcoder**.
- **Encrypt Field / Decrypt Field**, **Record Replay**.

(See the full Transform list + history for all members and new additions like **Parquet Parser/Formatter**, **GeoJSON Parser**, **WKT Parser**.)  
Docs: [Transform pack overview](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438327/Transform%2BSnap%2BPack), [Join](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-join.html), [Mapper](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-mapper.html), [CSV Parser](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-csv-parser.html), [JSON Formatter](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-json-formatter.html).

#### Binary Snap Pack
[Binary Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Binary-Snap-Pack) — file I/O, encryption, compression:
- **File Reader/Writer**, **Directory Browser**, **File Operation/Delete/Poller**, **Multi File Reader**, **Multipart Reader/Writer**, **ZipFile Read/Write**.
- **S3 File Reader/Writer**, **SAS Generator**.
- Crypto: **AES/Twofish/Blowfish Encrypt/Decrypt**, **PGP Encrypt/Decrypt/Sign**.
- **Compress/Decompress**.

#### Amazon S3 Snap Pack
[Amazon S3 Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Amazon-S3-Snap-Pack) — **S3 Browser, Copy, Delete, Download, Poller, Presigned, Restore, Select, Upload, Archive**.

#### API & protocol packs
- **API Suite** (prefer for REST/HTTP): [API Suite Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#API-Suite-Snap-Pack) — **HTTP Client**, **GraphQL Client**, **gRPC Client**.
- **OpenAPI**: [OpenAPI Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#OpenAPI-Snap-Pack) — import OpenAPI definitions.
- **SOAP**: [SOAP Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438425/SOAP%2BSnap%2BPack) — **SOAP Execute**.
- **REST (legacy)**: [REST Snap Pack (not recommended)](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#REST-Snap-Pack-[Not-Recommended]).

#### JDBC Snap Pack (universal DB connector)
[JDBC Snap Pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438072/JDBC%2BSnap%2BPack) — **Generic JDBC Execute/Select/Insert/Update**, **Schema List**, **Table List**.

#### Scripting, metadata, mail
- **Script Snap Pack**: [Script pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Script-Snap-Pack) — **Execute Script**, **Script**, **PySpark**.
- **Data Catalog Snap Pack**: [Catalog pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Data-Catalog-Snap-Pack) — **Catalog Insert/Query/Delete**, **Data Catalog Services**.
- **Email Snap Pack**: [Email pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Email-Snap-Pack) — **Email Reader/Sender/Archive/Delete**.
- **JWT**: [JWT pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#JWT-Snap-Pack) — **JWT Generate/Validate**.

---

### 2.2 Data Snaps (databases, warehouses, big data, streaming)
Official index: [Data Snaps](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439327/Data%2BSnaps)

**Relational / Cloud DW**
- **Snowflake** ([pack](https://docs.snaplogic.com/snaps/snaps-data/sp-snowflake/sp-snowflake-about.html)), **Amazon Redshift**, **Google BigQuery**, **Azure Synapse SQL**, **Azure SQL Database**, **Oracle**, **PostgreSQL**, **SQL Server**, **MySQL**, **Teradata**, **Vertica**, **SAP HANA**.

**NoSQL / Big Data / Streaming**
- **MongoDB**, **Cassandra**, **Hadoop (HDFS)**, **Hive**, **Kafka**, **DynamoDB**.

(Use **JDBC** where a direct pack is unavailable.)

---

### 2.3 Enterprise Snaps (SaaS/ERP/CRM & services)
Official index: [Enterprise Snaps](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439296/Enterprise%2BSnaps)

**Major application packs for ETL**
- **Salesforce** ([pack & Snaps](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438704/Salesforce%2BSnap%2BPack): SOQL/SOSL/Read/Create/Update/Upsert/Bulk, Platform Events).
- **Workday** ([pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438832/Workday%2BSnap%2BPack), [Workday REST](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/2647556240/Workday%2BREST)).
- **NetSuite** ([SOAP pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438933/NetSuite%2BSnap%2BPack), [REST pack](https://docs.snaplogic.com/snaps/snaps-enterprise/sp-netsuite-rest/snap-netsuite-rest-update.html)).
- **ServiceNow**, **SAP (ERP/S/4HANA/SuccessFactors/Concur/HANA)**, **Oracle HCM**.
- **Microsoft**: **Dynamics 365 (Sales/Finance/SCM/Business Central)**, **SharePoint Online**, **Teams**, **Power BI**, **Exchange** (legacy), **Entra ID (Azure AD)**, **OneDrive**.
- **Google**: **Sheets**, **Cloud Pub/Sub**, **Directory**.
- **Messaging/Queues**: **Amazon SNS**, **Azure Service Bus**, **RabbitMQ**.
- **Commerce & others**: **Shopify**, **Zuora**, **Coupa**, **JMS**, **Xactly**, **Jira**, **HubSpot**, **Slack**.

Each pack exposes purpose‑specific Snaps (for example, *Salesforce SOQL*, *Workday Write*, *NetSuite Search/Update*). See the Enterprise index for the complete A‑Z list and subpages.

---

## 3) What Flows Between Snaps (quick mental model)

| Concept | Document view | Binary view |
|---|---|---|
| **What is it?** | Structured JSON-like records used by Mappers, Joins, Aggregations | Raw bytes (files/media/streams) used by File/Cloud storage and by formatters/parsers |
| **When to use** | Schema‑oriented transforms, filtering, aggregations, joins, API payloads | File I/O, pass‑through payloads, format conversion (CSV/JSON/XML/Avro/Parquet) |
| **Typical bridge Snaps** | — | **Document to Binary** (serialize), **JSON/CSV/XML Formatter** |
| **Typical bridge Snaps** | **Binary to Document** (parse) | — |

Refs: [Binary→Document](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438465/Binary%2Bto%2BDocument), [Document→Binary](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438976/Document%2Bto%2BBinary), [CSV Parser](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-csv-parser.html), [JSON Formatter](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-json-formatter.html).

---

## 4) ETL Cookbook — Common Snaps & Patterns

### 4.1 Most‑used **transformation** Snaps (ETL)
- **Mapper**: build field mappings & expressions; supports structural transforms like Move/Copy/Remove.  
  Docs: [Mapper](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-mapper.html), [Structural transforms](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/mapper-structure-transformation.html)
- **Join**: inner/left/outer joins; stream‑optimized when inputs are sorted.  
  Docs: [Join](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-join.html)
- **Aggregate**: group by fields; SUM/COUNT/AVG, etc. (pre‑sort if needed for large unsorted inputs).  
  Docs: [Transform pack (history & notes)](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/sp-history.html)
- **Filter / Conditional**: route or drop documents based on EL predicates (e.g., `$amount > 0`).
- **Format/Parse**: **CSV/JSON/XML/Avro/Parquet** (Formatter/Parser) to bridge document↔file workflows.
- **Binary↔Document**: serialize/parse at the edges of file processing.

### 4.2 Most‑used **connector** Snaps (ETL)
- **Databases / DW**: *Snowflake (Bulk Load/Upsert, Execute, SCD2)*, *Redshift*, *BigQuery*, *Synapse/SQL Server*, *Oracle*, *PostgreSQL*, *MySQL*.  
  Docs (examples): [Snowflake pack](https://docs.snaplogic.com/snaps/snaps-data/sp-snowflake/sp-snowflake-about.html), [Snowflake examples](https://docs.snaplogic.com/snaps/snaps-data/sp-snowflake/sp-examples.html)
- **Applications**: *Salesforce (SOQL/Upsert/Platform Events)*, *Workday (Read/Write/REST)*, *NetSuite (SOAP/REST)*, *ServiceNow*.  
  Docs: [Salesforce pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438704/Salesforce%2BSnap%2BPack), [Workday pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438832/Workday%2BSnap%2BPack), [NetSuite SOAP](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438933/NetSuite%2BSnap%2BPack)
- **Files & Cloud storage**: *Amazon S3* (Upload/Download/Select), *ADLS/Blob via Binary*, *GCS via Binary/Hadoop).  
  Docs: [Amazon S3 pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps#Amazon-S3-Snap-Pack)

### 4.3 Pattern sketches

**A) CSV on S3 → Snowflake (bulk load)**  
`File Reader (S3) → CSV Parser → Mapper → Snowflake Bulk Load`  
- Parse/clean columns; use Mapper expressions for types and null‑handling.  
- For very large loads, prefer **Bulk Load/Upsert** Snaps in the Snowflake pack.

**B) Salesforce → S3 (archive as JSON/CSV)**  
`Salesforce SOQL/Read → JSON/CSV Formatter → File Writer (S3)`  
- SOQL pulls the fields; Formatter serializes to the chosen format; File Writer persists to S3.

**C) Oracle → PostgreSQL (daily sync)**  
`Oracle Select → Mapper/Join/Aggregate → PostgreSQL Insert/Update`  
- Use **JDBC** if you don’t have the specific pack; parameterize table/schema via pipeline parameters.

**D) Workday → Snowflake (dimensions)**  
`Workday Read/REST → Mapper (normalize) → Snowflake Upsert`  
- Keep Workday account & object schemas in one sub‑pipeline; call with **Pipeline Execute**.

---

## 5) Quick Reference — When to reach for…

- **Bridge binary↔document**: *Binary to Document*, *Document to Binary* (Transform pack).  
  Docs: [B→D](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438465/Binary%2Bto%2BDocument), [D→B](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438976/Document%2Bto%2BBinary)
- **Format conversion**: *CSV/JSON/XML/Avro/Parquet Parser/Formatter*.  
  Docs: [CSV Parser](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-csv-parser.html), [JSON Formatter](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-json-formatter.html)
- **Schema & mapping**: *Mapper*, *Structure*, *In‑Memory Lookup*.
- **Relational/DW targets**: use native pack (Snowflake/Redshift/BigQuery/Synapse/SQL Server/Oracle/PostgreSQL/MySQL); otherwise *JDBC*.
- **SaaS apps**: native packs (Salesforce, Workday, NetSuite, ServiceNow, Dynamics, etc.). See [Enterprise Snaps](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439296/Enterprise%2BSnaps).

---

## 6) Notes & gotchas for LLMs and power users

- **Expression Language ≠ full JavaScript**: No assignments, no `===/!==`, no `++/--`; functions are available as globals. Use `$` for document context.  
  Ref: [Expression Language Overview](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438042/Expression%2BLanguage%2BOverview)
- **Expression Libraries** are **object‑literal helpers**, evaluated to `lib.*`; contents are static for the run.  
  Ref: [Expression Libraries](https://docs-snaplogic.atlassian.net/wiki/x/nvEV)
- **Prefer API Suite’s HTTP Client** over legacy REST Snaps for new pipelines.  
  Ref: [Core Snaps index (notes)](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps)
- **Full Core lists** (enumerated members) are on the Confluence Core page; transformation membership evolves over time.
  Refs: [Core Snaps (Confluence)](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps), [Transform pack](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438327/Transform%2BSnap%2BPack)
- **Unix Execute Snap**: Execute Unix/Linux commands and shell scripts directly in pipelines for system operations, file management, or custom scripting tasks.
  Ref: [Unix Execute](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/2561606032/Unix+Execute)

---

## 7) Appendix — Link hub (official docs)

- **Snaps catalog:** [Snaps reference](https://docs.snaplogic.com/snaps/snaps-about.html)  
- **Core Snap Packs:** [Core (new site)](https://docs.snaplogic.com/snaps/snaps-core/snaps-core-about.html) · [Core (Confluence)](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439376/Core%2BSnaps)  
  - Flow · Transform · Binary · Amazon S3 · API Suite (HTTP/GraphQL/gRPC) · OpenAPI · JDBC · Script · Data Catalog · Email · SOAP · JWT
- **Data Snap Packs:** [Data packs index](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439327/Data%2BSnaps)  
  - Snowflake · Redshift · BigQuery · Synapse · Azure SQL · Oracle · PostgreSQL · SQL Server · MySQL · Teradata · Vertica · SAP HANA · MongoDB · Cassandra · Kafka · Hadoop/Hive
- **Enterprise Snap Packs:** [Enterprise packs index](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1439296/Enterprise%2BSnaps)  
  - Salesforce · Workday (incl. REST) · NetSuite (SOAP/REST) · ServiceNow · SAP (ERP/S/4HANA/SuccessFactors/Concur/HANA) · Oracle HCM · Microsoft (Dynamics/SharePoint/Teams/Power BI/Entra ID/OneDrive) · Google (Sheets/PubSub/Directory) · Amazon SNS · Azure Service Bus · RabbitMQ · Shopify · Zuora · Coupa · Xactly · Jira · HubSpot · Slack · Box · OpenAir · Reltio · Tableau · Twilio
- **Transform pack deep‑links:** [Transform pack overview](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438327/Transform%2BSnap%2BPack) · [Join](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-join.html) · [Mapper](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-mapper.html) · [CSV Parser](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-csv-parser.html) · [JSON Formatter](https://docs.snaplogic.com/snaps/snaps-core/sp-transform/snap-json-formatter.html)
- **Binary/Document bridge:** [Binary→Document](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438465/Binary%2Bto%2BDocument) · [Document→Binary](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438976/Document%2Bto%2BBinary) · [Connecting Snaps](https://docs.snaplogic.com/snaps/snaps-connecting-snaps.html)
- **Expression Language:** [Overview](https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438042/Expression%2BLanguage%2BOverview) · [Expression Libraries](https://docs-snaplogic.atlassian.net/wiki/x/nvEV)

---

### Changelog for this guide
- **2025‑09‑17:** Initial complete edition with Core/Data/Enterprise enumeration and ETL examples.
