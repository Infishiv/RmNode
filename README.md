# MQTT CLI Tool

A command-line interface tool for managing ESP RainMaker MQTT operations.

## Table of Contents
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Command Reference](#command-reference)
  - [OTA Commands](#1-ota-over-the-air-commands)
  - [User Commands](#2-user-commands)
  - [Device Commands](#3-device-commands)
  - [Node Config Commands](#4-node-configuration-commands)
  - [Time Series Commands](#5-time-series-commands)
  - [Connection Commands](#6-connection-commands)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Mqtt_cli_v01-1
```

2. Create and activate a virtual environment:
```bash
# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
.\venv\Scripts\activate
```

3. Install the package:
```bash
pip install -r requirements.txt
pip install -e .
```

## Project Structure
```
mqtt_cli/
├── commands/           # Command implementations
│   ├── connection.py   # Connection management
│   ├── messaging.py    # MQTT messaging
│   ├── device.py      # Device management
│   ├── ota.py         # OTA update handling
│   ├── user_mapping.py # User mapping operations
│   └── config.py      # Configuration management
├── utils/             # Utility functions
└── cli.py            # Main CLI entry point
```

## Command Reference

### 1. OTA (Over-The-Air) Commands
Commands for managing firmware updates.

#### ota fetch
```bash
mqtt-cli ota fetch [OPTIONS]

Required:
  --node-id TEXT      Node ID to fetch OTA update for
  --fw-version TEXT   Current firmware version

Optional:
  --network-id TEXT   Network ID for Thread-based OTA
  --help             Show this message and exit
```

#### ota status
```bash
mqtt-cli ota status [OPTIONS]

Required:
  --node-id TEXT     Node ID(s) to update status for
  --status TEXT      Status [in-progress|success|rejected|failed|delayed]
  --job-id TEXT      OTA job ID

Optional:
  --network-id TEXT  Network ID
  --info TEXT        Additional status information
```

#### ota request
```bash
mqtt-cli ota request [OPTIONS]

Required:
  --node-id TEXT    Node ID(s) to request OTA update for

Optional:
  --timeout INTEGER Timeout in seconds (default: 60)
```

### 2. User Commands
Commands for managing user-node mappings and alerts.

#### user map
```bash
mqtt-cli user map [OPTIONS]

Required:
  --node-id TEXT     Node ID to map the user to
  --user-id TEXT     User ID to map to the node
  --secret-key TEXT  Secret key for authentication

Optional:
  --reset           Reset the existing mapping
  --timeout INTEGER Timeout in seconds (default: 300)
```

#### user alert
```bash
mqtt-cli user alert [OPTIONS]

Required:
  --node-id TEXT  Node ID to send the alert to
  --message TEXT  Alert message to send
```

### 3. Device Commands
Commands for managing device operations.

#### device params
```bash
mqtt-cli device params [OPTIONS]

Required:
  --node-id TEXT  Node ID to get/set parameters for

Optional:
  --get TEXT      Parameter name to get
  --set TEXT      Parameter name to set
  --value TEXT    Value for the parameter being set
```

### 4. Node Configuration Commands
Commands for managing node configurations.

#### node-config get
```bash
mqtt-cli node-config get [OPTIONS]

Required:
  --node-id TEXT  Node ID to get config for
```

#### node-config set
```bash
mqtt-cli node-config set [OPTIONS]

Required:
  --node-id TEXT     Node ID to set config for
  --config-file TEXT Path to JSON config file
```

### 5. Time Series Commands
Commands for managing time series data.

#### time-series get
```bash
mqtt-cli time-series get [OPTIONS]

Required:
  --node-id TEXT    Node ID to get data for
  --start-time TEXT Start time (ISO format)
  --end-time TEXT   End time (ISO format)

Optional:
  --interval TEXT   Time interval (e.g., 1h, 1d)
```

### 6. Connection Commands
Commands for managing MQTT connections.

#### connection test
```bash
mqtt-cli connection test [OPTIONS]

Required:
  --node-id TEXT  Node ID to test connection for
```

## Usage Examples

### OTA Update Workflow
```bash
# 1. Request OTA update
mqtt-cli ota request --node-id node123 --timeout 120

# 2. Monitor and update status
mqtt-cli ota status --node-id node123 --status in-progress --job-id job123
mqtt-cli ota status --node-id node123 --status success --job-id job123
```

### User Management Workflow
```bash
# 1. Map user to node
mqtt-cli user map --node-id node123 --user-id user456 --secret-key abc123

# 2. Send alert to node
mqtt-cli user alert --node-id node123 --message "Update required"
```

### Device Management Workflow
```bash
# 1. Get device parameter
mqtt-cli device params --node-id node123 --get temperature

# 2. Set device parameter
mqtt-cli device params --node-id node123 --set temperature --value 25
```

## Common Options
Available for all commands:
- `--help`: Show command help
- `--debug`: Enable debug output
- `--config-dir`: Specify config directory

## Troubleshooting

### Common Issues
1. **Connection Errors**
   - Verify node ID is correct
   - Check certificate paths
   - Ensure network connectivity

2. **Command Failures**
   - Verify all required options are provided
   - Check option values are in correct format
   - Ensure proper permissions for config files

3. **OTA Update Issues**
   - Verify firmware version format
   - Check device storage space
   - Ensure stable network connection

### Debug Mode
For detailed logging:
```bash
mqtt-cli --debug [command]
```

## Support
For additional help or to report issues, please contact the support team or create an issue in the repository. 