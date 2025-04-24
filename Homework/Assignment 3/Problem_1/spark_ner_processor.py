from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr, udf, explode, count, struct, to_json
from pyspark.sql.types import StructType, StructField, StringType, ArrayType
import spacy
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_INPUT_TOPIC = 'news_topic'       # Topic to read raw news from
KAFKA_OUTPUT_TOPIC = 'ner_results_topic' # Topic to write NER counts to
CHECKPOINT_LOCATION = '/tmp/spark_ner_checkpoint' # Checkpoint directory

# --- Load spaCy Model ---
# Load the small English model outside the UDF for efficiency
try:
    nlp = spacy.load('en_core_web_sm')
    logging.info("spaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    logging.error("spaCy model 'en_core_web_sm' not found. ")
    logging.error("Please run: python -m spacy download en_core_web_sm")
    exit(1)

# --- Spark Session ---
def create_spark_session():
    """Creates a Spark session configured for Kafka streaming."""
    try:
        # Note: You might need to adjust the package version based on your Spark/Kafka setup
        # Example for Spark 3.3.x
        kafka_pkg = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0"

        spark = SparkSession.builder \
            .appName("SparkNERStreaming") \
            .config("spark.jars.packages", kafka_pkg) \
            .config("spark.sql.shuffle.partitions", 4) # Adjust based on your cluster size
            .getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        logging.info("Spark session created successfully.")
        return spark
    except Exception as e:
        logging.error(f"Error creating Spark session: {e}")
        return None

# --- Schema Definitions ---
# Schema for incoming Kafka messages (from news_producer.py)
input_schema = StructType([
    StructField("title", StringType(), True),
    StructField("description", StringType(), True),
    StructField("url", StringType(), True),
    StructField("publishedAt", StringType(), True)
])

# --- Named Entity Recognition UDF ---
@udf(returnType=ArrayType(StringType()))
def extract_named_entities(text):
    """UDF to extract named entities using spaCy."""
    if text is None:
        return []
    doc = nlp(text)
    # Extract relevant entities (e.g., ORG, PERSON, GPE)
    # You can customize the entity labels you want to count
    relevant_labels = {'ORG', 'PERSON', 'GPE', 'LOC', 'PRODUCT', 'EVENT'}
    entities = [ent.text for ent in doc.ents if ent.label_ in relevant_labels]
    return entities

# --- Main Processing Logic ---
def process_stream(spark):
    """Reads from Kafka, performs NER, counts entities, and writes back to Kafka."""
    try:
        # Read from Kafka input topic
        kafka_stream_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", KAFKA_INPUT_TOPIC) \
            .option("startingOffsets", "latest") \
            .load()

        # Deserialize JSON values from Kafka
        news_df = kafka_stream_df.selectExpr("CAST(value AS STRING)") \
            .select(from_json(col("value"), input_schema).alias("data")) \
            .select("data.*")

        # Combine title and description for NER
        news_df = news_df.withColumn("text", expr("concat_ws(' ', title, description)"))

        # Apply NER UDF
        entities_df = news_df.withColumn("entities", extract_named_entities(col("text")))

        # Explode entities array to have one row per entity
        exploded_entities_df = entities_df.select(explode(col("entities")).alias("entity"))

        # Calculate running count of each entity
        # Use groupBy and count
        entity_counts_df = exploded_entities_df.groupBy("entity").count()

        # Prepare data for Kafka output (key=entity, value=JSON{entity, count})
        # Kafka expects key and value columns (both usually strings or binary)
        output_df = entity_counts_df \
            .select(
                col("entity").alias("key"), # Use entity as key
                to_json(struct(col("entity"), col("count"))).alias("value") # Value as JSON string
            )

        # Write the aggregated counts to the output Kafka topic
        query = output_df.writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
            .option("topic", KAFKA_OUTPUT_TOPIC) \
            .option("checkpointLocation", CHECKPOINT_LOCATION) \
            .outputMode("update") # Output only updated counts
            .start()
        logging.info(f"Streaming query started. Writing NER counts to Kafka topic '{KAFKA_OUTPUT_TOPIC}'.")
        logging.info(f"Checkpoint location: {CHECKPOINT_LOCATION}")
        query.awaitTermination()

    except Exception as e:
        logging.error(f"Error during stream processing: {e}")
    finally:
        logging.info("Stopping Spark session.")
        spark.stop()

# --- Entry Point ---
if __name__ == "__main__":
    spark_session = create_spark_session()
    if spark_session:
        process_stream(spark_session)
    else:
        logging.error("Failed to initialize Spark session. Exiting.")
