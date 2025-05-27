"""
Connection manager for MQTT CLI.
"""
import json
import logging
import os
from pathlib import Path
from ..mqtt_operations import MQTTOperations

class ConnectionManager:
    """Manages MQTT client connections and their persistence."""
    
    def __init__(self, config_dir):
        """Initialize the connection manager."""
        config_dir = Path(config_dir)
        config_dir.mkdir(exist_ok=True)  # Ensure directory exists
        self.storage_file = config_dir / 'connection.json'
        self.connections = {}  # node_id: MQTTOperations
        self.connection_info = {}  # node_id: connection_info
        self.active_node = None
        self.logger = logging.getLogger("mqtt_cli")
        self._load()

    def _load(self):
        """Load saved connection information from storage file."""
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text())
                self.active_node = data.get('active_node')
                self.connection_info = data.get('connections', {})
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to load connections: {str(e)}")

    def _save(self):
        """Save current connection information to storage file."""
        save_data = {
            'active_node': self.active_node,
            'connections': self.connection_info
        }
        self.storage_file.write_text(json.dumps(save_data, indent=2))

    def add_connection(self, node_id: str, broker: str, cert_path: str, key_path: str, client: MQTTOperations):
        """
        Add a new connection.
        
        Args:
            node_id: The node ID
            broker: The broker URL
            cert_path: Path to the node certificate
            key_path: Path to the node key
            client: The connected MQTT client
        """
        self.connections[node_id] = client
        self.connection_info[node_id] = {
            'broker': broker,
            'cert_path': cert_path,
            'key_path': key_path
        }
        self.active_node = node_id
        self._save()

    def remove_connection(self, node_id: str) -> bool:
        """Remove a connection."""
        if node_id in self.connections:
            client = self.connections[node_id]
            try:
                client.disconnect()
            except:
                pass
            del self.connections[node_id]
            del self.connection_info[node_id]
            
            if self.active_node == node_id:
                self.active_node = None
            
            self._save()
            return True
        return False

    def get_connection(self, node_id: str) -> MQTTOperations:
        """Get a connection by node ID. Creates new connection if needed."""
        # Return existing active connection if it exists
        if node_id in self.connections and self.connections[node_id].is_connected():
            return self.connections[node_id]
            
        # If we have connection info, create a new connection
        if node_id in self.connection_info:
            info = self.connection_info[node_id]
            try:
                client = MQTTOperations(
                    broker=info['broker'],
                    node_id=node_id,
                    cert_path=info['cert_path'],
                    key_path=info['key_path']
                )
                if client.connect():
                    self.connections[node_id] = client
                    return client
            except Exception as e:
                self.logger.warning(f"Failed to connect to {node_id}: {str(e)}")
                
        return None

    def get_active_connection(self) -> MQTTOperations:
        """Get the currently active connection."""
        if self.active_node:
            return self.get_connection(self.active_node)
        return None

    def get_active_client(self) -> MQTTOperations:
        """Get the currently active client."""
        if self.active_node:
            return self.get_connection(self.active_node)
        return None

    def disconnect_all(self) -> dict:
        """Disconnect all connections."""
        results = {}
        for node_id in list(self.connections.keys()):
            results[node_id] = self.remove_connection(node_id)
        return results

    def list_connections(self) -> list:
        """List all stored connection information."""
        return list(self.connection_info.keys()) 