import time
import json
import threading
import pandas as pd
import matplotlib.pyplot as plt
from kafka import KafkaConsumer

# --- Configuration ---
KAFKA_BROKER = 'localhost:9094'
KAFKA_TOPIC = 'news-entities'
GROUP_ID = 'entity-visualizer-group' # Unique consumer group ID
PLOT_INTERVALS_MINUTES = [15, 30, 45, 60] # Intervals to generate plots
PLOT_INTERVALS_SECONDS = [m * 60 for m in PLOT_INTERVALS_MINUTES]
TOP_N = 10 # Number of top entities to plot

# --- State ---
entity_counts = {} # Dictionary to store aggregated counts {entity: count}
lock = threading.Lock() # To safely update counts from the consumer thread
start_time = time.time()
plot_timers = []

# --- Plotting Function ---
def generate_plot(interval_minutes):
    print(f"--- Generating plot for {interval_minutes} minutes ---")
    with lock:
        if not entity_counts:
            print("No entity data received yet. Skipping plot.")
            return

        # Create DataFrame for easier sorting/plotting
        df = pd.DataFrame(list(entity_counts.items()), columns=['Entity', 'Count'])
        df = df.sort_values(by='Count', ascending=False).head(TOP_N)

    if df.empty:
        print("Entity data exists but is empty after filtering? Skipping plot.")
        return

    # Create the plot
    plt.figure(figsize=(12, 7))
    plt.bar(df['Entity'], df['Count'])
    plt.xlabel("Named Entity")
    plt.ylabel("Frequency Count")
    plt.title(f"Top {TOP_N} Named Entities after {interval_minutes} Minutes")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Save the plot
    filename = f"top_entities_{interval_minutes}min.png"
    plt.savefig(filename)
    print(f"Plot saved as {filename}")
    plt.close() # Close the plot figure to free memory

# --- Kafka Consumer ---
def consume_messages():
    print("Starting Kafka consumer...")
    consumer = None
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=[KAFKA_BROKER],
                auto_offset_reset='earliest', # Start from the beginning of the topic
                group_id=GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000 # Timeout to allow checking loop condition
            )
            print(f"Successfully connected to Kafka topic '{KAFKA_TOPIC}'.")
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}. Retrying in 10 seconds...")
            time.sleep(10)

    print("Consuming messages...")
    try:
        for message in consumer:
            try:
                data = message.value
                entity = data.get('entity')
                count = data.get('count', 0) # Should always be present from Spark

                if entity and isinstance(count, int):
                    with lock:
                        entity_counts[entity] = entity_counts.get(entity, 0) + count
                        # Optional: print(f"Updated count for {entity}: {entity_counts[entity]}")
                else:
                    print(f"Skipping invalid message: {data}")

            except json.JSONDecodeError:
                print(f"Failed to decode JSON: {message.value}")
            except Exception as e:
                print(f"Error processing message {message.value}: {e}")

    except KeyboardInterrupt:
        print("Consumer interrupted.")
    finally:
        if consumer:
            consumer.close()
            print("Kafka consumer closed.")

# --- Main Execution ---
if __name__ == "__main__":
    # Start consumer in a separate thread
    consumer_thread = threading.Thread(target=consume_messages, daemon=True)
    consumer_thread.start()

    # Schedule plots using timers
    for i, interval_sec in enumerate(PLOT_INTERVALS_SECONDS):
        interval_min = PLOT_INTERVALS_MINUTES[i]
        timer = threading.Timer(interval_sec, generate_plot, args=[interval_min])
        plot_timers.append(timer)
        timer.start()
        print(f"Plot scheduled for {interval_min} minutes ({interval_sec} seconds)")

    print(f"Visualizer started. Waiting for plot intervals ({', '.join(map(str, PLOT_INTERVALS_MINUTES))} mins)...")
    print("Press Ctrl+C to stop.")

    # Keep the main thread alive until the last plot is scheduled or interrupted
    try:
        # Wait for the last timer to finish (or slightly beyond)
        if plot_timers:
            plot_timers[-1].join()
            # Add a small buffer in case the last plot takes time
            time.sleep(10)
        else:
             # If no timers, just wait for interrupt
             while True: time.sleep(1)

    except KeyboardInterrupt:
        print("Main thread interrupted. Stopping...")
    finally:
        # Cancel any pending timers if stopped early
        for timer in plot_timers:
            timer.cancel()
        print("Plot timers cancelled.")
        # Consumer thread will exit as it's a daemon or via its own KeyboardInterrupt

    print("Visualizer finished.")
