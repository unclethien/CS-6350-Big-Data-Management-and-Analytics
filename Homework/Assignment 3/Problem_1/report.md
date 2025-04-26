## Assignment 3 - Problem 1: Report

### Where the Data Comes From

We get financial news articles using the Finnhub API (via the `finnhub-python` library). Our script (`finnhub_producer.py`) fetches general news, makes sure we haven't seen the article before, and sends the raw news data (like headline, summary, source) to a Kafka topic called `news_raw`.

### Interpreting the Results

The main goal is to see which named entities (like companies, people, or places) are mentioned most often in the news. We use Kibana to visualize the counts of these entities extracted by Spark.

Looking at the Kibana 'Top 10 Entities' visualization (from `Top 10 Entities Result.png`):

*   The chart shows the entities that appeared most frequently in the processed news articles during the observed time period.
*   We can see specific company names like **AbbVie** appearing, indicating they were subjects of recent news.
*   Concepts like **AI** also show up, reflecting its common discussion point in the financial sector.
*   There's still an **'Other'** category, grouping less frequent entities, which is common in this type of analysis.
*   Some less relevant items (like percentages or date fragments, e.g., 'A decade', '5%') might still appear, suggesting the entity filtering in Spark could be further refined to focus only on organizations, people, and locations (ORG, PERSON, GPE labels).

### Potential Improvements

*   **Better Filtering:** Make the Spark job (`spark_app.py`) stricter about which entity types (like ORG, PERSON, GPE) it counts, ignoring others like MONEY, PERCENT, DATE.
*   **Kibana Tweaks:** Fine-tune the Kibana visualization (e.g., adjust 'Top N', add filters) to better highlight the key entities.

Overall, the visualization gives a snapshot of trending topics and entities in financial news, though filtering could be improved for cleaner results.
