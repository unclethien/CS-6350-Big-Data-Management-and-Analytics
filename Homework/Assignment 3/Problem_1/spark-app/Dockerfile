# Problem_1/spark-app/Dockerfile
FROM bitnami/spark:3.5.1
USER root
# Install Python dependencies: spaCy (for NER), finnhub-python (if needed inside Spark, possibly not used here), and kafka-python
# Pin numpy<2 first to avoid binary incompatibility issues with compiled extensions (like in thinc)
RUN pip install "numpy<2" && \
    pip install spacy==3.5.0 finnhub-python==2.4.23 kafka-python==2.0.2 && \
    python -m spacy download en_core_web_sm
# Copy the Spark streaming application code
COPY spark_app.py spark_app.py

# Run the Spark Structured Streaming job (with Kafka connector package)
# Using local[*] to utilize all available cores in the container
CMD [ "spark-submit", "--master", "local[*]", \
      "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0", \
      "spark_app.py" ]
