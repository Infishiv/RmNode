# Connection Management

## Commands

### Connect

Connect to one or more nodes.

```bash
rm-node connection connect [OPTIONS]
```

Options:
- `--node-id`: Node ID(s) to connect to (required)
- `--timeout`: Connection timeout in seconds
- `--persistent`: Keep connection alive until terminal is closed or interrupted
- `--broker`: Override default MQTT broker URL

Examples:
```bash
rm-node connection connect --node-id node123
rm-node connection connect --node-id "node123,node456,node789"
rm-node connection connect --node-id node123 --timeout 3600
rm-node connection connect --node-id node123 --persistent
rm-node connection connect --node-id node123 --broker mqtt://custom-broker.example.com
```

### Disconnect

Disconnect from one or more nodes.

```bash
rm-node connection disconnect [OPTIONS]
```

Options:
- `--node-id`: Node ID to disconnect from
- `--all`: Disconnect from all nodes

Examples:
```bash
rm-node connection disconnect --node-id node123
rm-node connection disconnect --all
rm-node connection disconnect
```

### List

List active connections.

```bash
rm-node connection list [OPTIONS]
```

Options:
- `--all`: Show all connections including inactive ones

Examples:
```bash
rm-node connection list
rm-node connection list --all
```

### Switch

Switch active connection to another node.

```bash
rm-node connection switch [OPTIONS]
```

Options:
- `--node-id`: Node ID to switch to (required)

Examples:
```bash
rm-node connection switch --node-id node123
```

## Connection States

Connections can have the following states:
- ✓ Connected: Node is actively connected
- ✗ Disconnected: Node is configured but not connected
- (active): Indicates the currently active node

## Connection Configuration

The CLI maintains connection information in two files:
1. `connection.json`: Stores persistent configuration (certificates, keys, default settings)
2. `connection_state.json`: Tracks active connections and their runtime state

### Example connection.json
```json
{
  "active_node": "node123",
  "connections": {
    "node123": {
      "broker": "mqtt://broker.example.com",
      "cert_path": "/path/to/cert.pem",
      "key_path": "/path/to/key.pem"
    }
  }
}
```

### Example connection_state.json
```json
{
  "node123": {
    "broker": "mqtt://broker.example.com",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "pid": 12345
  }
}
```

## Best Practices

1. Always check connection status before performing operations
2. Use timeouts for temporary connections
3. Disconnect explicitly when done to free up resources
4. Use the `--debug` flag for detailed connection logging
5. Keep track of the active node when working with multiple connections 