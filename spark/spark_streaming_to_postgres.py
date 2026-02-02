import os
import logging
from datetime import datetime, timezone
import signal
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, to_timestamp
from pyspark.sql.types import DecimalType
from pyspark.sql.functions import current_timestamp

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
    logger.info("Shutdown signal received. Stopping data generator gracefully.")
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

# -------------------------------------------------------------------
# Postgres write function
# -------------------------------------------------------------------
def write_batch_to_postgres(batch_df: DataFrame, batch_id: int):
    """
    Writes a micro-batch to Postgres.
    """
    if batch_df.isEmpty():
        logger.info(f"Batch {batch_id}: No valid records to write")
        return

    logger.info(f"Batch {batch_id}: Writing {batch_df.count()} records to Postgres")

    (
        batch_df.write
        .format("jdbc")
        .option("url", f"jdbc:postgresql://{POSTGRES_HOST}/{POSTGRES_DB}")
        .option("dbtable", "ecommerce_events")
        .option("user", POSTGRES_USER)
        .option("password", POSTGRES_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .save()
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

    spark.sparkContext.setLogLevel("WARN")

    input_dir = "/opt/spark/data/incoming"
    bad_records_dir = "/opt/spark/data/bad_records"

    os.makedirs(bad_records_dir, exist_ok=True)

    logger.info("Reading streaming CSV files")

    stream_df = (
        spark.readStream
        .format("csv")
        .option("header", "true")
        .option("badRecordsPath", bad_records_dir)
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
    
