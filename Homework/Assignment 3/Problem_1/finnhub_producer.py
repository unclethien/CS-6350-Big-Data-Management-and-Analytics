import os, time, json, sys
import finnhub
from kafka import KafkaProducer

# Load configuration from environment
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
NEWS_TOPIC = os.getenv("NEWS_TOPIC", "news_raw")

print(f"Using Finnhub API key: {FINNHUB_API_KEY[:5]}...")
print(f"Using Kafka server: {KAFKA_SERVER}")
print(f"Using News topic: {NEWS_TOPIC}")

# Initialize Finnhub client
try:
    finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
    print("Finnhub client initialized successfully")
except Exception as e:
    print(f"Error initializing Finnhub client: {e}")
    sys.exit(1)

# Initialize Kafka producer (JSON messages)
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_SERVER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    print("Kafka producer initialized successfully")
except Exception as e:
    print(f"Error initializing Kafka producer: {e}")
    sys.exit(1)

last_id = 0  # track last seen news ID to fetch only new news
print("Starting Finnhub news producer...")

# Try to verify the API key by making a simple request
try:
    print("Testing Finnhub API connection...")
    # Try a simple API call to verify connectivity
    test_response = finnhub_client.symbol_lookup('AAPL')
    print(f"API test response: {test_response}")
except Exception as e:
    print(f"Error testing Finnhub API: {e}")
    # Continue anyway, the main loop will retry

while True:
    try:
        print("Attempting to fetch news...")
        # Try different approaches to fetch news
        try:
            # Approach 1: General news
            news_list = finnhub_client.general_news('general', min_id=last_id)
            print(f"Fetched {len(news_list)} news items using general_news")
        except Exception as e1:
            print(f"Error with general_news: {e1}")
            try:
                # Approach 2: Market news
                news_list = finnhub_client.market_news('general')
                print(f"Fetched {len(news_list)} news items using market_news")
            except Exception as e2:
                print(f"Error with market_news: {e2}")
                # Approach 3: Company news (for a popular stock)
                news_list = finnhub_client.company_news('AAPL', _from="2023-01-01", to="2023-12-31")
                print(f"Fetched {len(news_list)} news items using company_news")
    except Exception as e:
        print(f"Error fetching news (all methods): {e}")
        time.sleep(10)
        continue

    if news_list:
        print(f"Processing {len(news_list)} news items")
        # Sort news by ID just in case (to send in order)
        try:
            news_list.sort(key=lambda x: x.get('id', 0))
        except Exception as e:
            print(f"Error sorting news: {e}")
            # Continue with unsorted list
            pass
            
        for item in news_list:
            try:
                news_id = item.get('id', 'unknown-' + str(time.time()))
                # Update last_id to the highest ID seen so far if it's a numeric ID
                if isinstance(news_id, (int, float)) and news_id > last_id:
                    last_id = news_id
                # Prepare the data payload (select fields of interest)
                payload = {
                    "id": news_id,
                    "datetime": item.get('datetime'),
                    "headline": item.get('headline', 'No headline'),
                    "summary": item.get('summary', 'No summary'),
                    "source": item.get('source', 'Unknown')
                }
                # Send to Kafka topic
                producer.send(NEWS_TOPIC, value=payload)
                print(f"Sent news ID {news_id} to topic {NEWS_TOPIC}")
            except Exception as e:
                print(f"Error processing news item: {e}")
                continue
        
        try:
            producer.flush()
            print("Successfully flushed messages to Kafka")
        except Exception as e:
            print(f"Error flushing messages: {e}")
    else:
        print("No news items found in this fetch")
        
    # Wait for a short interval before polling again
    print(f"Waiting 30 seconds before next fetch...")
    time.sleep(30)
