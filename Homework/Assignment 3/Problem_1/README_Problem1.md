# Assignment 3 - Problem 1: Real-time News Entity Analysis

This project analyzes named entities (like organizations, people, locations) from real-time financial news using Kafka, Spark Streaming, and the ELK stack.

## How it Works

1.  **News Fetcher (`finnhub_producer.py`):** Gets latest financial news from the Finnhub API and sends it to a Kafka topic called `news_raw`.
2.  **Spark Analyzer (`spark_app.py`):** Reads news from `news_raw`, uses spaCy to find named entities, counts them, and sends the counts to another Kafka topic `entity_counts`.
3.  **Data Storage (ELK Stack):**
    *   **Logstash:** Listens to `entity_counts` and sends the data to Elasticsearch.
    *   **Elasticsearch:** Stores the entity count data.
    *   **Kibana:** Lets you visualize the entity counts stored in Elasticsearch.

## Setup & Running

1.  **Prerequisites:**
    *   Docker & Docker Compose
    *   Python 3.x

2.  **API Key:**
    *   Create a `.env` file in this directory (`Problem_1`).
    *   Add your Finnhub API key: `FINNHUB_API_KEY=YOUR_KEY_HERE`

3.  **Start Everything:**
    *   Open a terminal here.
    *   Run: `docker-compose up -d`

4.  **Create Kafka Topics (First time only):**
    *   Wait a minute for Kafka to start.
    *   Run these commands:
        ```bash
        docker-compose exec kafka kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic news_raw
        docker-compose exec kafka kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic entity_counts
        ```

5.  **View Results in Kibana:**
    *   Go to [http://localhost:5601](http://localhost:5601) in your browser.
    *   You might need to set up an index pattern (like `logstash-*`) to see the data.
    *   Explore the data in the "Discover" tab or create charts in "Visualize".

6.  **Stop Everything:**
    *   Run: `docker-compose down`
    *   To also remove data volumes (like Kafka messages): `docker-compose down -v`

## Troubleshooting

*   **Services won't start?** Try `docker-compose down -v` to clear old data, then `docker-compose up -d`. **Remember to recreate Kafka topics** if you clear volumes.
*   **No data in Kibana?**
    *   Check producer logs: `docker-compose logs -f news-producer` (API key correct? Fetching news?)
    *   Check Spark logs: `docker-compose logs -f spark-streaming` (Reading from Kafka? Any errors?)
    *   Check Logstash logs: `docker-compose logs -f logstash` (Connecting to Kafka/Elasticsearch?)
    *   Use Kafka console consumers to verify messages are flowing through `news_raw` and `entity_counts` topics.
