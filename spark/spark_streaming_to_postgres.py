import os
import logging
from datetime import datetime, timezone
import signal
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, to_timestamp
from pyspark.sql.types import DecimalType
from pyspark.sql.functions import current_timestamp

import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import pool
from contextlib import contextmanager

from schema import get_event_schema


# ============================================================
# CONFIGURATION & ENVIRONMENT
# ============================================================
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


# global flag for graceful shutdown
running = True


# ============================================================
# GRACEFUL SHUTDOWN HANDLING
# ============================================================

def shutdown_handler(signum, frame):
    """
    Handles SIGINT (Ctrl+C) and SIGTERM signals.
    This allows the script to stop cleanly without corrupting files.

    """
    global running
    logger.info("Shutdown signal received. Stopping spark streaming job gracefully.")
    running = False


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


# -------------------------------------------------------------------
# Logging setup
# -------------------------------------------------------------------
LOG_DIR = "/opt/spark/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "spark_streaming.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ============================================================
# CREATE TABLE ON START UP
# ============================================================

def ensure_schema_exists():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public.ecommerce_events (
            event_id UUID PRIMARY KEY,
            user_id INT NOT NULL,
            product_id INT NOT NULL,
            event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('view', 'purchase')),
            price NUMERIC(10,2),
            event_timestamp TIMESTAMP NOT NULL,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.close()



# ============================================================
# CONNECTION POOL (Initialize once globally)
# ============================================================
connection_pool = None

def initialize_connection_pool():
    """Initialize connection pool once at startup."""
    global connection_pool
    if connection_pool is None:
        logger.info("Initializing Postgres connection pool")
        connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,  # Adjust based on your workload
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
        logger.info("Connection pool initialized")

@contextmanager
def get_db_connection():
    """Context manager to get connection from pool."""
    conn = connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        connection_pool.putconn(conn)


# -------------------------------------------------------------------
# Postgres Partition write function
# -------------------------------------------------------------------
def write_partition_to_postgres(rows):
    rows = list(rows)
    if not rows:
        return

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    cursor = conn.cursor()

    insert_sql = """
        INSERT INTO ecommerce_events (
            event_id,
            user_id,
            product_id,
            event_type,
            price,
            event_timestamp,
            ingestion_timestamp
        )
        VALUES %s
        ON CONFLICT (event_id)
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            product_id = EXCLUDED.product_id,
            event_type = EXCLUDED.event_type,
            price = EXCLUDED.price,
            event_timestamp = EXCLUDED.event_timestamp,
            ingestion_timestamp = EXCLUDED.ingestion_timestamp
    """

    values = [
        (
            r.event_id,
            r.user_id,
            r.product_id,
            r.event_type,
            r.price,
            r.event_timestamp,
            r.ingestion_timestamp
        )
        for r in rows
    ]

    execute_values(cursor, insert_sql, values, page_size=200)
    conn.commit()

    cursor.close()
    conn.close()

# -------------------------------------------------------------------
# Postgres write function
# -------------------------------------------------------------------
def write_batch_to_postgres(batch_df: DataFrame, batch_id: int):
    """
    Writes a micro-batch to Postgres using connection pool.
    """
    if batch_df.isEmpty():
        logger.info(f"Batch {batch_id}: No valid records to write")
        return
    
    logger.info(f"Batch {batch_id}: Writing {batch_df.count()} records to Postgres")
    
    (
        batch_df
        .repartition(4)   # tune this
        .foreachPartition(write_partition_to_postgres)
    )
    
    logger.info(f"Batch {batch_id}: Write completed")



# -------------------------------------------------------------------
# Bad records write function
# -------------------------------------------------------------------
def write_bad_records(batch_df: DataFrame, batch_id: int):
    """
    Writes bad records to the bad records directory.

    """

    bad_records_dir = "/opt/spark/data/bad_records"

    if batch_df.isEmpty():
        logger.info(f"Batch {batch_id}: No invalid records")
        return

    logger.warning(
        f"Batch {batch_id}: Writing {batch_df.count()} invalid records"
    )

    (
        batch_df.write
        .mode("append")
        .csv(bad_records_dir)
    )


# -------------------------------------------------------------------
# Main Spark processing function
# -------------------------------------------------------------------
def process_stream():
    """
    Sets up Spark, reads streaming data, validates records,
    routes bad records, and writes valid records to Postgres.
    """
    logger.info("Starting Spark streaming job")

    spark = (
        SparkSession.builder
        .appName("SparkStreamingToPostgres")
        .getOrCreate()
    )

    # Initialize connection pool ONCE
    initialize_connection_pool()

    ensure_schema_exists()

    spark.sparkContext.setLogLevel("WARN")

    input_dir = "/opt/spark/data/incoming"
    bad_records_dir = "/opt/spark/data/bad_records"

    os.makedirs(bad_records_dir, exist_ok=True)

    logger.info("Reading streaming CSV files")

    stream_df = (
        spark.readStream
        .format("csv")
        .option("header", "true")
        .schema(get_event_schema())
        .load(input_dir)
    )

    
    # ---------------------------------------------------------------
    # Explicit type casting
    # ---------------------------------------------------------------
    typed_df = (
        stream_df
        .withColumn("event_id", col("event_id"))
        .withColumn("user_id", col("user_id").cast("int"))
        .withColumn("product_id", col("product_id").cast("int"))
        .withColumn("price", col("price").cast(DecimalType(10, 2)))
        .withColumn(
            "event_timestamp",
            to_timestamp(col("event_timestamp"))
        )
    )


    # ---------------------------------------------------------------
    # Removing deduplication
    # ---------------------------------------------------------------
    deduped_df = typed_df.dropDuplicates(["event_id"])

    

    # ---------------------------------------------------------------
    # Validation rules
    # ---------------------------------------------------------------
    validated_df = (
        deduped_df
        .withColumn(
            "is_valid",
            when(
                col("user_id").isNotNull()
                & col("event_type").isNotNull()
                & col("event_timestamp").isNotNull()
                & (
                    (col("event_type") != "purchase") |
                    (col("price").isNotNull())
                ),
                True
            ).otherwise(False)
        )
    )

    valid_df = validated_df.filter(col("is_valid") == True).drop("is_valid")
    invalid_df = validated_df.filter(col("is_valid") == False).drop("is_valid")

    valid_df = valid_df.withColumn(
        "ingestion_timestamp",
        current_timestamp()
    )


    # ---------------------------------------------------------------
    # Write bad records to disk
    # ---------------------------------------------------------------
    logger.info("Configuring bad records sink")
    invalid_query = (
        invalid_df.writeStream
        .foreachBatch(write_bad_records)
        .option("checkpointLocation", "checkpoints/bad_records")
        .start()
    )


    # ---------------------------------------------------------------
    # Write valid records to Postgres
    # ---------------------------------------------------------------
    logger.info("Configuring Postgres sink")

    valid_query = (
        valid_df.writeStream
        .foreachBatch(write_batch_to_postgres)
        .option("checkpointLocation", "checkpoints/postgres")
        .outputMode("append")
        .start()
    )

    logger.info("Streaming started successfully")

    try:
        while running:
            # just sleep and keep the process alive
            time.sleep(1)

    finally:
        logger.info("Stopping streaming queries...")
        for query in spark.streams.active:
            query.stop()

        # Close connection pool on shutdown
        if connection_pool:
            logger.info("Closing connection pool")
            connection_pool.closeall()
        logger.info("Stopping Spark session...")
        spark.stop()
        logger.info("Spark shutdown completed cleanly")



# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    try:
        process_stream()
    except KeyboardInterrupt:
        # Already handled via signal handler
        print("Streaming stopped by user (Ctrl+C)")
        exit(0)
    except Exception:
        logger.exception("Fatal error in Spark streaming job")
        raise
    
