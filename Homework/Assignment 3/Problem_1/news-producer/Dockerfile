# Problem_1/news-producer/Dockerfile
FROM python:3.9-slim
WORKDIR /app
# Install required Python libraries: finnhub client and kafka client
RUN pip install finnhub-python==2.4.23 kafka-python==2.0.2
COPY finnhub_producer.py /app/
CMD ["python", "finnhub_producer.py"]
