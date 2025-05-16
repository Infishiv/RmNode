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
        broker = kwargs['broker']
        cert_folder = kwargs.get('cert_folder', 'certs')
        node_id = kwargs['node_id']
        self.broker = broker
        self.node_id = node_id
        self.mqtt_client = AWSIoTMQTTClient(node_id)
        self.subscription_messages = {}
        self._configure_mqtt_client(broker, cert_folder, node_id)
        self.logger = logging.getLogger("mqtt_cli")
        self.old_msgs = {}
        self.connected = False

    def _configure_mqtt_client(self, broker, cert_folder, node_id):
        """Configure MQTT client with proper certificate paths"""
        # Convert to absolute paths
        cert_folder = Path(cert_folder).absolute()
        
        # Define expected certificate files
        cert_files = {
            'cert': cert_folder / f"{node_id}.crt",
            'key': cert_folder / f"{node_id}.key",
            'root_ca': cert_folder / "root.pem"
        }

        # Verify all certificate files exist
        for name, path in cert_files.items():
            if not path.exists():
                raise MQTTOperationsException(f"Certificate file not found: {path}")

        # Configure MQTT client
        self.mqtt_client.configureEndpoint(broker, PORT)
        self.mqtt_client.configureCredentials(
            str(cert_files['root_ca']),
            str(cert_files['key']),
            str(cert_files['cert'])
        )
        self.mqtt_client.configureConnectDisconnectTimeout(CONNECT_DISCONNECT_TIMEOUT)
        self.mqtt_client.configureMQTTOperationTimeout(OPERATION_TIMEOUT)
        self.mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline queue
        self.mqtt_client.configureDrainingFrequency(2)  # 2 Hz draining frequency

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

    def is_connected(self):
        """Check connection status"""
        return self.connected

    def publish(self, topic, payload, qos=1, retry=2):
        """Publish message with delivery verification"""
        try:
            # Ensure connection
            if not self.connected:
                self.connect()
            
            # Convert payload if needed
            if not isinstance(payload, (bytearray, str, float, type(None), int)):
                payload = json.dumps(payload)
            
            # Publish with retry logic
            for attempt in range(retry + 1):
                try:
                    result = self.mqtt_client.publish(topic, payload, qos)
                    if result:
                        self.logger.info(f"Published to {topic}: {payload}")
                        return True
                    elif attempt < retry:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                except Exception as e:
                    if attempt == retry:
                        raise
                    time.sleep(2 ** attempt)
                    continue
            
            return False
        except Exception as e:
            self.logger.error(f"Publish failed after {retry} attempts: {str(e)}")
            raise MQTTOperationsException(f"Publish failed: {str(e)}")

    # ... (keep other methods unchanged)-----


class MQTTOperations:
    """Class to handle MQTT operations by node"""

    def __init__(self, **kwargs):
        broker = kwargs['broker']
        cert_folder = kwargs.get('cert_folder', 'certs')
        node_id = kwargs['node_id']
        self.broker = broker
        self.node_id = node_id
        self.mqtt_client = AWSIoTMQTTClient(node_id)
        self.subscription_messages = {}
        
        # Convert cert_folder to absolute path
        if not os.path.isabs(cert_folder):
            # Get the directory where this script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the package root
            project_root = os.path.dirname(current_dir)
            # Create absolute path to cert folder
            cert_folder = os.path.join(project_root, cert_folder)
        
        self._configure_mqtt_client(broker, cert_folder, node_id)
        self.logger = logging.getLogger("mqtt_cli")
        self.old_msgs = {}

    def _configure_mqtt_client(self, broker, cert_folder, node_id):
        # Build absolute paths to certificate files
        cert_path = os.path.join(cert_folder, f"{node_id}.crt")
        key_path = os.path.join(cert_folder, f"{node_id}.key")
        root_ca_path = os.path.join(cert_folder, "root.pem")

        # Verify files exist
        for path in [cert_path, key_path, root_ca_path]:
            if not os.path.exists(path):
                raise MQTTOperationsException(f"Certificate file not found: {path}")

        # Configure MQTT client with absolute paths
        self.mqtt_client.configureEndpoint(broker, PORT)
        self.mqtt_client.configureCredentials(
            root_ca_path,  # CA root file path
            key_path,      # Private key path
            cert_path      # Certificate file path
        )
        self.mqtt_client.configureConnectDisconnectTimeout(CONNECT_DISCONNECT_TIMEOUT)
        self.mqtt_client.configureMQTTOperationTimeout(OPERATION_TIMEOUT)

    def connect(self):
        try:
            response = self.mqtt_client.connect()
            if response:
                self.logger.info(f"Connected to broker {self.broker}")
            return response
        except Exception as e:
            raise MQTTOperationsException(f"Failed to connect: {str(e)}")

    def disconnect(self):
        try:
            response = self.mqtt_client.disconnect()
            if response:
                self.logger.info(f"Disconnected from broker {self.broker}")
            return response
        except Exception as e:
            raise MQTTOperationsException(f"Failed to disconnect: {str(e)}")

    def publish(self, topic, payload, qos=1, retry=0):
        try:
            if not isinstance(payload, (bytearray, str, float, type(None), int)):
                payload = str(payload)
            result = self.mqtt_client.publish(topic, payload, qos)
            if result:
                self.logger.info(f"Published to {topic}: {payload}")
            elif retry > 0:
                time.sleep(5)
                return self.publish(topic, payload, qos, retry - 1)
            return result
        except Exception as e:
            raise MQTTOperationsException(f"Publish failed: {str(e)}")

    def _on_message(self, client, userdata, message):
        self.subscription_messages[message.topic] = message.payload
        self.logger.info(f"Received on {message.topic}: {message.payload}")
        msg_queue = self.old_msgs.get(message.topic, [])
        msg_queue.append(message.payload)
        self.old_msgs[message.topic] = msg_queue

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