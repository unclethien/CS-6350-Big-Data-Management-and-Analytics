import spacy
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode, udf, count, struct, to_json
from pyspark.sql.types import StructType, StructField, StringType, ArrayType
import os

# --- Configuration ---
KAFKA_INPUT_TOPIC = 'raw-news'
KAFKA_OUTPUT_TOPIC = 'news-entities' # Should match Logstash input config
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9094' # Use the host port for Spark connection
SPACY_MODEL = 'en_core_web_sm' # Small English model, adjust if needed
SPARK_APP_NAME = 'NewsEntityCounter'

# --- Spacy Setup ---
# Ensure the model is downloaded: python -m spacy download en_core_web_sm
print(f"Loading Spacy model: {SPACY_MODEL}...")
try:
    nlp = spacy.load(SPACY_MODEL)
    print("Spacy model loaded successfully.")
except OSError:
    print(f"Spacy model '{SPACY_MODEL}' not found. Please download it:")
    print(f"python -m spacy download {SPACY_MODEL}")
    exit()

# --- Spark Session Setup ---
print("Creating Spark session...")
spark = SparkSession.builder \
    .appName(SPARK_APP_NAME) \
    .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1') \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN") # Reduce verbosity
print("Spark session created.")

# --- Kafka Schema ---
# Define the schema of the JSON data coming from the producer
kafka_schema = StructType([
    StructField("source", StringType(), True),
    StructField("author", StringType(), True),
    StructField("title", StringType(), True),
    StructField("description", StringType(), True),
    StructField("url", StringType(), True),
    StructField("publishedAt", StringType(), True),
    StructField("content", StringType(), True)
])

# --- NER Function ---
# Function to extract named entities (PERSON, ORG, GPE)
def extract_entities(text):
    if text is None:
        return []
    doc = nlp(str(text))
    entities = [
        ent.text for ent in doc.ents
        if ent.label_ in ["PERSON", "ORG", "GPE"] # Person, Organization, Geo-Political Entity
    ]
    return entities

# --- Spark UDF ---
# Create a User Defined Function (UDF) for Spark
extract_entities_udf = udf(extract_entities, ArrayType(StringType()))

# --- Read Stream from Kafka ---
print(f"Reading from Kafka topic: {KAFKA_INPUT_TOPIC}")
df_kafka = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_INPUT_TOPIC) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# --- Process Stream ---
# Select the 'value' column, cast to string, and parse JSON
df_parsed = df_kafka.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), kafka_schema).alias("data")) \
    .select("data.*")

# Apply NER UDF to the 'description' or 'content' field (choose one or combine)
# Using 'description' here as 'content' might be None/truncated
df_entities = df_parsed.withColumn("entities", extract_entities_udf(col("description"))) \
    .filter(col("entities").isNotNull()) # Filter out rows where NER couldn't run

# Explode the array of entities into individual rows
df_exploded = df_entities.select(explode(col("entities")).alias("entity"))

# Calculate running counts of each entity
df_counts = df_exploded.groupBy("entity").agg(count("*").alias("count"))

# --- Write Stream to Kafka ---
print(f"Writing counts to Kafka topic: {KAFKA_OUTPUT_TOPIC}")
# Format the output for Kafka: key=entity, value=JSON(entity, count)
query = df_counts \
    .selectExpr("CAST(entity AS STRING) AS key", "to_json(struct(*)) AS value") \
    .writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("topic", KAFKA_OUTPUT_TOPIC) \
    .option("checkpointLocation", "/tmp/spark_checkpoint_news_entities") \
    .outputMode("update") \
    .start()

print("Streaming query started. Waiting for termination...")
query.awaitTermination()
print("Streaming query terminated.")
