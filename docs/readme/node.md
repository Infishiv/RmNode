# Node Management

## Commands

### Configure Node

Configure node settings and parameters.

```bash
rm-node node config [OPTIONS]
```

Options:
- `--node-id`: Node ID to configure (required)
- `--device-type`: Device type
- `--project-name`: Project name
- `--config-file`: Configuration file path

Examples:
```bash
rm-node node config --node-id node123 --device-type light --project-name "Smart Home"
rm-node node config --node-id node123 --device-type heater --config-file custom_config.json
```

### Set Parameters

Set node parameters.

```bash
rm-node node params [OPTIONS]
```

Options:
- `--node-id`: Node ID (required)
- `--device-name`: Device name (required)
- `--params-file`: Parameters file path
- `--use-stored`: Use stored parameters
- `--remote`: Use remote configuration

Examples:
```bash
rm-node node params --node-id node123 --device-name "Water Heater" --params-file params.json
rm-node node params --node-id node123 --device-name "Water Heater" --use-stored --remote
```

### Group Parameters

Configure parameters for multiple nodes.

```bash
rm-node node group-params [OPTIONS]
```

Options:
- `--node-ids`: Comma-separated list of node IDs (required)
- `--params-file`: Parameters file path
- `--use-stored`: Use stored parameters

Examples:
```bash
rm-node node group-params --node-ids "node1,node2,node3" --params-file group_params.json
rm-node node group-params --node-ids "node1,node2,node3" --use-stored
```

### Node Presence

#### Connected

Mark a node as connected.

```bash
rm-node node presence connected [OPTIONS]
```

Options:
- `--node-id`: Node ID (required)
- `--ip-address`: Node's IP address

Examples:
```bash
rm-node node presence connected --node-id node123
```

#### Disconnected

Mark a node as disconnected.

```bash
rm-node node presence disconnected [OPTIONS]
```

Options:
- `--node-id`: Node ID (required)
- `--reason`: Disconnection reason

Examples:
```bash
rm-node node presence disconnected --node-id node123
```

## Configuration Files

### Device Configuration Template Example
```json
{
  "device_type": "light",
  "name": "Smart Light",
  "params": {
    "power": false,
    "brightness": 100,
    "color_temp": 4000
  }
}
```

### Parameters File Example
```json
{
  "power": true,
  "brightness": 75,
  "color_temp": 3000,
  "schedule": {
    "on": "07:00",
    "off": "22:00"
  }
}
```

## Best Practices

1. Configuration Management
   - Use version control for configuration files
   - Document custom configurations
   - Validate JSON files before applying

2. Parameter Updates
   - Test parameters on single node before group updates
   - Keep backup of current parameters
   - Use meaningful device names

3. Presence Management
   - Monitor connection status regularly
   - Handle disconnections gracefully
   - Track session information

4. Group Operations
   - Verify all nodes before group updates
   - Use consistent parameter formats
   - Monitor update success/failure

## Error Handling

1. Configuration Errors
   ```bash
   ✗ Invalid configuration format
   # Solution: Validate JSON structure
   ```

2. Parameter Update Errors
   ```bash
   ✗ Failed to update parameters
   # Solution: Check node connection and parameter format
   ```

3. Presence Status Errors
   ```bash
   ✗ Failed to update presence
   # Solution: Verify node ID and connection status
   ```

## Topics Used

1. Configuration
   - `node/{node_id}/config`
   - `node/{node_id}/config/response`

2. Parameters
   - `node/{node_id}/params/local`
   - `node/{node_id}/params/remote`
   - `node/{node_id}/params/local/group`

3. Presence
   - `node/{node_id}/presence/connected`
   - `node/{node_id}/presence/disconnected` 