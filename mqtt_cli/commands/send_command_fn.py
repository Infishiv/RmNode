import json
import logging
import tlv8
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import from mqtt_cli
sys.path.append(str(Path(__file__).parent.parent))
from mqtt_cli.mqtt_operations import MQTTOperations
from mqtt_cli.utils.cert_finder import get_cert_and_key_paths, get_root_cert_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def json_to_tlv8(json_data):
    """Convert JSON data to TLV8 format using the correct structure"""
    entries = []
    
    for key, value in json_data.items():
        # Convert key to integer (TLV8 type_id)
        type_id = int(key)
        
        # Convert value to appropriate bytes based on type
        if isinstance(value, str):
            value_bytes = value.encode('utf-8')
        elif isinstance(value, int):
            # Convert integer to bytes using little endian
            value_bytes = value.to_bytes(2, "little")
        elif isinstance(value, bool):
            value_bytes = b'\x01' if value else b'\x00'
        else:
            raise ValueError(f"Unsupported type for value: {type(value)}")
        
        entries.append(tlv8.Entry(type_id, value_bytes))
    
    return entries

def get_certificate_paths(node_id: str, base_path: str) -> tuple:
    """Get certificate and key paths using cert_finder methods"""
    try:
        # Get certificate and key paths using cert_finder
        cert_path, key_path = get_cert_and_key_paths(base_path, node_id)
        
        # Get root certificate path
        config_dir = Path(base_path)
        root_ca_path = get_root_cert_path(config_dir)
        
        logger.info(f"Found certificates for node {node_id}:")
        logger.info(f"  Certificate: {cert_path}")
        logger.info(f"  Private Key: {key_path}")
        logger.info(f"  Root CA: {root_ca_path}")
        
        return cert_path, key_path, root_ca_path
        
    except FileNotFoundError as e:
        logger.error(f"Certificate files not found: {e}")
        return None, None, None
    except Exception as e:
        logger.error(f"Error finding certificates: {e}")
        return None, None, None

def publish_tlv8_payload(node_id: str, broker: str, cert_base_path: str, payload: dict):
    """Publish TLV8 payload to MQTT
    
    Args:
        node_id: Node ID to publish to
        broker: MQTT broker URL
        cert_base_path: Base path for certificate search
        payload: Dictionary containing the payload data to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Update topic with node_id
        topic = f"node/{node_id}/from-node"
        
        logger.info(f"Publishing to node: {node_id}")
        logger.info(f"Broker: {broker}")
        logger.info(f"Certificate base path: {cert_base_path}")
        logger.info(f"Payload: {payload}")
        
        # Convert to TLV8
        logger.info("Converting JSON to TLV8...")
        tlv8_entries = json_to_tlv8(payload)
        encoded_data = tlv8.encode(tlv8_entries)
        byte_array = bytearray(encoded_data)
        
        logger.info(f"TLV8 conversion successful. Length: {len(byte_array)}")
        logger.info(f"Hex: {' '.join(f'{byte:02x}' for byte in byte_array)}")
        
        # Get certificate paths using cert_finder
        cert_path, key_path, root_ca_path = get_certificate_paths(node_id, cert_base_path)
        
        if not cert_path or not key_path or not root_ca_path:
            logger.error("Failed to find certificate files")
            return False
        
        # Create MQTT operations instance
        mqtt_ops = MQTTOperations(
            broker=broker,
            node_id=node_id,
            cert_path=cert_path,
            key_path=key_path,
            root_path=root_ca_path
        )
        
        # Connect and publish
        logger.info(f"Connecting to {broker}...")
        mqtt_ops.connect()
        
        logger.info(f"Publishing to topic: {topic}")
        mqtt_ops.publish(topic, byte_array, 1)
        
        logger.info("Successfully published!")
        mqtt_ops.disconnect()
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False 