# Problem_1/consumer.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode, lower, udf, count, window, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, IntegerType, TimestampType
import spacy
import json

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092" # Internal Docker network address
INPUT_KAFKA_TOPIC = "raw-news"
OUTPUT_KAFKA_TOPIC = "news-entities"
SPARK_APP_NAME = "NewsEntityCounter"
SPARK_MASTER_URL = "spark://spark-master:7077" # Internal Docker network address
WINDOW_DURATION = "5 minutes" # Process data in 5-minute windows
SLIDING_INTERVAL = "1 minute" # Update results every 1 minute
WATERMARK_DELAY = "10 minutes" # Allow data to be late by up to 10 minutes

# --- NER Function using spaCy ---
# Load spaCy model (make sure it's downloaded in the Docker container)
try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    print("Downloading 'en_core_web_sm'...")
    # Note: Downloading model here might not be ideal in a distributed environment.
    # It's better to ensure the model is pre-installed on worker nodes.
    # The docker-compose setup attempts to pre-install it.
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
    print("spaCy model 'en_core_web_sm' downloaded and loaded.")

def extract_entities(text):
    """Extracts named entities (ORG, PERSON, GPE) from text using spaCy."""
    if not text:
        return []
    doc = nlp(text)
    # Filter for specific entity types if needed, e.g., ORG, PERSON, GPE (Geopolitical Entity)
    entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ["ORG", "PERSON", "GPE"]]
    # Simple cleanup: remove leading/trailing whitespace and possessives
    cleaned_entities = [e.strip().replace("'s", "") for e in entities if e.strip()]
    return list(set(cleaned_entities)) # Return unique entities per article

# Register UDF (User Defined Function)
extract_entities_udf = udf(extract_entities, ArrayType(StringType()))

# --- Spark Session ---
print("Creating Spark Session...")
spark = (SparkSession
    .builder
    .appName(SPARK_APP_NAME)
    #.master(SPARK_MASTER_URL) # Comment out when submitting via spark-submit, master url is passed there
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0")
    # Unique checkpoint location for the input stream read
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint-consumer")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN") # Reduce verbosity
print("Spark Session created.")

# --- Define Input Schema ---
# Matches the structure sent by producer.py
schema = StructType([
    StructField("source", StringType(), True),
    StructField("title", StringType(), True),
    StructField("description", StringType(), True),
    StructField("publishedAt", StringType(), True), # Read as string initially
    StructField("url", StringType(), True),
    StructField("text_for_ner", StringType(), True) # Field containing text for NER
])

# --- Read from Kafka ---
print(f"Reading stream from Kafka topic: {INPUT_KAFKA_TOPIC}")
kafka_stream_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", INPUT_KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# --- Process Stream ---
# 1. Decode Kafka message value (JSON string)
# 2. Parse JSON and select relevant columns
# 3. Convert publishedAt string to Timestamp for watermarking
# 4. Extract named entities using UDF
# 5. Explode the array of entities into individual rows
# 6. Apply watermarking and windowing
# 7. Group by window and entity, then count occurrences
# 8. Format output for Kafka (JSON string)

print("Processing stream...")
json_df = kafka_stream_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# Add processing timestamp and parse event timestamp
processed_df = json_df \
    .withColumn("processingTime", current_timestamp()) \
    .withColumn("eventTime", col("publishedAt").cast(TimestampType())) \
    .filter(col("text_for_ner").isNotNull()) # Ensure text exists

# Apply NER and explode entities
entities_df = processed_df \
    .withColumn("entities", extract_entities_udf(col("text_for_ner"))) \
    .select("eventTime", "processingTime", explode("entities").alias("entity"))

# Apply watermarking and windowing, then count entities
# Watermark on event time to handle late data
# Group by window and entity name
entity_counts_df = entities_df \
    .withWatermark("eventTime", WATERMARK_DELAY) \
    .groupBy(
        window(col("eventTime"), WINDOW_DURATION, SLIDING_INTERVAL),
        col("entity")
    ) \
    .agg(count("entity").alias("count"))

# Select and format for output Kafka topic
# We want to send {"entity": "...", "count": ..., "window_start": "...", "window_end": "..."}
output_df = entity_counts_df \
    .select(
        col("entity"),
        col("count").cast(IntegerType()), # Ensure count is integer
        col("window.start").cast(StringType()).alias("window_start"), # Cast timestamp to string
        col("window.end").cast(StringType()).alias("window_end")
    ) \
    .selectExpr("to_json(struct(*)) AS value") # Convert row to JSON string

# --- Write to Kafka ---
print(f"Writing results to Kafka topic: {OUTPUT_KAFKA_TOPIC}")
query = (output_df
    .writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
    .option("topic", OUTPUT_KAFKA_TOPIC)
    # Unique checkpoint location for the output stream write
    .option("checkpointLocation", "/tmp/spark-checkpoint-output")
    .outputMode("update")
    # Use update mode for windowed aggregations
    .start()
)

print("Streaming query started. Waiting for termination...")
query.awaitTermination()
print("Streaming query terminated.")
