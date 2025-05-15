import json
from pathlib import Path
from typing import Dict, Any, Tuple

class ConfigManager:
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.state_file = self.config_dir / "current_state.json"
        self.current_device = None
        self.current_config = None
        self.current_params = None
        self._load_state()

    def _load_state(self):
        """Load persisted state if exists"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.current_device = state.get('current_device')
                    self.current_config = state.get('current_config')
                    self.current_params = state.get('current_params')
            except Exception:
                pass  # If state file is corrupted, we'll just start fresh

    def _save_state(self):
        """Save current state to file"""
        state = {
            'current_device': self.current_device,
            'current_config': self.current_config,
            'current_params': self.current_params
        }
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save state: {str(e)}")

    def get_device_config(self, device_type: str) -> Dict[str, Any]:
        """Get config for device type"""
        filepath = self.config_dir / f"{device_type.lower()}_config.json"
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load config: {str(e)}")

    def get_device_params(self, device_type: str) -> Dict[str, Any]:
        """Get params for device type"""
        filepath = self.config_dir / f"{device_type.lower()}_params.json"
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load params: {str(e)}")

    def make_device(self, device_type: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Get both config and params for specified device"""
        try:
            config = self.get_device_config(device_type)
            params = self.get_device_params(device_type)
            self.current_device = device_type
            self.current_config = config
            self.current_params = params
            self._save_state()
            return config, params
        except Exception as e:
            raise Exception(f"Failed to make device: {str(e)}")

    def get_current_device(self) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Get current device state"""
        if not self.current_device:
            raise Exception("No device type configured. Use 'make' command first")
        return self.current_device, self.current_config, self.current_params

    def update_device_config(self, device_type: str, config: Dict[str, Any]):
        """Update config for device type and maintain power state consistency"""
        filepath = self.config_dir / f"{device_type.lower()}_config.json"
        try:
            # Ensure power state is consistent between current and new config
            if self.current_config and 'Power' in self.current_config:
                config['Power'] = self.current_config['Power']
            elif self.current_config and 'power' in self.current_config:
                config['power'] = self.current_config['power']

            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to update config: {str(e)}")
