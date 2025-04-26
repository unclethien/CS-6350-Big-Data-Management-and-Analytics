# CS-6350 Assignment 3 - Problem 1: Real-time News Entity Analysis

This project implements a real-time data pipeline using Kafka, Spark Streaming, and the ELK stack (Elasticsearch, Logstash, Kibana) to analyze named entities in financial news articles fetched from the Finnhub API.

## Components

*   **Zookeeper:** Manages Kafka cluster state.
*   **Kafka:** Message broker for decoupling producer and consumer. Topics used:
    *   `news_raw`: Stores raw news articles fetched from Finnhub.
    *   `entity_counts`: Stores named entity counts processed by Spark.
*   **Finnhub Producer (`finnhub_producer.py`):** Fetches news articles from the Finnhub API (currently configured for `general_news`), ensures uniqueness using a set of seen IDs, and sends them to the `news_raw` Kafka topic.
*   **Spark Streaming (`spark_app.py`):** Consumes news articles from `news_raw`, uses spaCy for Named Entity Recognition (NER), counts entity occurrences within processing windows, and sends the counts to the `entity_counts` Kafka topic.
*   **Logstash (`logstash.conf`):** Consumes entity counts from the `entity_counts` Kafka topic and indexes them into Elasticsearch.
*   **Elasticsearch:** Stores and indexes the named entity counts for searching and analysis.
*   **Kibana:** Provides a web interface for visualizing the entity counts stored in Elasticsearch.

## Setup

1.  **Prerequisites:**
    *   Docker and Docker Compose installed.
    *   Python 3.x

2.  **Environment Variables:**
    *   Create a `.env` file in the `Problem_1` directory.
    *   Add your Finnhub API key:
        ```
        FINNHUB_API_KEY=YOUR_FINNHUB_API_KEY
        ```
    *   Replace `YOUR_FINNHUB_API_KEY` with your actual key.

3.  **Build Docker Images (if necessary):**
    *   Docker Compose will typically build the images on the first run if they don't exist. If you modify Dockerfiles, you might need to rebuild:
        ```bash
        docker-compose build
        ```

## Running the Pipeline

1.  **Start Services:**
    *   Open a terminal in the `Problem_1` directory.
    *   Run the following command to start all services in detached mode:
        ```bash
        docker-compose up -d
        ```

2.  **Create Kafka Topics (Required on First Run or After Clearing Volumes):**
    *   Wait a minute for Kafka to stabilize after starting.
    *   Execute the following commands to create the necessary topics:
        ```bash
        docker-compose exec kafka kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic news_raw
        docker-compose exec kafka kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic entity_counts
        ```

3.  **Monitor Logs (Optional):**
    *   Check the news producer:
        ```bash
        docker-compose logs -f news-producer
        ```
    *   Check the Spark application:
        ```bash
        docker-compose logs -f spark-streaming
        ```
    *   Check Logstash:
        ```bash
        docker-compose logs -f logstash
        ```

4.  **Access Kibana:**
    *   Open your web browser and navigate to [http://localhost:5601](http://localhost:5601).
    *   Configure an index pattern (e.g., `logstash-*`) to view the entity count data.
    *   Use the "Discover" tab to see raw data or create visualizations (e.g., bar charts, tag clouds) in the "Visualize" and "Dashboard" tabs.

5.  **Stopping the Pipeline:**
    *   To stop all running services:
        ```bash
        docker-compose down
        ```
    *   To stop services and remove associated volumes (clears Kafka data, Zookeeper state, etc.):
        ```bash
        docker-compose down -v
        ```

## Data Flow

1.  `finnhub_producer.py` fetches news from Finnhub API.
2.  Producer sends unique news articles (JSON) to Kafka topic `news_raw`.
3.  `spark_app.py` reads from `news_raw`.
4.  Spark performs NER on news text, counts entities.
5.  Spark sends entity counts (JSON) to Kafka topic `entity_counts`.
6.  Logstash reads from `entity_counts`.
7.  Logstash sends data to Elasticsearch.
8.  Kibana reads from Elasticsearch for visualization.

## Troubleshooting

*   **Kafka/Zookeeper Issues:** If services fail to start correctly, especially Kafka, try clearing Docker volumes to remove potentially corrupted state:
    ```bash
    docker-compose down -v
    docker-compose up -d
    # Remember to recreate Kafka topics after clearing volumes!
    ```
*   **No Data in Kibana:**
    *   Check `news-producer` logs: Is it fetching news? Are there API errors (check `.env` key)?
    *   Check Kafka `news_raw` topic: Use a console consumer (`docker-compose exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic news_raw --from-beginning`) to see if data arrives.
    *   Check `spark-streaming` logs: Are there processing errors? Is it reading from `news_raw`?
    *   Check Kafka `entity_counts` topic: Use a console consumer (`docker-compose exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic entity_counts --from-beginning`) to see if entity counts arrive.
    *   Check `logstash` logs: Are there connection errors to Kafka or Elasticsearch?
    *   Check Elasticsearch: Ensure it's running and receiving data.
    *   Check Kibana index pattern: Ensure it's correctly configured to match the Logstash index.
*   **Producer Skipping All News:** Ensure the producer isn't stuck fetching the same old data block. The current version fetches recent general news and uses `seen_news_ids` to handle duplicates correctly.
