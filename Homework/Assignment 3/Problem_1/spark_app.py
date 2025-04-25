import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode, current_timestamp, to_json, struct, expr
from pyspark.sql.types import StructType, StructField, StringType, LongType
import spacy

# Load environment variables for Kafka connection and topic names
kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
input_topic = os.getenv("INPUT_TOPIC", "news_raw")
output_topic = os.getenv("OUTPUT_TOPIC", "entity_counts")

# Initialize spaCy English model (small)
nlp = spacy.load("en_core_web_sm")

# Define schema of incoming news JSON for parsing
news_schema = StructType([
    StructField("id", LongType(), True),
    StructField("datetime", LongType(), True),
    StructField("headline", StringType(), True),
    StructField("summary", StringType(), True),
    StructField("source", StringType(), True)
])

# Create Spark session with Kafka support
spark = SparkSession.builder.appName("NewsNERStreaming").getOrCreate()

# Read news data from Kafka topic1 as streaming DataFrame
news_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap) \
    .option("subscribe", input_topic) \
    .option("startingOffsets", "earliest") \
    .load()

# Convert the binary 'value' to string and parse JSON
json_df = news_df.selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), news_schema).alias("data")) \
    .select("data.*")  # columns: id, datetime, headline, summary, source

# UDF or function to extract entities from text using spaCy
def extract_entities(text):
    doc = nlp(text)
    # Get all named entities (text) recognized by spaCy
    return [ent.text for ent in doc.ents]

# Register the function as a PySpark UDF returning an array of strings
# (Using pandas UDF for vectorized operation could be an optimization, but simple UDF is okay for now)
from pyspark.sql.functions import udf, array
from pyspark.sql.types import ArrayType
entity_udf = udf(lambda text: extract_entities(text), ArrayType(StringType()))

# Combine headline and summary into one text field (some summaries might be None)
text_df = json_df.withColumn(
    "text",
    expr("CASE WHEN summary IS NOT NULL THEN CONCAT(headline, '. ', summary) ELSE headline END")
)
# Extract entities as an array
entities_df = text_df.withColumn("entities", entity_udf(col("text")))

# Explode the array of entities into individual rows, filter out empty results
entity_exploded = entities_df.select("id", explode(col("entities")).alias("entity"))
# We can optionally filter by entity type or length (e.g., drop very short strings or purely numeric entities)
# For simplicity, let's remove empty entity strings or one-character artifacts:
entity_exploded = entity_exploded.filter(col("entity").rlike(r'\w'))

# Aggregate over all data seen (running counts per entity)
entity_counts = entity_exploded.groupBy("entity").count()

# Add a timestamp for when the count is computed (to help Kibana time-based index)
result_df = entity_counts.withColumn("timestamp", current_timestamp())

# Convert to JSON string for output to Kafka
output_df = result_df.select(to_json(struct(col("entity"), col("count"), col("timestamp"))).alias("value"))

# Write the output stream to Kafka topic2
query = output_df.writeStream.format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap) \
    .option("topic", output_topic) \
    .option("checkpointLocation", "/tmp/spark-checkpoint") \
    .outputMode("complete") \
    .start()

query.awaitTermination()
