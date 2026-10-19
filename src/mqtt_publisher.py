import os
import json
import logging
import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MQTT_MODE = os.getenv("MQTT_MODE", "local")
SITE_ID = os.getenv("SITE_ID", "demo_site_001")

TOPIC_TELEMETRY = f"solar/site/{SITE_ID}/telemetry"
TOPIC_STATUS = f"solar/site/{SITE_ID}/status"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        # Publish online status upon connection
        logger.info("Connected to MQTT broker successfully.")
        client.publish(TOPIC_STATUS, json.dumps({"online": True}), qos=1, retain=True)

    else:
        logger.error(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, flags, rc, properties=None):
    logger.warning(f"Disconnected with result code: {rc}. Attempting reconnection...")

def create_mqtt_client():
    # Using CallbackAPIVersion.VERSION2 for modern paho-mqtt versions
    client = mqtt.Client(client_id=f"publisher_{SITE_ID}", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    
    # Configure Last Will and Testament (LWT)
    client.will_set(TOPIC_STATUS, payload=json.dumps({"online": False}), qos=1, retain=True)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if MQTT_MODE == "aws":
        aws_endpoint = os.getenv("AWS_IOT_ENDPOINT")
        ca_path = os.getenv("AWS_CA_PATH")
        cert_path = os.getenv("AWS_CERT_PATH")
        key_path = os.getenv("AWS_KEY_PATH")
        
        client.tls_set(ca_certs=ca_path, certfile=cert_path, keyfile=key_path)
        client.connect(aws_endpoint, 8883, keepalive=60)
    else:
        # Default to local broker
        client.connect("localhost", 1883, keepalive=60)

    return client

def publish(record: dict):
    """
    Publishes a single normalized record to the MQTT broker.
    Logs failures instead of raising exceptions.
    """
    try:
        client = create_mqtt_client()
        client.loop_start()
        
        payload = json.dumps(record)
        info = client.publish(TOPIC_TELEMETRY, payload, qos=1, retain=False)
        info.wait_for_publish()
        
        logger.info(f"Published message ID {info.mid} to {TOPIC_TELEMETRY}")
        
        client.loop_stop()
        client.disconnect()
        return True
    except Exception as e:
        logger.error(f"Failed to publish MQTT message: {e}")
        return False
