# Problem_1/producer.py
import time
import json
import os
from kafka import KafkaProducer
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
NEWS_API_KEY = os.getenv('NEWS_API_KEY') # Read from environment variable (loaded from .env)

KAFKA_BOOTSTRAP_SERVERS = 'localhost:29092' # Use the external port mapping
KAFKA_TOPIC = 'raw-news'
QUERY = 'news' # Change topic as needed (e.g., 'finance', 'politics', 'business')
FETCH_INTERVAL_SECONDS = 300 # Fetch news every 5 minutes (adjust as needed)
NEWS_API_FROM_MINUTES_AGO = 60 # Fetch news published in the last 60 minutes

# --- Initialization ---
if NEWS_API_KEY is None:
    print("ERROR: NEWS_API_KEY not found. Make sure it's set in your .env file or environment variables.")
    exit(1)

newsapi = NewsApiClient(api_key=NEWS_API_KEY)

# Configure Kafka producer
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all', # Ensure message delivery
        retries=5 # Retry sending messages on failure
    )
    print(f"Kafka Producer connected to {KAFKA_BOOTSTRAP_SERVERS}")
except Exception as e:
    print(f"Error connecting to Kafka: {e}")
    exit(1)

# --- Main Loop ---
def fetch_and_send_news():
    """Fetches news from NewsAPI and sends relevant fields to Kafka."""
    try:
        print(f"Fetching top headlines for query '{QUERY}'...")
        # Use get_top_headlines instead of get_everything
        all_articles = newsapi.get_top_headlines(
            q=QUERY,
            language='en',
            page_size=100 # Get max articles per request
        )

        articles_sent = 0
        if all_articles['status'] == 'ok':
            for article in all_articles['articles']:
                # Select relevant fields (title and description usually contain most entities)
                # Ensure description is not None
                article_text = f"{article.get('title', '')}. {article.get('description', '') or ''}"

                if article_text.strip() and article_text != '. ': # Avoid sending empty messages
                    message = {
                        'source': article['source']['name'] if article.get('source') else 'Unknown',
                        'title': article.get('title'),
                        'description': article.get('description'),
                        'publishedAt': article.get('publishedAt'),
                        'url': article.get('url'),
                        'text_for_ner': article_text # Combine title and description for NER
                    }
                    print(f"Sending article: {message['title']}")
                    producer.send(KAFKA_TOPIC, value=message)
                    articles_sent += 1

            producer.flush() # Ensure messages are sent
            print(f"Sent {articles_sent} articles to Kafka topic '{KAFKA_TOPIC}'.")
        else:
            print(f"Error fetching news: Status '{all_articles.get('status', 'N/A')}', Code: '{all_articles.get('code', 'N/A')}', Message: '{all_articles.get('message', 'Unknown error')}'")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print("Starting NewsAPI producer...")
    while True:
        fetch_and_send_news()
        print(f"Sleeping for {FETCH_INTERVAL_SECONDS} seconds...")
        time.sleep(FETCH_INTERVAL_SECONDS)
