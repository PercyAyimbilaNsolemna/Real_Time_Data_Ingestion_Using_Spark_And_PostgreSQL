<div align="center">

# Real-Time Data Ingestion Using Spark and PostgreSQL

### *Production-Grade Streaming Architecture for E-Commerce Analytics*

[![Apache Spark](https://img.shields.io/badge/Apache_Spark-3.5+-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)](https://spark.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

---

*Demonstrating enterprise-grade streaming data engineering with academic rigor and industry best practices*

[📖 Overview](#1-project-overview) • [🏗️ Architecture](#3-high-level-architecture) • [⚡ Data Flow](#4-data-flow-description) • [🛡️ Reliability](#6-fault-tolerance-and-reliability)

</div>

---

## 1. Project Overview

This project demonstrates the design and implementation of a **real-time data ingestion pipeline** using **Apache Spark Structured Streaming** and **PostgreSQL**, orchestrated with **Docker**. The system simulates live e-commerce user activity, processes incoming data streams in near real time, validates records, and persists clean data into a relational database for analytics and downstream consumption.

<div align="center">

### **Key Engineering Principles**

</div>

<table>
<tr>
<td width="50%">

**Streaming Architecture**
- Micro-batch processing semantics
- Schema enforcement at ingestion
- Exactly-once processing guarantees
- Checkpointing for fault tolerance

</td>
<td width="50%">

**Engineering Best Practices**
- Separation of concerns (generate → process → store)
- Data quality validation gates
- Structured observability & logging
- Container-based reproducibility

</td>
</tr>
</table>

The project is intentionally designed to reflect **both academic rigor and industry best practices**, including:

```
✓ Streaming ingestion semantics (micro-batching)
✓ Schema enforcement and data validation
✓ Fault tolerance via checkpoints
✓ Separation of concerns between data generation, processing, and storage
✓ Observability through structured logging
```

---

## 2. Problem Statement

Modern data-driven systems rarely rely on static batch data alone. Instead, they ingest **continuous streams of events** such as clicks, views, purchases, and sensor readings. These systems must:

<table>
<tr>
<th>Challenge</th>
<th>Solution in This Project</th>
</tr>
<tr>
<td>Handle continuously arriving data</td>
<td>Spark Structured Streaming with file-based micro-batching</td>
</tr>
<tr>
<td>Validate records to avoid polluting downstream systems</td>
<td>Rule-based validation with bad record isolation</td>
</tr>
<tr>
<td>Persist data reliably, even in the presence of failures</td>
<td>Checkpointing + transactional batch writes to PostgreSQL</td>
</tr>
<tr>
<td>Scale independently across components</td>
<td>Docker-based component isolation with clear interfaces</td>
</tr>
</table>

This project addresses these challenges by implementing a **simplified but realistic real-time ingestion architecture** for e-commerce events.

---

## 3. High-Level Architecture

<div align="center">

### **System Components**

</div>

At a high level, the system consists of four major components:

<table>
<tr>
<th width="25%">Component</th>
<th width="75%">Responsibility</th>
</tr>
<tr>
<td><strong>1. Data Generator</strong><br>(Producer)</td>
<td>Simulates real-time e-commerce events and writes them as CSV files in small batches.</td>
</tr>
<tr>
<td><strong>2. Spark Streaming</strong><br>(Processor)</td>
<td>Continuously monitors incoming files, validates records, separates bad data from good data, and writes valid events to PostgreSQL.</td>
</tr>
<tr>
<td><strong>3. PostgreSQL</strong><br>(Sink / Storage)</td>
<td>Stores validated events in a relational table optimized for querying and analytics.</td>
</tr>
<tr>
<td><strong>4. Docker Infrastructure</strong><br>(Orchestration)</td>
<td>Ensures reproducibility, isolation, and ease of deployment across environments.</td>
</tr>
</table>

---

<div align="center">

### **Data Flow Architecture**

</div>

Data flows strictly **one way**:

```
┌─────────────────┐
│ Data Generator  │ (Simulates e-commerce events)
└────────┬────────┘
         │ CSV batches
         ▼
┌─────────────────┐
│ Spark Streaming │ (Validates & processes)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌──────────────┐
│ Valid │  │ Bad Records  │
│ Data  │  │ (Disk/Audit) │
└───┬───┘  └──────────────┘
    │
    ▼
┌─────────────┐
│ PostgreSQL  │ (Analytics-ready storage)
└─────────────┘
```

---

## 4. Data Flow Description

### Step 1: Event Generation

The `data_generator.py` script simulates user behavior on an e-commerce platform. Each event represents either:

- A **view** event (≈70%), or
- A **purchase** event (≈30%)

**Event Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Unique identifier for each event |
| `user_id` | Integer | User performing the action |
| `product_id` | Integer | Product being viewed/purchased |
| `event_type` | String | Either `view` or `purchase` |
| `price` | Decimal | Transaction amount (purchases only) |
| `event_timestamp` | Timestamp | UTC, timezone-aware event time |

Events are written as **small CSV batches** into the `data/incoming/` directory, mimicking real-time arrival of data.

---

### Step 2: Streaming Ingestion with Spark

The `spark_streaming_to_postgres.py` job uses **Spark Structured Streaming** in file-based streaming mode:

<table>
<tr>
<td width="50%">

**Processing Model:**
- Spark continuously monitors the `incoming/` directory
- Newly arriving CSV files are treated as streaming micro-batches
- A predefined schema is enforced at read time

</td>
<td width="50%">

**Why This Approach:**
- Mirrors real-world ingestion patterns
- Used with cloud object storage (S3, GCS, Azure Blob)
- Provides exactly-once semantics
- Supports schema evolution

</td>
</tr>
</table>

---

### Step 3: Data Validation

Before persisting any data, each record is validated according to business rules:

#### **Validation Rules**

```
1. Required fields must not be null:
   • user_id
   • event_type
   • event_timestamp

2. Conditional validation:
   • If event_type = 'purchase', then price must not be null
```

**Record Routing:**

<table>
<tr>
<th>Record Type</th>
<th>Destination</th>
<th>Purpose</th>
</tr>
<tr>
<td>✅ Valid records</td>
<td>PostgreSQL <code>ecommerce_events</code> table</td>
<td>Analytics and downstream consumption</td>
</tr>
<tr>
<td>❌ Invalid records</td>
<td><code>data/bad_records/</code> directory</td>
<td>Inspection, debugging, and potential replay</td>
</tr>
</table>

This ensures data quality while preserving invalid data for auditing.

---

### Step 4: Enrichment and Persistence

Before writing to PostgreSQL, valid records are enriched with:

- **`ingestion_timestamp`**: The time the record was ingested by Spark

**Write Strategy:**

Data is then written using Spark's `foreachBatch` mechanism, which:

```
✓ Preserves transactional batch semantics
✓ Allows fine-grained control over database writes
✓ Integrates cleanly with JDBC sinks
✓ Supports custom error handling and retry logic
```

---

## 5. Storage Layer (PostgreSQL)

PostgreSQL serves as the **system of record** for validated events.

### Key Characteristics

<table>
<tr>
<td width="50%">

**Schema Design:**
- Relational schema with constraints
- Indexed columns for query performance
- Automatic ingestion timestamping
- Normalized structure for analytics

</td>
<td width="50%">

**Operational Features:**
- ACID compliance for data integrity
- Connection pooling for high throughput
- Read replicas support (future extension)
- Partitioning-ready design

</td>
</tr>
</table>

The primary table:

- **`ecommerce_events`**

is created ahead of time using `postgres_setup.sql`, ensuring schema stability and controlled evolution.

---

## 6. Fault Tolerance and Reliability

This system incorporates multiple reliability mechanisms:

### Checkpointing

<table>
<tr>
<td width="50%">

**What is Checkpointed:**
- Streaming progress tracking
- Offset information for exactly-once semantics
- Aggregation state (if stateful operations exist)

</td>
<td width="50%">

**Recovery Behavior:**
- If the Spark job restarts, it resumes from the last known state
- No data loss or duplication
- Transparent to downstream consumers

</td>
</tr>
</table>

---

### Graceful Shutdown

```
✓ The streaming job handles termination signals cleanly
✓ Active queries are stopped gracefully
✓ Spark sessions are shut down without corrupting state
✓ In-flight batches are completed before shutdown
```

---

### Bad Record Isolation

<table>
<tr>
<th>Design Decision</th>
<th>Benefit</th>
</tr>
<tr>
<td>Invalid data never reaches PostgreSQL</td>
<td>Maintains database integrity and query performance</td>
</tr>
<tr>
<td>Bad data is preserved on disk</td>
<td>Enables debugging, root cause analysis, and replay</td>
</tr>
<tr>
<td>Separate storage for bad records</td>
<td>Clear separation between production and problematic data</td>
</tr>
</table>

---

## 7. Observability and Logging

Structured logging is implemented across components:

<table>
<tr>
<th>Component</th>
<th>Logged Information</th>
</tr>
<tr>
<td><strong>Data Generator</strong></td>
<td>
• Event generation lifecycle<br>
• Batch sizes and timing<br>
• File write operations
</td>
</tr>
<tr>
<td><strong>Spark Streaming</strong></td>
<td>
• Streaming lifecycle events<br>
• Batch processing metrics<br>
• Validation statistics<br>
• Shutdown events
</td>
</tr>
</table>

Logs are written to a shared `logs/` directory, enabling:

```
✓ Debugging and troubleshooting
✓ Auditing and compliance
✓ Operational monitoring
✓ Performance analysis
```

---

## 8. Technology Stack

<div align="center">

| Component | Technology | Purpose |
|:---------:|:----------:|:--------|
| **Language** | Python | Application logic and orchestration |
| **Streaming Engine** | Apache Spark (Structured Streaming) | Real-time data processing |
| **Database** | PostgreSQL | Persistent storage and analytics |
| **Containerization** | Docker & Docker Compose | Environment isolation and deployment |
| **Data Format** | CSV | Event serialization (extensible to JSON, Avro, Parquet) |
| **Logging** | Python `logging` module | Structured observability |

</div>

---

## 9. Use Cases and Extensions

This architecture can be extended to support:

<table>
<tr>
<td width="50%">

**Streaming Sources:**
- Kafka-based streaming sources
- Cloud object storage (S3 / GCS)
- Message queues (RabbitMQ, SQS)
- CDC streams from databases

</td>
<td width="50%">

**Downstream Consumers:**
- Real-time analytics dashboards
- Data warehouses (Redshift, BigQuery, Snowflake)
- Machine learning feature stores
- Event-driven microservices

</td>
</tr>
</table>

**Additional Enhancements:**

```
✓ Schema evolution and versioning (Schema Registry)
✓ Multi-sink writes (PostgreSQL + data lake)
✓ Windowed aggregations for real-time metrics
✓ Exactly-once delivery to Kafka topics
✓ Integration with dbt for transformation
```

---

## 10. Summary

This project demonstrates a complete, production-inspired **real-time data ingestion pipeline**:

<div align="center">

| Feature | Implementation |
|:--------|:---------------|
| **End-to-end streaming flow** | File-based ingestion → Spark processing → PostgreSQL persistence |
| **Strong validation guarantees** | Rule-based filtering with bad record isolation |
| **Reliable persistence** | Checkpointing + transactional writes |
| **Clean shutdown behavior** | Graceful termination with state preservation |
| **Industry-aligned architecture** | Container-based, scalable, and observable |

</div>

It is suitable for:

```
✓ Academic evaluation
✓ Technical interviews
✓ Portfolio demonstration
✓ Foundation for more advanced streaming systems
```

---

<div align="center">

## 🚀 Getting Started

**Ready to run the pipeline?**

Check out the [Installation Guide](docs/INSTALLATION.md) and [Configuration Documentation](docs/CONFIGURATION.md)

---

## 👨‍💻 About the Author

**Percy Ayimbila Nsolemna**

*Data Engineer | Streaming Architecture Specialist*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/yourprofile)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/PercyAyimbilaNsolemna)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:your.email@example.com)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⭐ Show Your Support

**If this project helped you understand streaming data engineering, give it a star!**

[![Star](https://img.shields.io/github/stars/yourusername/spark-postgres-streaming?style=social)](https://github.com/yourusername/spark-postgres-streaming)

---

*Built with precision for the data engineering community*

**Made with ❤️ by Percy Ayimbila Nsolemna**

</div>