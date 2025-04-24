# Use the official Bitnami Spark image as base
FROM bitnami/spark:3.4

# Switch to root user to install packages
USER root

# Install pip for Python3 and copy requirements
RUN apt-get update && \
    apt-get install -y python3-pip && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/bitnami/spark/app/requirements.txt

# Install Python dependencies
# Note: findspark is not needed inside the Spark container
RUN pip install --no-cache-dir -r /opt/bitnami/spark/app/requirements.txt

# Download the default spaCy English model
# This avoids downloading it dynamically during the first run
RUN python3 -m spacy download en_core_web_sm

# Copy the consumer script into the image
COPY consumer.py /opt/bitnami/spark/app/consumer.py

# Change back to the default non-root user
USER 1001

# Set working directory (optional, but good practice)
WORKDIR /opt/bitnami/spark

