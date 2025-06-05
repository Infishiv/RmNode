# Project Structure

## Command Groups

The CLI tool is organized into the following command groups:

- `rm-node connection`: Connection management
- `rm-node device`: Device operations
- `rm-node node`: Node configuration
- `rm-node user`: User mapping
- `rm-node ota`: OTA updates
- `rm-node tsdata`: Time series data
- `rm-node config`: Configuration
- `rm-node messaging`: MQTT messaging

## Command Format

All commands follow this format:
```bash
rm-node [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

## Command Categories

```
rm-node
├── connection
│   ├── connect
│   ├── disconnect
│   ├── list
│   └── switch
│
├── device
│   └── send-command
│
├── node
│   ├── config
│   ├── params
│   ├── group-params
│   └── presence
│       ├── connected
│       └── disconnected
│
├── user
│   └── map
│
├── ota
│   ├── update
│   └── status
│
├── tsdata
│   ├── send
│   └── batch
│
├── config
│   ├── set-cert-path
│   ├── add-node
│   └── remove-node
│
└── messaging
    ├── publish
    ├── subscribe
    └── monitor
```

## Command Details

### 1. Connection Management
```
rm-node connection
├── connect [--node-id] [--broker] [--timeout]
├── disconnect [--node-id] [--all]
├── list [--all]
└── switch [--node-id]
```

### 2. Device Management
```
rm-node device
└── send-command [--node-id] [--request-id] [--role] [--command] [--command-data]
```

### 3. Node Management
```
rm-node node
├── config [--node-id] [--device-type] [--config-file] [--project-name]
├── params [--node-id] [--params-file] [--device-name] [--use-stored] [--remote]
├── group-params [--node-ids] [--params-file] [--use-stored]
└── presence
    ├── connected [--node-id] [--client-id] [--principal-id] [--session-id] [--ip-address] [--version]
    └── disconnected [--node-id] [--client-id] [--principal-id] [--session-id] [--disconnect-reason] [--version]
```

### 4. User Management
```
rm-node user
└── map [--node-id] [--user-id] [--secret-key] [--reset] [--timeout]
```

### 5. OTA Updates
```
rm-node ota
├── update [--node-id] [--firmware-file] [--version] [--force] [--timeout]
└── status [--node-id] [--wait]
```

### 6. Time Series Data
```
rm-node tsdata
├── send [--node-id] [--param-name] [--value] [--data-type] [--basic-ingest]
└── batch [--node-id] [--param-name] [--values] [--data-type] [--interval] [--basic-ingest]
```

### 7. Configuration Management
```
rm-node config
├── set-cert-path [--path] [--update/--no-update]
├── add-node [--node-id] [--cert-path] [--key-path]
└── remove-node [--node-id]
```

### 8. Messaging
```
rm-node messaging
├── publish [--topic] [--message] [--qos] [--retain]
├── subscribe [--topic] [--qos] [--timeout]
└── monitor [--topic] [--filter] [--format] [--timeout]
```

## Global Options

These options can be used with any command:

```
rm-node [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]

Global Options:
  --config-dir DIRECTORY  Configuration directory path
  --debug                Enable debug mode with detailed logging
  --broker TEXT          MQTT broker endpoint to use
  -h, --help            Show this help message
```

## Code Structure

The CLI is organized in the following directory structure:

```
rm-node_cli/
├── __init__.py
├── cli.py                 # Main CLI entry point
├── mqtt_operations.py     # Core MQTT operations
├── commands/             # Command implementations
│   ├── __init__.py
│   ├── connection.py
│   ├── device.py
│   ├── node_config.py
│   ├── user_mapping.py
│   ├── ota.py
│   ├── time_series.py
│   ├── config.py
│   └── messaging.py
└── utils/               # Utility functions
    ├── __init__.py
    ├── connection_manager.py
    ├── config_manager.py
    ├── cert_finder.py
    ├── validators.py
    ├── exceptions.py
    └── debug_logger.py
```

## Implementation Details

### Command Registration

Commands are registered in `cli.py` using Click's command groups:

```python
# cli.py
@click.group()
def cli():
    """MQTT CLI - A command-line interface for MQTT operations."""
    pass

# Register command groups
cli.add_command(connection)
cli.add_command(device)
cli.add_command(node)
cli.add_command(user)
cli.add_command(ota)
cli.add_command(tsdata)
cli.add_command(config)
cli.add_command(messaging)
```

### Command Implementation

Each command category is implemented in its own module under the `commands` directory:

```python
# commands/connection.py
@click.group()
def connection():
    """Connection management commands."""
    pass

@connection.command('connect')
@click.option('--node-id', required=True, help='Node ID to connect to')
def connect(node_id):
    """Connect to a node."""
    pass
```

### Utility Classes

Core functionality is provided by utility classes:

```python
# utils/connection_manager.py
class ConnectionManager:
    """Manages MQTT client connections and their persistence."""
    pass

# utils/config_manager.py
class ConfigManager:
    """Manages configuration and certificate files."""
    pass
``` 