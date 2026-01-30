from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
)

# ============================================================
# SCHEMA DEFINITION
# ============================================================

def get_event_schema() -> StructType:
    return StructType([
        StructField("event_id", StringType(), True),
        StructField("user_id", IntegerType(), True),
        StructField("product_id", IntegerType(), True),
        StructField("event_type", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("event_timestamp", StringType(), True),
    ])