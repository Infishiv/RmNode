import time
import logging
import AWSIoTPythonSDK
from pathlib import Path
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

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

    def _configure_mqtt_client(self, broker, cert_folder, node_id):
        cert_path = Path(cert_folder)
        cert = cert_path.joinpath(f"{node_id}.crt").absolute()
        key = cert_path.joinpath(f"{node_id}.key").absolute()
        root_ca = cert_path.joinpath("root.pem").absolute()

        self.mqtt_client.configureEndpoint(broker, PORT)
        self.mqtt_client.configureCredentials(str(root_ca), str(key), str(cert))
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