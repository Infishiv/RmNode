import time
import logging
import os
from pathlib import Path
import AWSIoTPythonSDK
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json

PORT = 443
OPERATION_TIMEOUT = 10
CONNECT_DISCONNECT_TIMEOUT = 5


class MQTTOperationsException(Exception):
    """Class to handle MQTTOperations method exceptions."""

class MQTTOperations:
    """Class to handle MQTT operations by node"""
    
    def __init__(self, **kwargs):
        self.broker = kwargs['broker']
        self.node_id = kwargs['node_id']
        cert_folder = kwargs.get('cert_folder', 'certs')

        # Resolve absolute certificate path
        cert_folder = Path(cert_folder)
        if not cert_folder.is_absolute():
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent
            cert_folder = project_root / cert_folder

        self.cert_folder = cert_folder
        self.mqtt_client = AWSIoTMQTTClient(self.node_id)
        self.subscription_messages = {}
        self.old_msgs = {}
        self.logger = logging.getLogger("mqtt_cli")
        self.connected = False

        self._configure_mqtt_client()

    def _configure_mqtt_client(self):
        """Configure MQTT client with certificates and options"""

        cert = self.cert_folder / f"{self.node_id}.crt"
        key = self.cert_folder / f"{self.node_id}.key"
        root_ca = self.cert_folder / "root.pem"

        for f in [cert, key, root_ca]:
            if not f.exists():
                raise MQTTOperationsException(f"Certificate file not found: {f}")

        self.mqtt_client.configureEndpoint(self.broker, PORT)
        self.mqtt_client.configureCredentials(str(root_ca), str(key), str(cert))
        self.mqtt_client.configureConnectDisconnectTimeout(CONNECT_DISCONNECT_TIMEOUT)
        self.mqtt_client.configureMQTTOperationTimeout(OPERATION_TIMEOUT)
        self.mqtt_client.configureOfflinePublishQueueing(-1)
        self.mqtt_client.configureDrainingFrequency(2)

    def connect(self):
        """Connect to MQTT broker with status tracking"""
        try:
            if not self.connected:
                result = self.mqtt_client.connect()
                if result:
                    self.connected = True
                    self.logger.info(f"Connected to broker {self.broker}")
                return result
            return True
        except Exception as e:
            self.connected = False
            raise MQTTOperationsException(f"Failed to connect: {str(e)}")

    def disconnect(self):
        try:
            result = self.mqtt_client.disconnect()
            if result:
                self.connected = False
                self.logger.info(f"Disconnected from broker {self.broker}")
            return result
        except Exception as e:
            raise MQTTOperationsException(f"Failed to disconnect: {str(e)}")

    def is_connected(self):
        """Check if currently connected"""
        return self.connected

    def publish(self, topic, payload, qos=1, retry=2):
        """Publish message with retry logic and optional serialization"""
        try:
            if not self.connected:
                self.connect()

            if not isinstance(payload, (str, int, float, bytearray, type(None))):
                payload = json.dumps(payload)

            for attempt in range(retry + 1):
                try:
                    result = self.mqtt_client.publish(topic, payload, qos)
                    if result:
                        self.logger.info(f"Published to {topic}: {payload}")
                        return PublishResult(success=True)
                    if attempt < retry:
                        time.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == retry:
                        raise
                    time.sleep(2 ** attempt)
            return PublishResult(success=False)
        except Exception as e:
            self.logger.error(f"Publish failed: {str(e)}")
            raise MQTTOperationsException(f"Publish failed: {str(e)}")

    def subscribe(self, topic, qos=1, callback=None):
        try:
            cb = callback or self._on_message
            result = self.mqtt_client.subscribe(topic, qos, cb)
            if result:
                self.logger.info(f"Subscribed to {topic}")
            return result
        except Exception as e:
            raise MQTTOperationsException(f"Subscribe failed: {str(e)}")

    def unsubscribe(self, topic):
        try:
            result = self.mqtt_client.unsubscribe(topic)
            if result:
                self.logger.info(f"Unsubscribed from {topic}")
            return result
        except Exception as e:
            raise MQTTOperationsException(f"Unsubscribe failed: {str(e)}")

    def _on_message(self, client, userdata, message):
        self.subscription_messages[message.topic] = message.payload
        self.logger.info(f"Received on {message.topic}: {message.payload}")
        self.old_msgs.setdefault(message.topic, []).append(message.payload) 


class PublishResult:
    def __init__(self, success=True):
        self._published = success

    def wait_for_publish(self, timeout=None):
        return True

    def is_published(self):
        return self._published
