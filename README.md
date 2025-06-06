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
pip install rmnode
```

## Basic Usage

1. Connect to a node:
```bash
rmnode connection connect --node-id your-node-id
```

2. Send a device command:
```bash
rmnode device send-command --node-id your-node-id --role 1 --command 0
```

3. Monitor messages on a topic:
```bash
rmnode messaging monitor --topic "your/topic/#"
```

## Configuration

The CLI tool uses a configuration directory (default: `.rmnode/`) to store settings and certificates.

You can specify a custom config directory:

```bash
rmnode --config-dir /path/to/config
```

### Admin CLI Configuration

Get current admin CLI path:
```bash
rmnode config get-admin-cli
```

Set admin CLI path:
```bash
rmnode config set-admin-cli /path/to/admin/cli
```

## Connection Management

### Device Management

Add a new device connection:
```bash
rmnode connection add --name "my-device" --cert "path/to/cert.pem" --key "path/to/key.pem"
```

List connections:
```bash
rmnode connection list
```

Show connection details:
```bash
rmnode connection show --name "my-device"
```

Test connection:
```bash
rmnode connection test --name "my-device"
```

Set active connection:
```bash
rmnode connection set-active --name "my-device"
```

Remove connection:
```bash
rmnode connection remove --name "my-device"
```

Update connection:
```bash
rmnode connection update --name "my-device" --cert "new/cert.pem" --key "new/key.pem"
```

Direct connection:
```bash
rmnode connection connect --node-id "node123" --cert "path/to/cert.pem" --key "path/to/key.pem"
```

Disconnect:
```bash
rmnode connection disconnect
```

Check status:
```bash
rmnode connection status
```

## Messaging

### Subscribe to Topics

```bash
rmnode messaging subscribe --topic "my/topic/#"
```

### Publish Messages

```bash
rmnode messaging publish --topic "my/topic" --message "Hello, MQTT!"
```

### Monitor Topics

```bash
rmnode messaging monitor --topic "my/topic/#"
```

## Device Management

### List Devices

```bash
rmnode device list
```

### Check Device Status

```bash
rmnode device status --device-id "device123"
```

### Send Device Commands

```bash
rmnode device command --device-id "device123" --command "restart"
```

## OTA Updates

### Monitor OTA Status

```bash
rmnode ota monitor --node-id "node123"
```

### Request OTA Update

```bash
rmnode ota request --node-id "node123" --fw-version "1.0.0" --timeout 60
```

### Fetch OTA Update

```bash
rmnode ota fetch --node-id "node123" --fw-version "1.0.0" --network-id "network123"
```

### Update OTA Status

```bash
rmnode ota status --node-id "node123" --status "in-progress" --job-id "job123" --info "25% complete"
```

### Auto Status Updates

Monitor OTA progress with automatic status updates:

```bash
rmnode ota monitor --node-id "node123" --auto-status
```

## Node Configuration

### Configure Node

Using stored configuration:
```bash
rmnode node config --node-id "node123" --use-stored
```

With custom name:
```bash
rmnode node config --node-id "node123" --use-stored --name "Living Room Node"
```

Using custom config file:
```bash
rmnode node config --node-id "node123" --config-file "custom_config.json"
```

### Initialize Parameters

Using stored parameters:
```bash
rmnode node init-params --node-id "node123" --use-stored
rmnode node init-params --node-id "node123" --params-file "init_params.json"
```

### Group Parameters

Configure multiple nodes:
```bash
rmnode node group-params --node-ids "node1,node2,node3" --params-file "group_params.json"
rmnode node group-params --node-ids "node1,node2" --use-stored
```

### Set Parameters

```bash
rmnode node params --node-id "node123" --device-name "Light" --param "power" --value "on"
```

## Device Commands

### Send Commands

Basic command:
```bash
rmnode device send-command --node-id "node123" --role 1 --command 0
rmnode device send-command --node-id "node123" --role 2 --command 1 --command-data '{"param": "value"}'
```

Send alerts:
```bash
rmnode device send-alert --node-id "node123" --message "Temperature high!"
rmnode device send-alert --node-id "node123" --message "Alert!" --basic-ingest
```

## Time Series Data

### Send Data

Single value:
```bash
rmnode tsdata send "node123" "temperature" "25.5" --data-type float
rmnode tsdata send "node123" "power" "true" --data-type bool --simple
```

Batch data:
```bash
rmnode tsdata batch "node123" "temperature" "25.5" "26.0" "26.5" --interval 30
rmnode tsdata batch "node123" "humidity" "45" "48" "50" --data-type int --basic-ingest
```

## User Management

### Map Users to Nodes

Basic mapping:
```bash
rmnode user map --node-id "node123" --user-id "user456" --secret-key "abc123"
```

Advanced mapping:
```bash
rmnode user map --node-id "node123" --user-id "user456" --secret-key "abc123" --timeout 600 --reset
```

Send user alerts:
```bash
rmnode user alert --node-id "node123" --message "System update required"
```

## Node Management

### Get Node Configuration

```bash
rmnode node get-config --node-id "node123"
```

### Set Node Configuration

```bash
rmnode node set-config --node-id "node123" --config-file "config.json"
```

### Reset Node

```bash
rmnode node reset --node-id "node123"
```

## User Mapping

### Map User to Node

```bash
rmnode user map --user-id "user123" --node-id "node123"
```

### List Mappings

```bash
rmnode user list-mappings
```

### Unmap User from Node

```bash
rmnode user unmap --user-id "user123" --node-id "node123"
```

## Time Series Data

### Get Data

```bash
rmnode tsdata get --node-id "node123" --start-time "2024-01-01" --end-time "2024-01-02"
```

### Export Data

```bash
rmnode tsdata export --node-id "node123" --format csv --output "data.csv"
```

## Rainmaker Integration

### Initialize

```bash
rmnode rainmaker init
```

### Get Certificates

```bash
rmnode rainmaker get-certs --node-id "node123"
```

### Provision Node

```bash
rmnode rainmaker provision --node-id "node123"
```

## Additional Features

### List Configured Nodes

```bash
rmnode config list-nodes
```

### List All Connections

```bash
rmnode connection list --all
```

### Show Node Details

```bash
rmnode node show --node-id "node123"
```

### Connect with Certificates

```bash
rmnode connection connect --node-id "node123" --cert "path/to/cert.pem" --key "path/to/key.pem"
```

### Import Node Configuration

```bash
rmnode config import-nodes --base-path "/path/to/nodes" --is-rainmaker
```

## Configuration Directory

The tool uses `.rmnode/` as the default configuration directory. This can be overridden using the `--config-dir` option.

## Advanced Usage

### Update Admin CLI

```bash
rmnode config set-admin-cli "/path/to/admin-cli" --update
```

### Connect Multiple Nodes

Single node:
```bash
rmnode connection connect "node123"
```

Multiple nodes:
```bash
rmnode connection connect "node123" "node456" "node789"
```

Switch active node:
```bash
rmnode connection switch "node456"
```

### Node Configuration

Set configuration:
```bash
rmnode node set-config --node-id "node123" \
    --name "Living Room" \
    --type "light" \
    --version "1.0.0"
```

Set local parameters:
```bash
rmnode node set-local-params "node123" "light" "power" "on"
```

## Node Status

### Check Status

```bash
rmnode node status --node-id "node123"
```

### Update Connection Status

```bash
rmnode node connected --node-id "node123" --ip-address "192.168.1.100"
```

### Monitor Node Presence

```bash
rmnode node monitor-presence --node-id "node123"
```

## Group Operations

### Set Group Parameters

```bash
rmnode node set-local-params "node123" "light" "power" "on" --group-id "group1"
```

### Get Parameters

```bash
rmnode node get-params --node-id "node123"
```

### Monitor Parameters

```bash
rmnode node monitor-params --node-id "node123"
```

## Node Reset and Backup

### Reset Node

```bash
rmnode node reset --node-id "node123"
```

### Backup Configuration

```bash
rmnode node backup-config --node-id "node123" --output "backup.json"
```

### Restore Configuration

```bash
rmnode node restore-config --node-id "node123" --input "backup.json"
```

### Remove Node

```bash
rmnode config remove-node --node-id "node123"
```

## Certificate Management

### Show Certificates

```bash
rmnode node show-certs --node-id "node123"
```

### Update Certificates

```bash
rmnode node update-certs --node-id "node123" --cert "new.crt" --key "new.key"
```

### Verify Certificates

```bash
rmnode node verify-certs --node-id "node123"
```

## Testing and Diagnostics

### Test Connection

```bash
rmnode connection test --node-id "node123"
```

### View Logs

```bash
rmnode node logs --node-id "node123"
```

### Diagnose Issues

```bash
rmnode node diagnose --node-id "node123"
```

## Examples

### Connection Examples

Basic connection:
```bash
rmnode connection connect --node-id "node123"
```

Multiple nodes:
```bash
rmnode connection connect --node-id "node123,node456,node789"
```

Test connection with certificates:
```bash
rmnode connection test --name "my-device" --cert "/path/to/cert.pem" --key "/path/to/key.pem"
```

### OTA Examples

Request update:
```bash
rmnode ota request --node-id "node123" --fw-version "1.0.0"
```

Multiple nodes:
```bash
rmnode ota request --node-id "node123,node456" --fw-version "1.0.0"
```

Monitor multiple nodes:
```bash
rmnode ota monitor --node-id "node123,node456"
```

## Debug Mode

Enable debug logging:
```bash
rmnode --debug [command]
``` 