<div align="center">

# User Guide
## Real-Time Data Ingestion Using Spark & PostgreSQL

*Step-by-step instructions for setup, execution, and verification*

---

[![Docker](https://img.shields.io/badge/Docker-Required-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Apache Spark](https://img.shields.io/badge/Spark-3.5+-E25A1C?style=flat-square&logo=apachespark)](https://spark.apache.org/)

</div>

---

## 📑 Table of Contents

- [Prerequisites](#1-prerequisites)
- [Project Structure](#2-project-structure)
- [Environment Configuration](#3-environment-configuration)
- [Starting Infrastructure](#4-start-infrastructure-services)
- [PostgreSQL Verification](#5-verify-postgresql-initialization)
- [Running Data Generator](#6-run-the-data-generator)
- [Running Spark Streaming](#7-run-the-spark-streaming-job)
- [Data Verification](#8-verify-data-in-postgresql)
- [pgAdmin Connection](#9-connect-using-pgadmin)
- [Stopping the System](#10-stopping-the-system)
- [Troubleshooting](#11-common-issues--troubleshooting)

---

## 1. Prerequisites

This guide provides **step-by-step instructions** for setting up, running, and verifying the real-time data ingestion pipeline built with **Apache Spark Structured Streaming** and **PostgreSQL** using **Docker**.

It assumes no prior knowledge of the internal implementation and is written to be reproducible on any machine with Docker installed.

### Required Software

Ensure the following tools are installed on your system:

<table>
<tr>
<th>Tool</th>
<th>Minimum Version</th>
<th>Purpose</th>
</tr>
<tr>
<td><strong>Docker</strong></td>
<td>20.x or higher</td>
<td>Container runtime</td>
</tr>
<tr>
<td><strong>Docker Compose</strong></td>
<td>v2 (recommended)</td>
<td>Multi-container orchestration</td>
</tr>
<tr>
<td><strong>Git</strong></td>
<td>Any recent version</td>
<td>Repository cloning (optional)</td>
</tr>
<tr>
<td><strong>pgAdmin or psql</strong></td>
<td>Latest</td>
<td>Database inspection</td>
</tr>
</table>

### Verify Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version
```

**Expected Output:**
```
Docker version 24.0.x, build ...
Docker Compose version v2.x.x
```

---

## 2. Project Structure

Confirm that your project directory matches the structure below:

```
Real_Time_Data_Ingestion_Using_Spark_And_PostgreSQL/
│
├── data/
│   ├── incoming/        # Generated CSV files (stream source)
│   ├── bad_records/     # Invalid records
│   └── processed/       # (Optional future use)
│
├── logs/                # Application logs
│
├── spark/
│   ├── data_generator.py
│   ├── spark_streaming_to_postgres.py
│   ├── schema.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── sql/
│   └── postgres_setup.sql
│
├── docker-compose.yml
├── .env
└── README.md (optional)
```

> **Note:** Ensure all directories exist before proceeding. Docker Compose will mount these as volumes.

---

## 3. Environment Configuration

Edit the `.env` file at the project root:

```env
POSTGRES_DB=ecommerce
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### Important Configuration Notes

<table>
<tr>
<th>Parameter</th>
<th>Value</th>
<th>Context</th>
</tr>
<tr>
<td><code>POSTGRES_HOST</code></td>
<td><code>postgres</code></td>
<td>✅ Correct for Docker internal networking</td>
</tr>
<tr>
<td><code>POSTGRES_HOST</code></td>
<td><code>localhost</code></td>
<td>✅ Use when connecting from host machine (pgAdmin)</td>
</tr>
</table>

> ⚠️ **Important:** The hostname differs based on connection origin. Inside Docker containers, use `postgres`. From your host machine (e.g., pgAdmin), use `localhost`.

---

## 4. Start Infrastructure Services

From the project root directory, run:

```bash
docker compose up -d --build
```

### What This Command Does

<table>
<tr>
<td width="40%"><strong>Flag</strong></td>
<td width="60%"><strong>Purpose</strong></td>
</tr>
<tr>
<td><code>up</code></td>
<td>Start all services defined in docker-compose.yml</td>
</tr>
<tr>
<td><code>-d</code></td>
<td>Run in detached mode (background)</td>
</tr>
<tr>
<td><code>--build</code></td>
<td>Rebuild images before starting containers</td>
</tr>
</table>

This will:

- ✅ Build the Spark container
- ✅ Start PostgreSQL
- ✅ Initialize the database and tables via `postgres_setup.sql`

### Verify Containers Are Running

```bash
docker ps
```

**Expected Output:**

```
CONTAINER ID   IMAGE              STATUS         PORTS                    NAMES
abc123def456   postgres:16        Up 10 seconds  0.0.0.0:5432->5432/tcp   postgres
xyz789ghi012   spark-streaming    Up 10 seconds                           spark
```

You should see:
- `postgres` container
- `spark` container

---

## 5. Verify PostgreSQL Initialization

### Step 1: Enter PostgreSQL Container

```bash
docker exec -it postgres psql -U postgres
```

### Step 2: List Databases

```sql
\l
```

**Expected Output:**

```
                                      List of databases
   Name    |  Owner   | Encoding |  Collate   |   Ctype    |   Access privileges
-----------+----------+----------+------------+------------+-----------------------
 ecommerce | postgres | UTF8     | en_US.utf8 | en_US.utf8 |
 postgres  | postgres | UTF8     | en_US.utf8 | en_US.utf8 |
```

You should see the `ecommerce` database.

### Step 3: Connect to Database

```sql
\c ecommerce
```

### Step 4: List Tables

```sql
\dt
```

**Expected Output:**

```
               List of relations
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | ecommerce_events  | table | postgres
```

Expected tables:
- `ecommerce_events`

### Step 5: Exit psql

```sql
\q
```

---

## 6. Run the Data Generator

### Step 1: Enter Spark Container

```bash
docker exec -it spark bash
```

### Step 2: Start Data Generation

```bash
python app/data_generator.py
```

### Expected Behavior

<table>
<tr>
<th>Observable Effect</th>
<th>Description</th>
</tr>
<tr>
<td>CSV files appearing</td>
<td>New files created every few seconds in <code>data/incoming/</code></td>
</tr>
<tr>
<td>Log file updates</td>
<td>Detailed logs written to <code>logs/data_generator.log</code></td>
</tr>
</table>

**Sample Console Output:**

```
2024-01-30 10:15:23 - INFO - Generated batch of 50 events
2024-01-30 10:15:23 - INFO - Written to: data/incoming/batch_20240130_101523.csv
2024-01-30 10:15:28 - INFO - Generated batch of 50 events
...
```

### Stopping the Generator

Press `Ctrl + C` to stop gracefully.

> **Note:** Graceful shutdown is supported and will complete the current batch before terminating.

---

## 7. Run the Spark Streaming Job

### Step 1: Open New Terminal

It's recommended to run this in a separate terminal window for better visibility.

### Step 2: Enter Spark Container

```bash
docker exec -it spark bash
```

### Step 3: Start Streaming Job

```bash
python app/spark_streaming_to_postgres.py
```

### Expected Behavior

<table>
<tr>
<th>Stage</th>
<th>Observable Effect</th>
</tr>
<tr>
<td><strong>Initialization</strong></td>
<td>Spark context creation, checkpoint directory setup</td>
</tr>
<tr>
<td><strong>File Detection</strong></td>
<td>Spark detects new CSV files in <code>data/incoming/</code></td>
</tr>
<tr>
<td><strong>Processing</strong></td>
<td>Batch processing logs, validation statistics</td>
</tr>
<tr>
<td><strong>Valid Records</strong></td>
<td>Written to PostgreSQL <code>ecommerce_events</code> table</td>
</tr>
<tr>
<td><strong>Invalid Records</strong></td>
<td>Written to <code>data/bad_records/</code> directory</td>
</tr>
<tr>
<td><strong>Logging</strong></td>
<td>Detailed logs written to <code>logs/spark_streaming.log</code></td>
</tr>
</table>

**Sample Console Output:**

```
2024-01-30 10:16:05 - INFO - Streaming query started
2024-01-30 10:16:10 - INFO - Batch 0: Processed 50 records
2024-01-30 10:16:10 - INFO - Valid: 48, Invalid: 2
2024-01-30 10:16:15 - INFO - Batch 1: Processed 50 records
...
```

### Stopping the Streaming Job

Press `Ctrl + C` to stop gracefully.

> **Note:** Clean shutdown is supported. The job will complete the current batch and save checkpoint state before terminating.

---

## 8. Verify Data in PostgreSQL

### Using psql

```bash
docker exec -it postgres psql -U postgres -d ecommerce
```

### Query 1: Count Total Records

```sql
SELECT COUNT(*) FROM ecommerce_events;
```

**Expected Output:**

```
 count
-------
   248
(1 row)
```

### Query 2: View Recent Records

```sql
SELECT 
    event_id,
    user_id,
    product_id,
    event_type,
    price,
    event_timestamp,
    ingestion_timestamp
FROM ecommerce_events
ORDER BY ingestion_timestamp DESC
LIMIT 10;
```

**Sample Output:**

```
              event_id              | user_id | product_id | event_type | price |     event_timestamp     |   ingestion_timestamp
------------------------------------+---------+------------+------------+-------+-------------------------+-------------------------
 a1b2c3d4-e5f6-7890-abcd-ef1234567890 |     42 |        105 | purchase   | 49.99 | 2024-01-30 10:15:45+00 | 2024-01-30 10:16:02+00
 b2c3d4e5-f6g7-8901-bcde-fg2345678901 |     17 |         89 | view       |       | 2024-01-30 10:15:43+00 | 2024-01-30 10:16:02+00
...
```

### Query 3: Verify Event Type Distribution

```sql
SELECT 
    event_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM ecommerce_events
GROUP BY event_type;
```

**Expected Output:**

```
 event_type | count | percentage
------------+-------+------------
 view       |   172 |      69.35
 purchase   |    76 |      30.65
```

---

## 9. Connect Using pgAdmin

### Step 1: Open pgAdmin

Launch pgAdmin on your host machine.

### Step 2: Create New Server

Right-click **Servers** → **Create** → **Server**

### Step 3: Configure Connection

**General Tab:**
- **Name:** `Ecommerce Streaming Pipeline` (or any descriptive name)

**Connection Tab:**

<table>
<tr>
<th>Setting</th>
<th>Value</th>
</tr>
<tr>
<td>Host name/address</td>
<td><code>localhost</code></td>
</tr>
<tr>
<td>Port</td>
<td><code>5432</code></td>
</tr>
<tr>
<td>Maintenance database</td>
<td><code>postgres</code></td>
</tr>
<tr>
<td>Username</td>
<td><code>postgres</code></td>
</tr>
<tr>
<td>Password</td>
<td><code>postgres</code></td>
</tr>
</table>

### Step 4: Navigate to Table

Once connected:

```
Servers → Ecommerce Streaming Pipeline → Databases → ecommerce → 
Schemas → public → Tables → ecommerce_events
```

### Step 5: View Data

Right-click **ecommerce_events** → **View/Edit Data** → **All Rows**

> **Tip:** Refresh periodically to see streaming data arriving in real-time.

---

## 10. Stopping the System

### Stop All Services

```bash
docker compose down
```

This will:
- ✅ Stop all running containers
- ✅ Remove containers
- ✅ Preserve data volumes

### Remove Volumes (Delete All Data)

```bash
docker compose down -v
```

> ⚠️ **Warning:** This command deletes all data in the PostgreSQL database. Use with caution.

### Verify Cleanup

```bash
docker ps -a
```

Should show no containers related to this project.

---

## 11. Common Issues & Troubleshooting

### Issue 1: Spark Not Detecting Files

**Symptoms:**
- No batch processing logs
- Data generator runs but Spark shows no activity

**Solutions:**

<table>
<tr>
<th>Check</th>
<th>Command/Action</th>
</tr>
<tr>
<td>Files exist in incoming directory</td>
<td><code>ls -la data/incoming/</code></td>
</tr>
<tr>
<td>File permissions</td>
<td><code>chmod -R 755 data/incoming/</code></td>
</tr>
<tr>
<td>Spark checkpoint directory</td>
<td>Delete <code>checkpoint/</code> and restart</td>
</tr>
</table>

> **Important:** Do not modify existing CSV files after creation. Spark streaming relies on file immutability.

---

### Issue 2: PostgreSQL Connection Issues

**Symptoms:**
- "Connection refused" errors
- "Host not found" errors

**Solutions:**

<table>
<tr>
<th>Connection From</th>
<th>Use Host</th>
</tr>
<tr>
<td>Inside Docker (Spark)</td>
<td><code>postgres</code></td>
</tr>
<tr>
<td>Outside Docker (pgAdmin)</td>
<td><code>localhost</code></td>
</tr>
</table>

**Verify PostgreSQL is Running:**

```bash
docker ps | grep postgres
```

**Check Logs:**

```bash
docker logs postgres
```

---

### Issue 3: Empty bad_records Files

**Symptoms:**
- Files exist in `data/bad_records/` but appear empty
- Metadata files (`.crc`, `_SUCCESS`) present

**Explanation:**

This is **expected behavior** when no invalid records exist. Spark creates metadata files even when the output is empty.

**To Verify:**

```bash
# Count actual data files
find data/bad_records/ -type f -name "part-*" -exec wc -l {} \;
```

If all counts are 0, no invalid records were generated (which is expected for clean data).

---

### Issue 4: Port Already in Use

**Symptoms:**
```
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Solutions:**

1. **Stop conflicting service:**
   ```bash
   # On Linux/Mac
   sudo systemctl stop postgresql
   
   # On Windows
   net stop postgresql-x64-xx
   ```

2. **Change port in docker-compose.yml:**
   ```yaml
   ports:
     - "5433:5432"  # Use 5433 on host instead
   ```

---

### Issue 5: Permission Denied Errors

**Symptoms:**
- Cannot write to `data/` or `logs/` directories
- FileNotFoundError in logs

**Solution:**

```bash
# Fix directory permissions
sudo chmod -R 777 data/ logs/

# Or set proper ownership
sudo chown -R $USER:$USER data/ logs/
```

---

### Issue 6: Spark Session Errors

**Symptoms:**
```
Exception: Java gateway process exited before sending its port number
```

**Solutions:**

1. **Verify Java installation in container:**
   ```bash
   docker exec -it spark java -version
   ```

2. **Rebuild Spark image:**
   ```bash
   docker compose build --no-cache spark
   ```

---

## 12. Summary

### ✅ You Have Successfully:

- ✓ Started a containerized streaming system
- ✓ Generated live e-commerce data
- ✓ Processed and validated data using Spark
- ✓ Persisted clean data to PostgreSQL
- ✓ Verified results via SQL and pgAdmin

### 📚 Next Steps

- Experiment with different validation rules
- Scale data generation rate
- Add custom analytics queries
- Integrate with visualization tools (Grafana, Metabase)
- Extend to Kafka-based streaming sources

---

<div align="center">

This completes the operational setup of the real-time data ingestion pipeline.

**For additional help, refer to:**
- [Main README](../README.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](API.md)

---

*Documentation maintained by Percy Ayimbila Nsolemna*

</div>