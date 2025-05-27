"""
Configuration manager for MQTT CLI.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
import click

class ConfigManager:
    """Manages MQTT CLI configuration including broker and node details."""
    
    DEFAULT_BROKER = "a3q0b7ncspt14l-ats.iot.us-east-1.amazonaws.com"
    
    def __init__(self, config_dir: Path):
        """Initialize the configuration manager."""
        if not config_dir:
            raise ValueError("Configuration directory path cannot be empty")
            
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / 'config.json'
        self.config = {
            'broker': self.DEFAULT_BROKER,
            'nodes': {},  # node_id -> {'cert_path': str, 'key_path': str}
            'cert_cli_path': None
        }
        self._load()

    def _load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.loads(f.read())
                    # Validate and merge with defaults
                    self.config['broker'] = loaded_config.get('broker', self.DEFAULT_BROKER)
                    self.config['nodes'] = loaded_config.get('nodes', {})
                    # Handle legacy admin_cli_path
                    self.config['cert_cli_path'] = loaded_config.get('cert_cli_path') or loaded_config.get('admin_cli_path')
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid configuration file format: {e}")
            except Exception as e:
                raise IOError(f"Error reading configuration file: {e}")

    def _save(self):
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            raise IOError(f"Error saving configuration: {e}")

    def set_broker(self, broker: str):
        """Set the MQTT broker URL."""
        if not broker:
            raise ValueError("Broker URL cannot be empty")
        self.config['broker'] = broker
        self._save()

    def get_broker(self) -> str:
        """Get the current MQTT broker URL."""
        return self.config.get('broker', self.DEFAULT_BROKER)

    def set_cert_cli_path(self, path: str):
        """Set the Node's Certs path for certificate and key management."""
        if not path:
            raise ValueError("Certificate path cannot be empty")
            
        resolved_path = Path(path).resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Certificate path does not exist: {resolved_path}")
            
        if not resolved_path.is_dir():
            raise NotADirectoryError(f"Certificate path is not a directory: {resolved_path}")
            
        self.config['cert_cli_path'] = str(resolved_path)
        self._save()

    def get_cert_cli_path(self) -> Optional[str]:
        """Get the Node's Certs path used for certificate and key management."""
        path = self.config.get('cert_cli_path')
        if path and not Path(path).exists():
            click.echo(click.style(f"Warning: Configured certificate path no longer exists: {path}", fg='yellow'))
        return path

    def add_node(self, node_id: str, cert_path: str, key_path: str):
        """Add or update a node's certificate paths."""
        if not node_id:
            raise ValueError("Node ID cannot be empty")
            
        cert_path = Path(cert_path).resolve()
        key_path = Path(key_path).resolve()
        
        if not cert_path.exists():
            raise FileNotFoundError(f"Certificate file not found: {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"Key file not found: {key_path}")
            
        self.config['nodes'][node_id] = {
            'cert_path': str(cert_path),
            'key_path': str(key_path)
        }
        self._save()

    def get_node_paths(self, node_id: str) -> Optional[Tuple[str, str]]:
        """Get certificate paths for a node."""
        if not node_id:
            raise ValueError("Node ID cannot be empty")
            
        node_info = self.config['nodes'].get(node_id)
        if node_info:
            cert_path = Path(node_info['cert_path'])
            key_path = Path(node_info['key_path'])
            
            # Check if files still exist
            if not cert_path.exists() or not key_path.exists():
                click.echo(click.style(
                    f"Warning: Certificate files for node {node_id} no longer exist at configured location",
                    fg='yellow'
                ))
                return None
                
            return str(cert_path), str(key_path)
        return None

    def list_nodes(self) -> Dict[str, dict]:
        """Get all configured nodes."""
        # Filter out nodes with missing certificate files
        valid_nodes = {}
        for node_id, info in self.config['nodes'].items():
            cert_path = Path(info['cert_path'])
            key_path = Path(info['key_path'])
            if cert_path.exists() and key_path.exists():
                valid_nodes[node_id] = info
            else:
                click.echo(click.style(
                    f"Warning: Skipping node {node_id} - certificate files no longer exist",
                    fg='yellow'
                ))
        return valid_nodes

    def remove_node(self, node_id: str) -> bool:
        """Remove a node's configuration."""
        if not node_id:
            raise ValueError("Node ID cannot be empty")
            
        if node_id in self.config['nodes']:
            del self.config['nodes'][node_id]
            self._save()
            return True
        return False

    def reset(self):
        """Reset configuration to defaults."""
        self.config = {
            'broker': self.DEFAULT_BROKER,
            'nodes': {},
            'cert_cli_path': None
        }
        self._save() 