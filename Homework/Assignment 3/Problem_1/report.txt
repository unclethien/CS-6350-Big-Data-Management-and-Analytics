## CS-6350 Assignment 3 - Problem 1: Report

### Data Source Explanation

The primary data source for this project is the Finnhub Stock API (finnhub.io). Specifically, we utilize the `finnhub-python` client library to interact with the API within our Python producer script (`finnhub_producer.py`). The producer is currently configured to fetch news articles from the `general_news` endpoint with the 'general' category specified. This endpoint provides recent, general financial and market news articles from various sources aggregated by Finnhub. The producer script includes logic to periodically poll this endpoint, retrieve new articles, filter out any articles that have already been processed (using a set of seen news IDs to ensure uniqueness), and then publish the unique, raw news articles (containing fields like ID, headline, summary, source, datetime) as JSON messages to the `news_raw` Kafka topic.

### Results Interpretation

The goal of visualizing the results in Kibana is to show the frequency counts of significant named entities (primarily organizations like companies, persons, and geopolitical entities/locations) extracted from the processed news articles. By tracking these counts, we aim to identify which entities are being mentioned most often in the recent financial news stream, indicating key subjects of discussion or market focus (e.g., which companies are trending, which public figures are frequently quoted).

Based on the current visualization (as shown in the provided screenshot dated Apr 25, 2025), the entity extraction process is running, but the 'Top 10 Entities' chart requires further refinement for clear interpretation. It currently shows:

1.  A large portion of counts grouped under an 'Other' category, which typically happens in Kibana when aggregating many low-frequency terms.
2.  Several entries in the top list that are not the primary target entity types (ORG, PERSON, GPE), such as percentages ('42%', '5%'), quantities ('40 miles', '800,000'), or date-related terms ('A decade'). While filters are applied to exclude some numerical/percentage values, noise still seems present.
3.  Some relevant entities like 'AbbVie' and 'AI' appear but with relatively low counts compared to the 'Other' category.

This suggests potential areas for improvement:

*   **Refining NER Filtering:** The Spark application (`spark_app.py`) could be enhanced to more strictly filter the extracted entities, ensuring only those with desired labels (e.g., 'ORG', 'PERSON', 'GPE') are counted and sent forward. Entities like 'MONEY', 'PERCENT', 'QUANTITY', 'DATE' might need to be explicitly excluded during the Spark processing stage.
*   **Improving Kibana Visualization:** Further tuning within Kibana, such as adjusting the 'Top N' value, adding more specific exclusion filters, or changing the aggregation method, might help focus the chart on the most relevant named entities.
*   **Evaluating Data Source/Content:** The 'general' news category might contain a wide variety of text, potentially leading to more diverse but less frequent mentions of specific target entities compared to a more focused news source.

Ideally, after these refinements, the visualization would clearly highlight the most frequently mentioned companies, people, and places, providing actionable insights into current financial news trends.
