import os, time, json, sys
import finnhub
from kafka import KafkaProducer
from datetime import datetime, timedelta

# Load configuration from environment
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
NEWS_TOPIC = os.getenv("NEWS_TOPIC", "news_raw")

print(f"Using Finnhub API key: {FINNHUB_API_KEY[:5] if FINNHUB_API_KEY else 'None'}...")
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

# Set to store already seen news IDs to avoid duplicates
seen_news_ids = set()

while True:
    # Calculate dates dynamically within the loop for a rolling window
    today = datetime.now()
    yesterday = today - timedelta(days=1) # Fetch news from the last day
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    news_list = []
    
    # Use general_news instead of company_news
    try:
        print("Attempting to fetch general market news...")
        # Fetch general news (no date parameter needed for general_news)
        news_list = finnhub_client.general_news('general')
        print(f"Fetched {len(news_list)} general news items")
    except Exception as e:
        print(f"Error with general_news: {e}")
        time.sleep(5)
        continue

    if news_list:
        print(f"Processing {len(news_list)} news items")
        # Sort news by ID just in case (to send in order)
        try:
            news_list.sort(key=lambda x: x.get('id', 0))
        except Exception as e:
            print(f"Error sorting news: {e}")
            # Continue with unsorted list
            
        # Track how many new items we process
        new_items_count = 0
            
        for item in news_list:
            try:
                news_id = item.get('id', 'unknown-' + str(time.time()))
                
                # Skip if we've already seen this news ID
                if news_id in seen_news_ids:
                    print(f"Skipping already processed news ID {news_id}")
                    continue
                    
                # Add to seen IDs set
                seen_news_ids.add(news_id)
                new_items_count += 1
                
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
                
        print(f"Processed {new_items_count} new news items (skipped {len(news_list) - new_items_count} duplicates)")
        
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
