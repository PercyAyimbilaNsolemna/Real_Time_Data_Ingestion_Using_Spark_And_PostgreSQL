"""
Data Generator for Real-Time E-commerce Events

This script simulates user activity on an e-commerce platform.
It generates CSV files in small batches to mimic real-time streaming data.

Spark Structured Streaming will later monitor this directory
and ingest the files as they arrive.

"""

import csv
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from random import random, randint, seed

from faker import Faker

# ============================================================
# CONFIGURATION SECTION
# ============================================================

# Where generated CSV files will be written
DATA_DIR = "/opt/spark/data/incoming"

# Where logs will be written
LOG_DIR = "/opt/spark/logs"

# Number of events per CSV file
BATCH_SIZE = 20

# Seconds to wait before generating the next batch
SLEEP_SECONDS = 3

# Seed for reproducibility (important for debugging & testing)
RANDOM_SEED = 42


# ============================================================
# INITIALIZATION
# ============================================================

# Ensure deterministic randomness
seed(RANDOM_SEED)
fake = Faker()
Faker.seed(RANDOM_SEED)

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "data_generator.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | data_generator | %(message)s",
)

logger = logging.getLogger(__name__)

# Flag used for graceful shutdown
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


# ============================================================
# EVENT GENERATION LOGIC
# ============================================================

def generate_event():
    """
    Generates a single e-commerce event.

    70% of events are 'view'
    30% of events are 'purchase'

    """
    event_type = "purchase" if random() < 0.3 else "view"

    return {
        "event_id": str(uuid.uuid4()),                     # unique identifier
        "user_id": randint(1, 1000),                       # simulated users
        "product_id": randint(1, 500),                     # simulated products
        "event_type": event_type,                          # view or purchase
        "price": (
            round(randint(10, 500) + random(), 2)
            if event_type == "purchase"
            else None
        ),
        "event_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    }


# ============================================================
# CSV BATCH WRITER
# ============================================================

def write_batch(batch_id: int):
    """
    Writes a batch of events to a CSV file.
    Each batch represents a micro-batch in a streaming system.

    """
    filename = f"events_batch_{batch_id:04d}.csv"
    filepath = os.path.join(DATA_DIR, filename)

    events = [generate_event() for _ in range(BATCH_SIZE)]

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)

    logger.info(f"Generated {filename} with {BATCH_SIZE} events")


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    """
    Main execution loop.
    Continuously generates CSV files until stopped.
    
    """
    logger.info("Data generator started")

    batch_id = 1

    while running:
        write_batch(batch_id)
        batch_id += 1
        time.sleep(SLEEP_SECONDS)

    logger.info("Data generator stopped cleanly")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("Fatal error occurred", exc_info=True)
        sys.exit(1)
