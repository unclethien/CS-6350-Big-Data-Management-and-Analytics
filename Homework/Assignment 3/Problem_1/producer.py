import os
import time
import json
from kafka import KafkaProducer
from newsapi import NewsApiClient
from dotenv import load_dotenv

# Load environment variables from .env file (optional, good practice)
load_dotenv()

# --- Configuration ---
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
KAFKA_BROKER = 'localhost:9094'  # Kafka broker address (host port)
KAFKA_TOPIC = 'raw-news'        # Kafka topic to send data to
QUERY = 'technology'             # News query
FETCH_INTERVAL_SECONDS = 10      # Fetch news every 10 seconds (adjust as needed)

# --- Input Validation ---
if not NEWS_API_KEY:
    raise ValueError("NEWS_API_KEY environment variable not set.")

# --- Initialize Clients ---
print("Initializing NewsAPI client...")
newsapi = NewsApiClient(api_key=NEWS_API_KEY)

print(f"Connecting to Kafka broker at {KAFKA_BROKER}...")
producer = None
while producer is None:
    try:
        # Use json serializer
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5, # Retry sending messages
            linger_ms=100 # Batch messages slightly
        )
        print("Successfully connected to Kafka.")
    except Exception as e:
        print(f"Failed to connect to Kafka: {e}. Retrying in 10 seconds...")
        time.sleep(10)

# --- Main Loop ---
def send_to_kafka(article):
    try:
        # Send article data as JSON
        producer.send(KAFKA_TOPIC, value=article)
        print(f"Sent article to Kafka: {article.get('title', 'N/A')[:50]}...")
        producer.flush() # Ensure messages are sent
    except Exception as e:
        print(f"Error sending article to Kafka: {e}")
        # Optional: Add logic to attempt reconnection if producer fails

print("Starting news fetching loop...")
while True:
    try:
        # --- NewsAPI Fetching ---
        print(f"Fetching news for query: '{QUERY}'...")
        top_headlines = newsapi.get_top_headlines(
            # q=QUERY, # Keep commented for now to get general headlines
            language='en'
            # sort_by='publishedAt'
            # page_size=20
        )
        articles = top_headlines.get('articles', [])
        print(f"Fetched {len(articles)} articles.")
        if articles:
            for article in articles:
                # Select relevant fields
                data_to_send = {
                    'source': article.get('source', {}).get('name'),
                    'author': article.get('author'),
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'url': article.get('url'),
                    'publishedAt': article.get('publishedAt'),
                    'content': article.get('content')
                }
                send_to_kafka(data_to_send)
        else:
            print("No articles found for this query in this fetch.")

    except Exception as e:
        print(f"An error occurred during news fetching or processing: {e}")

    print(f"Sleeping for {FETCH_INTERVAL_SECONDS} seconds...")
    time.sleep(FETCH_INTERVAL_SECONDS)

# Note: This script runs indefinitely. You'll need to stop it manually (Ctrl+C).
