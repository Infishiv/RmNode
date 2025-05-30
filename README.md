# MQTT CLI Tool

A command-line interface for MQTT operations with AWS IoT Core integration, featuring enhanced command-line parsing and multi-node operations.

## Recent Updates and Improvements

### Architecture Changes
- **Enhanced CLI Interface**: Migrated from positional arguments to explicit option flags for better usability and clarity
- **Multi-Node Support**: Added support for parallel operations on multiple nodes using comma-separated node IDs
- **Improved Error Handling**: Better error messages and validation for all commands
- **Standardized Command Structure**: Consistent command patterns across all operations
- **Dynamic Configuration**: Added support for dynamic node configuration and parameter management
- **Group Operations**: Support for group parameter updates across multiple nodes

### Key Features
- Support for both single and multiple node operations
- Enhanced OTA update management
- Improved connection handling with explicit parameter validation
- Better time series data management with Swagger compatibility
- Standardized command-line interface across all operations
- Dynamic node configuration with templates
- Group parameter management support

## Project Structure
```
mqtt_cli/
├── commands/                # Command implementations
│   ├── connection.py       # Connection management
│   ├── messaging.py        # MQTT messaging
│   ├── device.py          # Device management
│   ├── ota.py             # OTA update handling
│   ├── node_config.py     # Node configuration
│   ├── time_series.py     # Time series data
│   ├── user_mapping.py    # User mapping operations
│   └── node_configs/      # Configuration templates
│       ├── default_config.json
│       └── default_params.json
├── core/                   # Core functionality
│   ├── mqtt_client.py     # MQTT client implementation
│   └── utils.py           # Utility functions
├── models/                 # Data models
└── cli.py                 # Main CLI entry point
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Infishiv/RmNode.git
cd Rmnode
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

## Configuration

The CLI tool uses a configuration directory (default: `.mqtt-cli/`) to store settings and certificates.

### Basic Configuration Commands

```bash
# Set configuration directory (optional)
mqtt-cli --config-dir /path/to/config

# Get admin CLI path
mqtt-cli config get-admin-cli

# Set admin CLI path
mqtt-cli config set-admin-cli /path/to/admin/cli
```

## Connection Management

### Setting Up Connections

```bash
# Add a new connection with certificates
mqtt-cli connection add --name "my-device" --cert "path/to/cert.pem" --key "path/to/key.pem"

# List all configured connections
mqtt-cli connection list

# Show connection details
mqtt-cli connection show --name "my-device"

# Test connection
mqtt-cli connection test --name "my-device"

# Set active connection
mqtt-cli connection set-active --name "my-device"

# Remove connection
mqtt-cli connection remove --name "my-device"

# Update connection details
mqtt-cli connection update --name "my-device" --cert "new/cert.pem" --key "new/key.pem"

# Connect to a node with specific certificates
mqtt-cli connection connect --node-id "node123" --cert "path/to/cert.pem" --key "path/to/key.pem"

# Disconnect active connection
mqtt-cli connection disconnect

# Show connection status
mqtt-cli connection status
```

## Basic MQTT Messaging

```bash
# Subscribe to a topic
mqtt-cli messaging subscribe --topic "my/topic/#"

# Publish to a topic
mqtt-cli messaging publish --topic "my/topic" --message "Hello, MQTT!"

# Monitor messages on a topic
mqtt-cli messaging monitor --topic "my/topic/#"
```

## Device Management

```bash
# List connected devices
mqtt-cli device list

# Get device status
mqtt-cli device status --device-id "device123"

# Send command to device
mqtt-cli device command --device-id "device123" --command "restart"
```

## OTA (Over-The-Air) Updates

```bash
# Start OTA monitor (in a separate terminal)
mqtt-cli ota monitor --node-id "node123"

# Request OTA update check with specific version
mqtt-cli ota request --node-id "node123" --fw-version "1.0.0" --timeout 60

# Fetch OTA update
mqtt-cli ota fetch --node-id "node123" --fw-version "1.0.0" --network-id "network123"

# Update OTA status
mqtt-cli ota status --node-id "node123" --status "in-progress" --job-id "job123" --info "25% complete"

# Common status values:
# - in-progress: Update is being applied
# - success: Update completed successfully
# - rejected: Update was rejected by device
# - failed: Update failed to apply
# - delayed: Update postponed

# Monitor OTA updates with automatic status updates
mqtt-cli ota monitor --node-id "node123" --auto-status
```

## Node Configuration and Parameters

```bash
# Set node configuration using stored template
mqtt-cli node config --node-id "node123" --use-stored

# Set node configuration with custom name
mqtt-cli node config --node-id "node123" --use-stored --name "Living Room Node"

# Set node configuration from file
mqtt-cli node config --node-id "node123" --config-file "custom_config.json"

# Initialize node parameters
mqtt-cli node init-params --node-id "node123" --use-stored
mqtt-cli node init-params --node-id "node123" --params-file "init_params.json"

# Update parameters for a group of nodes
mqtt-cli node group-params --node-ids "node1,node2,node3" --params-file "group_params.json"
mqtt-cli node group-params --node-ids "node1,node2" --use-stored

# Set parameters for a specific device
mqtt-cli node params --node-id "node123" --device-name "Light" --param "power" --value "on"
```

## Device Commands and Alerts

```bash
# Send TLV-formatted command to node
mqtt-cli device send-command --node-id "node123" --role 1 --command 0
mqtt-cli device send-command --node-id "node123" --role 2 --command 1 --command-data '{"param": "value"}'

# Send alert from node
mqtt-cli device send-alert --node-id "node123" --message "Temperature high!"
mqtt-cli device send-alert --node-id "node123" --message "Alert!" --basic-ingest
```

## Time Series Data Management

```bash
# Send single time series data point
mqtt-cli tsdata send "node123" "temperature" "25.5" --data-type float
mqtt-cli tsdata send "node123" "power" "true" --data-type bool --simple

# Send batch time series data
mqtt-cli tsdata batch "node123" "temperature" "25.5" "26.0" "26.5" --interval 30
mqtt-cli tsdata batch "node123" "humidity" "45" "48" "50" --data-type int --basic-ingest
```

## User-Node Mapping

```bash
# Map user to node with authentication
mqtt-cli user map --node-id "node123" --user-id "user456" --secret-key "abc123"

# Map user with timeout and reset
mqtt-cli user map --node-id "node123" --user-id "user456" --secret-key "abc123" --timeout 600 --reset

# Send user alert
mqtt-cli user alert --node-id "node123" --message "System update required"
```

## Node Configuration

```bash
# Get node configuration
mqtt-cli node get-config --node-id "node123"

# Set node configuration
mqtt-cli node set-config --node-id "node123" --config-file "config.json"

# Reset node
mqtt-cli node reset --node-id "node123"
```

## User Mapping

```bash
# Map user to node
mqtt-cli user map --user-id "user123" --node-id "node123"

# List user mappings
mqtt-cli user list-mappings

# Remove user mapping
mqtt-cli user unmap --user-id "user123" --node-id "node123"
```

## Time Series Data

```bash
# Get time series data
mqtt-cli tsdata get --node-id "node123" --start-time "2024-01-01" --end-time "2024-01-02"

# Export time series data
mqtt-cli tsdata export --node-id "node123" --format csv --output "data.csv"
```

## Rainmaker Integration

```bash
# Initialize Rainmaker
mqtt-cli rainmaker init

# Get node certificates
mqtt-cli rainmaker get-certs --node-id "node123"

# Provision node
mqtt-cli rainmaker provision --node-id "node123"
```

## Node Management

### Listing and Configuring Nodes

```bash
# List all configured nodes (shows nodes in config.json)
mqtt-cli config list-nodes

# List active connections and their status
mqtt-cli connection list --all

# Show specific node details
mqtt-cli node show --node-id "node123"

# Connect to a node with specific certificates
mqtt-cli connection connect --node-id "node123" --cert "path/to/cert.pem" --key "path/to/key.pem"

# Import nodes from a directory (supports both standard and Rainmaker formats)
mqtt-cli config import-nodes --base-path "/path/to/nodes" --is-rainmaker
```

### Node Configuration and Setup

```bash
# Set admin CLI path and auto-discover nodes
mqtt-cli config set-admin-cli "/path/to/admin-cli" --update

# Connect to a specific node
mqtt-cli connection connect "node123"

# Connect to multiple nodes
mqtt-cli connection connect "node123" "node456" "node789"

# Switch active connection to another node
mqtt-cli connection switch "node456"

# Set node configuration
mqtt-cli node set-config --node-id "node123" \
    --name "My ESP Device" \
    --model "esp32_device" \
    --type "Generic Device" \
    --fw-version "1.0.0"

# Set node parameters
mqtt-cli node set-local-params "node123" "light" "power" "on"
```

### Node Status and Presence

```bash
# Check node connection status
mqtt-cli node status --node-id "node123"

# Send node connected event
mqtt-cli node connected --node-id "node123" --ip-address "192.168.1.100"

# Monitor node presence
mqtt-cli node monitor-presence --node-id "node123"
```

### Node Groups and Parameters

```bash
# Set parameters for a node group
mqtt-cli node set-local-params "node123" "light" "power" "on" --group-id "group1"

# Get node parameters
mqtt-cli node get-params --node-id "node123"

# Monitor node parameters
mqtt-cli node monitor-params --node-id "node123"
```

### Common Node Operations

```bash
# Reset node configuration
mqtt-cli node reset --node-id "node123"

# Backup node configuration
mqtt-cli node backup-config --node-id "node123" --output "backup.json"

# Restore node configuration
mqtt-cli node restore-config --node-id "node123" --input "backup.json"

# Remove node from configuration
mqtt-cli config remove-node --node-id "node123"
```

### Node Certificate Management

```bash
# Show node certificates
mqtt-cli node show-certs --node-id "node123"

# Update node certificates
mqtt-cli node update-certs --node-id "node123" --cert "new.crt" --key "new.key"

# Verify node certificates
mqtt-cli node verify-certs --node-id "node123"
```

### Troubleshooting Node Connections

```bash
# Test node connection
mqtt-cli connection test --node-id "node123"

# Show node connection logs
mqtt-cli node logs --node-id "node123"

# Diagnose node connection issues
mqtt-cli node diagnose --node-id "node123"
```

## Common Options

Most commands support the following common options:

- `--help`: Show help message
- `--config-dir`: Specify configuration directory
- `--verbose`: Enable verbose output

## Environment Setup

The CLI tool expects the following environment structure:

```
.mqtt-cli/
├── certs/           # Certificate storage
├── configs/         # Configuration files
└── connections.json # Connection information
```

## Error Handling

The CLI provides detailed error messages and exit codes:

- Exit code 0: Success
- Exit code 1: General error
- Exit code 2: Configuration error
- Exit code 3: Connection error

## Platform Support

This CLI tool is compatible with:
- macOS
- Linux
- Windows

The commands work the same way across all platforms, with the only difference being the command prompt syntax and path separators.

## Best Practices

1. Always use the virtual environment
2. Keep certificates in a secure location
3. Use descriptive names for connections and nodes
4. Monitor OTA updates in a separate terminal
5. Backup configuration files regularly

## Troubleshooting

Common issues and solutions:

1. Certificate errors:
   - Verify certificate paths
   - Check certificate permissions
   - Ensure certificates are in PEM format

2. Connection issues:
   - Check network connectivity
   - Verify broker address
   - Confirm active connection settings

3. Command failures:
   - Check configuration directory permissions
   - Verify active connection
   - Ensure required parameters are provided

## Support

For issues and feature requests, please create an issue in the repository.

## Command Examples with New Syntax

### Connection Management
```bash
# Connect to single node
mqtt-cli connection connect --node-id "node123"

# Connect to multiple nodes
mqtt-cli connection connect --node-id "node123,node456,node789"

# Test connection with specific certificates
mqtt-cli connection test --name "my-device" --cert "/path/to/cert.pem" --key "/path/to/key.pem"
```

### OTA Updates
```bash
# Request OTA update for single node
mqtt-cli ota request --node-id "node123" --fw-version "1.0.0"

# Request OTA update for multiple nodes
mqtt-cli ota request --node-id "node123,node456" --fw-version "1.0.0"

# Monitor OTA status for multiple nodes
mqtt-cli ota monitor --node-id "node123,node456"
```

## Development Guidelines

### Adding New Commands
1. Create a new command file in the `commands/` directory
2. Use the `click` library for command-line parsing
3. Follow the established pattern of using explicit option flags
4. Include comprehensive help text and error messages
5. Support both single and multi-node operations where applicable

### Code Style
- Use explicit option flags instead of positional arguments
- Include descriptive help text for all commands and options
- Implement proper error handling and validation
- Follow PEP 8 style guidelines
- Add type hints for better code clarity

### Testing
1. Write unit tests for new commands
2. Test both single and multi-node scenarios
3. Verify error handling and edge cases
4. Test connection handling and timeout scenarios

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes following the development guidelines
4. Submit a pull request with a clear description of changes

## Troubleshooting

### Common Issues
1. **Connection Failures**
   - Verify certificate paths
   - Check node ID format
   - Ensure proper network connectivity

2. **OTA Update Issues**
   - Confirm firmware version format
   - Check node connectivity
   - Verify sufficient storage on target device

3. **Command Parsing Errors**
   - Use proper option flags (e.g., --node-id instead of positional arguments)
   - Check for proper quoting of values
   - Verify correct command syntax

### Debug Mode
Enable debug logging for more detailed output:
```bash
mqtt-cli --debug [command]
```

## License
[Insert License Information]

## Contact
[Insert Contact Information] 