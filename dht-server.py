import time
import logging
import board
import adafruit_dht
from flask import Flask, jsonify
from waitress import serve

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to include detailed logs
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # Logs to console
    ]
)

# Initialize the DHT22 sensor
logging.info("Initializing DHT22 sensor on pin D4...")
dht_device = adafruit_dht.DHT22(board.D4)

# Create the Flask app
app = Flask(__name__)

# Cache variables
cached_data = None
cache_timestamp = 0
CACHE_DURATION = 5  # Cache duration in seconds

def read_sensor():
    """Read temperature and humidity from the sensor with retries."""
    for attempt in range(1, 4):  # Retry up to 3 times
        try:
            logging.debug(f"Attempt {attempt}: Reading from DHT22 sensor...")
            # Read temperature and humidity from the sensor
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            logging.info(f"Successfully read from sensor: Temperature={temperature}°C, Humidity={humidity}%")
            return {
                "temperature_celsius": temperature,
                "humidity": humidity
            }
        except RuntimeError as error:
            logging.warning(f"Attempt {attempt} failed: {error}")
            if attempt < 3:
                logging.debug("Retrying in 2 seconds...")
                time.sleep(2)
    # If all retries fail, raise an exception
    logging.error("Failed to read from the DHT sensor after 3 retries.")
    raise RuntimeError("Failed to read from the DHT sensor after 3 retries.")

@app.route('/sensor', methods=['GET'])
def get_sensor_data():
    global cached_data, cache_timestamp

    # Check if the cached data is still valid
    if time.time() - cache_timestamp < CACHE_DURATION:
        logging.debug("Returning cached data.")
        return jsonify(cached_data)

    try:
        # Read new data from the sensor
        logging.debug("Cache expired, reading new data from sensor...")
        data = read_sensor()
        # Update the cache
        cached_data = data
        cache_timestamp = time.time()
        logging.info("Updated cache with new sensor data.")
        return jsonify(data)
    except RuntimeError as error:
        logging.error(f"Error reading sensor data: {error}")
        return jsonify({"error": str(error)}), 500

if __name__ == '__main__':
    logging.info("Starting the server on host 0.0.0.0 and port 7124...")
    serve(app, host="0.0.0.0", port=7124)
