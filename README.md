# Course Homepage

| Topic | Slides | Lab | Reading |
|---|---|---|---|
| 1 | Introduction to Class<br>Introduction to Big Data | | |
| 2 | Introduction to Hadoop | Lab1 | Hadoop the Definitive Guide Chapter 3<br>Data Intensive Text Processing with MapReduce Chapter 2 |
| 3 | Hadoop MapReduce | PySpark Lab 1 | |
| 4 | Apache Spark<br>Information Retrieval using MapReduce | PySpark Lab 2<br>PySpark Lab 3 | RDD Paper |
| 5 | PySpark DataFrames | Data Frame Lab | Spark SQL Paper |
| 6 | Spark MLlib<br>Spark Pipelines | MLlib Lab 1<br>K-Means Lab<br>Recommender Systems Lab | Recommender Systems Paper |
| 7 | | | |
| 8 | Spark GraphX | Lab 1<br>Lab 2 | |
| 9 | Structured Streaming | Kafka Lab | |
| 10 | Apache Hive | Hive Lab | Hive Paper |
| 11 | NoSQL | NoSQL Paper<br>Getting Stated with MongoDB | |
| 12 | MongoDB | MongoDB Lab | |
| 13 | HBase | HBase Lab | |
| 14 | Cassandra | Cassandra_Google_Cloud.pdf<br>Cassandra Lab | Cassandra Paper |
| 15 | Review 1<br>Review 2<br>Review 3 | | |

# Spark Streaming NER with Kafka and ELK Stack

This project demonstrates a real-time data pipeline using Spark Structured Streaming, Kafka, and the ELK stack (Elasticsearch, Logstash, Kibana) to perform Named Entity Recognition (NER) on news headlines fetched from NewsAPI.

## Project Structure

```
.
├── news_producer.py       # Fetches news from NewsAPI and sends to Kafka (topic1)
├── spark_ner_processor.py # Reads from Kafka (topic1), performs NER, writes counts to Kafka (topic2)
├── logstash.conf          # Logstash config to read from Kafka (topic2) and send to Elasticsearch
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Prerequisites

1.  **Java Development Kit (JDK):** Required for Kafka, Spark, and Elasticsearch.
2.  **Python 3.x:** With `pip` for package management.
3.  **Apache Kafka:** Download and install Kafka ([Quickstart](https://kafka.apache.org/quickstart)). Ensure Zookeeper and Kafka brokers are running.
4.  **Apache Spark:** Download and install Spark ([Downloads](https://spark.apache.org/downloads.html)). Set `SPARK_HOME` environment variable.
5.  **Elasticsearch & Kibana:** Download and install Elasticsearch and Kibana ([Downloads](https://www.elastic.co/downloads)). Ensure they are running.
6.  **Logstash:** Download and install Logstash ([Downloads](https://www.elastic.co/downloads/logstash)).
7.  **NewsAPI Key:** Get a free API key from [newsapi.org](https://newsapi.org/).
8.  **spaCy English Model:** Download the small English model: `python -m spacy download en_core_web_sm`

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure NewsAPI Key:**
    Edit `news_producer.py` and replace `'YOUR_NEWS_API_KEY'` with your actual NewsAPI key.
    *Alternatively, for better practice, use environment variables (e.g., create a `.env` file and use `python-dotenv`).*

4.  **Start Services (Order Matters):**
    *   **Zookeeper:** (Comes with Kafka)
        ```bash
        # Navigate to your Kafka installation directory
        bin/zookeeper-server-start.sh config/zookeeper.properties
        ```
    *   **Kafka Broker:** (In a new terminal)
        ```bash
        # Navigate to your Kafka installation directory
        bin/kafka-server-start.sh config/server.properties
        ```
    *   **Create Kafka Topics:** (In a new terminal, if they don't exist)
        ```bash
        # Navigate to your Kafka installation directory
        # Topic for raw news
        bin/kafka-topics.sh --create --topic news_topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
        # Topic for NER results
        bin/kafka-topics.sh --create --topic ner_results_topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
        ```
    *   **Elasticsearch:** (Follow Elastic documentation for startup)
    *   **Kibana:** (Follow Elastic documentation for startup)
    *   **Logstash:** (In a new terminal)
        ```bash
        # Navigate to your Logstash installation directory
        bin/logstash -f /path/to/your/logstash.conf 
        ```
        (Replace `/path/to/your/logstash.conf` with the actual path to `logstash.conf` in this project)

## Running the Pipeline

1.  **Start the News Producer:** (Ensure Kafka is running)
    ```bash
    python news_producer.py
    ```
    This will start fetching news and sending it to the `news_topic` Kafka topic.

2.  **Start the Spark NER Processor:** (Ensure Kafka and Spark environment are set up)
    Submit the Spark job. You need to provide the Spark-Kafka package.
    ```bash
    # Adjust the package version based on your Spark/Scala version
    # Example for Spark 3.3.0 / Scala 2.12
    PACKAGE="org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0"

    spark-submit --packages $PACKAGE spark_ner_processor.py
    ```
    This will read from `news_topic`, process entities, and write counts to `ner_results_topic`.

## Viewing Results in Kibana

1.  Open Kibana in your web browser (usually `http://localhost:5601`).
2.  Go to **Stack Management -> Index Patterns**.
3.  Create an index pattern: `ner-counts-*` (matching the index name in `logstash.conf`). Use `@timestamp` as the time field if available, otherwise select "I don't want to use a time filter".
4.  Go to **Discover** to see the raw JSON data being indexed.
5.  Go to **Visualize Library** -> **Create Visualization**.
6.  Choose **Bar chart**.
7.  Select the `ner-counts-*` index pattern.
8.  Configure the bar chart:
    *   **Y-axis:** Aggregation: `Sum`, Field: `count`.
    *   **X-axis (Buckets):** Aggregation: `Terms`, Field: `entity.keyword` (or just `entity` if not mapped as keyword), Order by: `Metric: Sum of count`, Size: `10` (for top 10).
9.  Click **Update** to see the bar plot of the top 10 named entities and their running counts.
10. Save the visualization and add it to a Dashboard if desired.
11. Take screenshots at different intervals (e.g., 15, 30, 45, 60 minutes) as required by the assignment.

## Report

### Data Source

*(Explain your chosen data source - NewsAPI in this case. Mention the type of data, frequency, and any limitations.)*

NewsAPI was used as the real-time data source. It provides access to recent news articles and headlines from various sources worldwide. For this project, top headlines from the US (language='en', country='us') were fetched every 5 minutes. The API returns articles typically including a title, description, URL, source, and publication timestamp. The free tier has limitations on the number of requests and the age of articles retrievable.

### Results Explanation

*(Explain what your bar plots generated at different intervals indicate. Discuss any trends observed in the named entities, potential reasons for certain entities appearing frequently, etc.)*

*(Placeholder: Add your observations here after running the pipeline and generating the plots. For example:)*

The bar plots show the frequency of named entities (like Organizations, Persons, Locations) mentioned in the news headlines over time. After 15 minutes, entities related to [mention specific event/topic] were prominent. By 60 minutes, the focus might shift, or entities related to ongoing major news stories might dominate. The frequency counts indicate the real-time relevance and discussion volume surrounding specific entities in the news cycle captured by the API during the observation period.
