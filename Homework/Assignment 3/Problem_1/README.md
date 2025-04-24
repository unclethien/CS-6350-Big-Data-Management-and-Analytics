# Problem_1: Real-Time News Entity Analysis Pipeline

This project implements a real-time data pipeline using NewsAPI, Kafka, Spark Structured Streaming, and the ELK stack (Elasticsearch, Logstash, Kibana) to analyze named entities in news articles.

## Components

1.  **NewsAPI Producer (`producer.py`)**: Fetches news articles related to a specific query (default: 'technology') from NewsAPI and sends them to the `raw-news` Kafka topic.
2.  **Kafka**: Message broker used for decoupling the producer and consumer. Runs in Docker.
3.  **Spark Structured Streaming Consumer (`consumer.py`)**: Reads news articles from the `raw-news` topic, extracts named entities (ORG, PERSON, GPE) using spaCy, calculates running counts within time windows, and sends the aggregated counts (entity, count, window start/end) to the `news-entities` Kafka topic. Runs in Docker.
4.  **ELK Stack (Elasticsearch, Logstash, Kibana)**:
    *   **Logstash**: Reads entity counts from the `news-entities` topic, parses them, and sends them to Elasticsearch. Runs in Docker.
    *   **Elasticsearch**: Stores and indexes the entity count data. Runs in Docker.
    *   **Kibana**: Visualizes the entity counts stored in Elasticsearch. Runs in Docker.

## Prerequisites

*   **Docker and Docker Compose**: Install from [Docker's website](https://www.docker.com/get-started).
*   **NewsAPI Key**: Obtain a free API key from [newsapi.org](https://newsapi.org/).
*   **Python 3 & pip**: For running the producer locally.

## Setup

1.  **Clone the repository** (or ensure you have the `Problem_1` folder structure).
2.  **Create `.env` file**: In the `Problem_1` directory, create a file named `.env` and add your NewsAPI key like this:
    ```
    NEWS_API_KEY=YOUR_ACTUAL_API_KEY_HERE
    ```
    Replace `YOUR_ACTUAL_API_KEY_HERE` with your real key.
3.  **Install Python Dependencies (for local producer)**:
    Navigate to the `Problem_1` directory in your terminal and run:
    ```bash
    pip install -r requirements.txt
    pip install python-dotenv
    ```
    *(This installs `newsapi-python`, `kafka-python-ng`, `spacy`, `findspark`, and `python-dotenv`)*
4.  **Directory**: Ensure all subsequent commands are run from the `Problem_1` directory:
    ```bash
    cd /path/to/CS-6350-Big-Data-Management-and-Analytics/Homework/Assignment 3/Problem_1
    ```

## Running the Pipeline

1.  **Start Docker Services (Kafka, Spark, ELK)**:
    ```bash
    docker-compose up -d
    ```
    This will start all services in detached mode. Wait a minute or two for all containers to initialize, especially Elasticsearch and Kafka. You can check logs using `docker-compose logs -f <service_name>` (e.g., `docker-compose logs -f kafka`).

2.  **Create Kafka Topics** (Do this once after Kafka is up):
    Connect to the Kafka container and create the topics:
    ```bash
    # Execute inside the kafka container
    docker exec -it kafka kafka-topics --create --topic raw-news --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
    docker exec -it kafka kafka-topics --create --topic news-entities --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1

    # Verify topics (optional)
    docker exec -it kafka kafka-topics --list --bootstrap-server kafka:9092
    ```

3.  **Submit Spark Job**:
    Submit the `consumer.py` script to the Spark cluster running in Docker:
    ```bash
    docker exec -it spark-master spark-submit \
        --master spark://spark-master:7077 \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
        /opt/bitnami/spark/app/consumer.py
    ```
    Keep this terminal window open to monitor Spark logs, or run it in the background/detached mode if preferred.

4.  **Run the Producer (Locally)**:
    Open a *new* terminal window on your Mac. Navigate back to the `Problem_1` directory.
    ```bash
    # Ensure you are in the Problem_1 directory
    # cd /path/to/CS-6350-Big-Data-Management-and-Analytics/Homework/Assignment 3/Problem_1

    # The producer will automatically load the API key from your .env file.

    # Run the producer
    python producer.py
    ```
    The producer will start fetching news and sending it to Kafka. Keep this running.

## Visualization in Kibana

1.  **Access Kibana**: Open your web browser and go to `http://localhost:5601`.
2.  **Create Data View (formerly Index Pattern)**:
    *   Navigate to "Stack Management" (usually via the main menu / hamburger icon ☰).
    *   Go to "Data Views" under "Kibana".
    *   Click "Create data view".
    *   Enter `news-entities*` as the name and index pattern.
    *   Select `@timestamp` as the Timestamp field.
    *   Click "Save data view to Kibana".
3.  **Create Visualization**:
    *   Navigate to "Visualize Library" (usually via the main menu under "Analytics").
    *   Click "Create visualization".
    *   Choose "Bar" chart (Vertical or Horizontal).
    *   Select the `news-entities*` data view you just created.
    *   **Configure the Chart**:
        *   **Vertical axis / Metrics**: Aggregation: `Sum`, Field: `count`. Label it "Total Count".
        *   **Horizontal axis / Buckets**: Aggregation: `Terms`, Field: `entity.keyword` (use `.keyword` for exact matching). Order by: `Metric: Sum of count`, Order: `Descending`. Size: `10` (for Top 10). Label it "Named Entity".
    *   **Time Range**: Adjust the time picker in the top right corner to see data over different intervals (e.g., Last 15 minutes, Last hour, or specific intervals as required by the assignment).
    *   Click **Update** to refresh the chart.
    *   **Save** the visualization with a descriptive name (e.g., "Top 10 News Entities").

## Taking Screenshots for Submission

Run the pipeline for the required duration (e.g., 60 minutes). Use the Kibana time picker to select the intervals mentioned in the assignment (e.g., after 15, 30, 45, 60 minutes relative to the start time) and take screenshots of the Top 10 bar chart for each interval.

## Stopping the Pipeline

1.  Stop the producer script (`Ctrl+C` in its terminal).
2.  Stop the Spark job (`Ctrl+C` in its terminal, or stop the `docker exec` command if detached).
3.  Stop and remove the Docker containers, network, and volumes:
    ```bash
    docker-compose down -v
    ```
    *(Using `-v` removes the Kafka/Zookeeper state, Elasticsearch data, and Spark checkpoints. Omit `-v` if you want to preserve this data between runs, but be aware of potential state issues.)*

## Customization

*   **News Query**: Change the `QUERY` variable in `producer.py` to fetch news on different topics.
*   **NER Entities**: Modify the `extract_entities` function in `consumer.py` to include/exclude different spaCy entity types (e.g., `NORP`, `LOC`).
*   **Windowing**: Adjust `WINDOW_DURATION`, `SLIDING_INTERVAL`, and `WATERMARK_DELAY` in `consumer.py` to change aggregation behavior.
*   **Resources**: Adjust memory (`*_JAVA_OPTS`, `SPARK_WORKER_MEMORY`) in `docker-compose.yml` if needed, especially if dealing with high data volumes.
