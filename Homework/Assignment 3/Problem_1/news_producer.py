import time
import json
from kafka import KafkaProducer
from newsapi import NewsApiClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
NEWS_API_KEY = 'Yae0b819414cc450daf77055b9de139b9'  # Replace with your NewsAPI key
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'news_topic'
FETCH_INTERVAL_SECONDS = 300  # Fetch news every 5 minutes

def create_kafka_producer(bootstrap_servers):
    """Creates a Kafka producer instance."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # Ensure messages are received by all replicas
            retries=3    # Retry sending messages up to 3 times
        )
        logging.info("Kafka producer connected successfully.")
        return producer
    except Exception as e:
        logging.error(f"Failed to connect Kafka producer: {e}")
        return None

def fetch_news(api_client):
    """Fetches top headlines from NewsAPI."""
    try:
        # Fetch top headlines from major US sources
        top_headlines = api_client.get_top_headlines(
            language='en',
            country='us',
            page_size=100 # Fetch more articles per request
        )
        logging.info(f"Fetched {len(top_headlines.get('articles', []))} articles.")
        return top_headlines.get('articles', [])
    except Exception as e:
        logging.error(f"Error fetching news: {e}")
        return []

def send_to_kafka(producer, topic, articles):
    """Sends articles to the specified Kafka topic."""
    if not producer:
        logging.error("Kafka producer is not available. Cannot send messages.")
        return

    count = 0
    for article in articles:
        # We can send the whole article or just relevant parts
        # Sending title and description for NER analysis
        message = {
            'title': article.get('title'),
            'description': article.get('description'),
            'url': article.get('url'),
            'publishedAt': article.get('publishedAt')
        }
        if message['title']: # Send only if there's a title
            try:
                producer.send(topic, value=message)
                count += 1
            except Exception as e:
                logging.error(f"Failed to send message to Kafka: {e}")

    if count > 0:
        producer.flush() # Ensure all messages are sent
        logging.info(f"Sent {count} articles to Kafka topic '{topic}'.")


def main():
    """Main function to fetch news and send to Kafka periodically."""
    if NEWS_API_KEY == 'YOUR_NEWS_API_KEY':
        logging.error("Please replace 'YOUR_NEWS_API_KEY' with your actual NewsAPI key.")
        return

    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    producer = create_kafka_producer(KAFKA_BOOTSTRAP_SERVERS)

    if not producer:
        logging.error("Exiting due to Kafka connection failure.")
        return

    try:
        while True:
            logging.info("Fetching news...")
            articles = fetch_news(newsapi)
            if articles:
                send_to_kafka(producer, KAFKA_TOPIC, articles)
            else:
                logging.info("No articles fetched in this interval.")

            logging.info(f"Sleeping for {FETCH_INTERVAL_SECONDS} seconds...")
            time.sleep(FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Script interrupted by user.")
    finally:
        if producer:
            producer.close()
            logging.info("Kafka producer closed.")

if __name__ == "__main__":
    main()
