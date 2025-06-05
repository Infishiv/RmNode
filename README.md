# MQTT CLI Tool

A command-line interface for MQTT operations, designed for easy device management and messaging.

## Features

- Connect to MQTT brokers with certificate-based authentication
- Subscribe to topics and monitor messages
- Publish messages to topics
- Manage device configurations
- Handle OTA updates
- Monitor time series data
- User-node mapping functionality

## Installation

```bash
pip install rm-node
```

## Basic Usage

1. Connect to a node:
```bash
rm-node connection connect --node-id your-node-id
```

2. Send a device command:
```bash
rm-node device send-command --node-id your-node-id --role 1 --command 0
```

3. Monitor messages on a topic:
```bash
rm-node messaging monitor --topic "your/topic/#"
```

## Configuration

The CLI tool uses a configuration directory (default: `.rm-node/`) to store settings and certificates.

You can specify a custom config directory:

```bash
rm-node --config-dir /path/to/config
```

### Admin CLI Configuration

Get current admin CLI path:
```bash
rm-node config get-admin-cli
```

Set admin CLI path:
```bash
rm-node config set-admin-cli /path/to/admin/cli
```

## Connection Management

### Device Management

Add a new device connection:
```bash
rm-node connection add --name "my-device" --cert "path/to/cert.pem" --key "path/to/key.pem"
```

List connections:
```bash
rm-node connection list
```

Show connection details:
```bash
rm-node connection show --name "my-device"
```

Test connection:
```bash
rm-node connection test --name "my-device"
```

Set active connection:
```bash
rm-node connection set-active --name "my-device"
```

Remove connection:
```bash
rm-node connection remove --name "my-device"
```

Update connection:
```bash
rm-node connection update --name "my-device" --cert "new/cert.pem" --key "new/key.pem"
```

Direct connection:
```bash
rm-node connection connect --node-id "node123" --cert "path/to/cert.pem" --key "path/to/key.pem"
```

Disconnect:
```bash
rm-node connection disconnect
```

Check status:
```bash
rm-node connection status
```

## Messaging

### Subscribe to Topics

```bash
rm-node messaging subscribe --topic "my/topic/#"
```

### Publish Messages

```bash
rm-node messaging publish --topic "my/topic" --message "Hello, MQTT!"
```

### Monitor Topics

```bash
rm-node messaging monitor --topic "my/topic/#"
```

## Device Management

### List Devices

```bash
rm-node device list
```

### Check Device Status

```bash
rm-node device status --device-id "device123"
```

### Send Device Commands

```bash
rm-node device command --device-id "device123" --command "restart"
```

## OTA Updates

### Monitor OTA Status

```bash
rm-node ota monitor --node-id "node123"
```

### Request OTA Update

```bash
rm-node ota request --node-id "node123" --fw-version "1.0.0" --timeout 60
```

### Fetch OTA Update

```bash
rm-node ota fetch --node-id "node123" --fw-version "1.0.0" --network-id "network123"
```

### Update OTA Status

```bash
rm-node ota status --node-id "node123" --status "in-progress" --job-id "job123" --info "25% complete"
```

### Auto Status Updates

Monitor OTA progress with automatic status updates:

```bash
rm-node ota monitor --node-id "node123" --auto-status
```

## Node Configuration

### Configure Node

Using stored configuration:
```bash
rm-node node config --node-id "node123" --use-stored
```

With custom name:
```bash
rm-node node config --node-id "node123" --use-stored --name "Living Room Node"
```

Using custom config file:
```bash
rm-node node config --node-id "node123" --config-file "custom_config.json"
```

### Initialize Parameters

Using stored parameters:
```bash
rm-node node init-params --node-id "node123" --use-stored
rm-node node init-params --node-id "node123" --params-file "init_params.json"
```

### Group Parameters

Configure multiple nodes:
```bash
rm-node node group-params --node-ids "node1,node2,node3" --params-file "group_params.json"
rm-node node group-params --node-ids "node1,node2" --use-stored
```

### Set Parameters

```bash
rm-node node params --node-id "node123" --device-name "Light" --param "power" --value "on"
```

## Device Commands

### Send Commands

Basic command:
```bash
rm-node device send-command --node-id "node123" --role 1 --command 0
rm-node device send-command --node-id "node123" --role 2 --command 1 --command-data '{"param": "value"}'
```

Send alerts:
```bash
rm-node device send-alert --node-id "node123" --message "Temperature high!"
rm-node device send-alert --node-id "node123" --message "Alert!" --basic-ingest
```

## Time Series Data

### Send Data

Single value:
```bash
rm-node tsdata send "node123" "temperature" "25.5" --data-type float
rm-node tsdata send "node123" "power" "true" --data-type bool --simple
```

Batch data:
```bash
rm-node tsdata batch "node123" "temperature" "25.5" "26.0" "26.5" --interval 30
rm-node tsdata batch "node123" "humidity" "45" "48" "50" --data-type int --basic-ingest
```

## User Management

### Map Users to Nodes

Basic mapping:
```bash
rm-node user map --node-id "node123" --user-id "user456" --secret-key "abc123"
```

Advanced mapping:
```bash
rm-node user map --node-id "node123" --user-id "user456" --secret-key "abc123" --timeout 600 --reset
```

Send user alerts:
```bash
rm-node user alert --node-id "node123" --message "System update required"
```

## Node Management

### Get Node Configuration

```bash
rm-node node get-config --node-id "node123"
```

### Set Node Configuration

```bash
rm-node node set-config --node-id "node123" --config-file "config.json"
```

### Reset Node

```bash
rm-node node reset --node-id "node123"
```

## User Mapping

### Map User to Node

```bash
rm-node user map --user-id "user123" --node-id "node123"
```

### List Mappings

```bash
rm-node user list-mappings
```

### Unmap User from Node

```bash
rm-node user unmap --user-id "user123" --node-id "node123"
```

## Time Series Data

### Get Data

```bash
rm-node tsdata get --node-id "node123" --start-time "2024-01-01" --end-time "2024-01-02"
```

### Export Data

```bash
rm-node tsdata export --node-id "node123" --format csv --output "data.csv"
```

## Rainmaker Integration

### Initialize

```bash
rm-node rainmaker init
```

### Get Certificates

```bash
rm-node rainmaker get-certs --node-id "node123"
```

### Provision Node

```bash
rm-node rainmaker provision --node-id "node123"
```

## Additional Features

### List Configured Nodes

```bash
rm-node config list-nodes
```

### List All Connections

```bash
rm-node connection list --all
```

### Show Node Details

```bash
rm-node node show --node-id "node123"
```

### Connect with Certificates

```bash
rm-node connection connect --node-id "node123" --cert "path/to/cert.pem" --key "path/to/key.pem"
```

### Import Node Configuration

```bash
rm-node config import-nodes --base-path "/path/to/nodes" --is-rainmaker
```

## Configuration Directory

The tool uses `.rm-node/` as the default configuration directory. This can be overridden using the `--config-dir` option.

## Advanced Usage

### Update Admin CLI

```bash
rm-node config set-admin-cli "/path/to/admin-cli" --update
```

### Connect Multiple Nodes

Single node:
```bash
rm-node connection connect "node123"
```

Multiple nodes:
```bash
rm-node connection connect "node123" "node456" "node789"
```

Switch active node:
```bash
rm-node connection switch "node456"
```

### Node Configuration

Set configuration:
```bash
rm-node node set-config --node-id "node123" \
    --name "Living Room" \
    --type "light" \
    --version "1.0.0"
```

Set local parameters:
```bash
rm-node node set-local-params "node123" "light" "power" "on"
```

## Node Status

### Check Status

```bash
rm-node node status --node-id "node123"
```

### Update Connection Status

```bash
rm-node node connected --node-id "node123" --ip-address "192.168.1.100"
```

### Monitor Node Presence

```bash
rm-node node monitor-presence --node-id "node123"
```

## Group Operations

### Set Group Parameters

```bash
rm-node node set-local-params "node123" "light" "power" "on" --group-id "group1"
```

### Get Parameters

```bash
rm-node node get-params --node-id "node123"
```

### Monitor Parameters

```bash
rm-node node monitor-params --node-id "node123"
```

## Node Reset and Backup

### Reset Node

```bash
rm-node node reset --node-id "node123"
```

### Backup Configuration

```bash
rm-node node backup-config --node-id "node123" --output "backup.json"
```

### Restore Configuration

```bash
rm-node node restore-config --node-id "node123" --input "backup.json"
```

### Remove Node

```bash
rm-node config remove-node --node-id "node123"
```

## Certificate Management

### Show Certificates

```bash
rm-node node show-certs --node-id "node123"
```

### Update Certificates

```bash
rm-node node update-certs --node-id "node123" --cert "new.crt" --key "new.key"
```

### Verify Certificates

```bash
rm-node node verify-certs --node-id "node123"
```

## Testing and Diagnostics

### Test Connection

```bash
rm-node connection test --node-id "node123"
```

### View Logs

```bash
rm-node node logs --node-id "node123"
```

### Diagnose Issues

```bash
rm-node node diagnose --node-id "node123"
```

## Examples

### Connection Examples

Basic connection:
```bash
rm-node connection connect --node-id "node123"
```

Multiple nodes:
```bash
rm-node connection connect --node-id "node123,node456,node789"
```

Test connection with certificates:
```bash
rm-node connection test --name "my-device" --cert "/path/to/cert.pem" --key "/path/to/key.pem"
```

### OTA Examples

Request update:
```bash
rm-node ota request --node-id "node123" --fw-version "1.0.0"
```

Multiple nodes:
```bash
rm-node ota request --node-id "node123,node456" --fw-version "1.0.0"
```

Monitor multiple nodes:
```bash
rm-node ota monitor --node-id "node123,node456"
```

## Debug Mode

Enable debug logging:
```bash
rm-node --debug [command]
``` 