"""
Connection manager for MQTT CLI.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from ..mqtt_operations import MQTTOperations

class ConnectionManager:
    """Manages MQTT client connections and their persistence."""
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.connections: Dict[str, MQTTOperations] = {}
        self.connection_info: Dict[str, dict] = {}
        self.active_node = None
        self.state_file = config_dir / 'connection.json'
        self.logger = logging.getLogger(__name__)
        self._load()

    def _load(self):
        """Load connection info from state file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.connection_info = data.get('connections', {})
                    self.active_node = data.get('active_node')
        except Exception as e:
            self.logger.warning(f"Failed to load connection state: {str(e)}")
            self.connection_info = {}
            self.active_node = None

    def _save(self):
        """Save connection info to state file."""
        try:
            data = {
                'connections': self.connection_info,
                'active_node': self.active_node
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.logger.warning(f"Failed to save connection state: {str(e)}")

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
            'cert_path': str(cert_path),
            'key_path': str(key_path)
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

    def get_connection(self, node_id: str) -> Optional[MQTTOperations]:
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

    def get_active_node(self) -> Optional[str]:
        """Get the currently active node ID."""
        return self.active_node

    def get_active_connection(self) -> Optional[MQTTOperations]:
        """Get the currently active connection."""
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

    def update_connection_broker(self, node_id: str, broker: str):
        """Update broker URL for a connection."""
        if node_id in self.connection_info:
            self.connection_info[node_id]['broker'] = broker
            self._save()
            # Force reconnect with new broker
            if node_id in self.connections:
                try:
                    self.connections[node_id].disconnect()
                except:
                    pass
                del self.connections[node_id] 