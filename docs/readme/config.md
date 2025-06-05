# Configuration Management

The config command group provides functionality for managing certificates, node configurations, and admin CLI integration.

## Commands

### Set Certificate Path

Set the path to certificates.

```bash
rm-node config set-cert-path [OPTIONS]

Options:
  --path TEXT          Path to certificates directory [required]
  --no-update          Don't update existing configurations
  -h, --help          Show this help message

Examples:
  # Set path and update existing nodes
  rm-node config set-cert-path --path /path/to/admin/cli

  # Set path without updating existing nodes
  rm-node config set-cert-path --path /path/to/admin/cli --no-update
```

### Add Node

Add a new node configuration.

```bash
rm-node config add-node [OPTIONS]

Options:
  --node-id TEXT    Node ID to add [required]
  --cert-path TEXT  Path to certificate file [required]
  --key-path TEXT   Path to key file [required]
  -h, --help       Show this help message

Example:
  rm-node config add-node --node-id node123 --cert-path /path/to/cert.pem --key-path /path/to/key.pem
```

### Remove Node

Remove a node configuration.

```bash
rm-node config remove-node [OPTIONS]

Options:
  --node-id TEXT  Node ID to remove [required]
  -h, --help     Show this help message

Example:
  rm-node config remove-node --node-id node123
```

## Configuration Directory

The tool uses `.rm-node/` as the default configuration directory structure:

```
.rm-node/
├── certs/           # Certificate storage
├── configs/         # Configuration files
└── connections.json # Connection information
```

## Configuration Files

1. connection.json
```json
{
  "active_node": "node123",
  "connections": {
    "node123": {
      "cert_path": "/path/to/cert.pem",
      "key_path": "/path/to/key.pem"
    }
  }
}
```

2. connection_state.json
```json
{
  "node123": {
    "timestamp": "2024-01-01T12:00:00Z",
    "pid": 12345
  }
}
```

## Certificate Management

### Certificate Requirements

1. Node Certificates
   - X.509 format
   - PEM encoded
   - Valid signature
   - Not expired

2. Private Keys
   - PEM format
   - Proper permissions
   - Secure storage
   - Backup protection

### Certificate Operations

1. Adding Certificates
   - Validate format
   - Check expiration
   - Set permissions
   - Update config

2. Updating Certificates
   - Backup old certs
   - Validate new certs
   - Update references
   - Test connection

3. Removing Certificates
   - Backup certificates
   - Remove references
   - Clean up files
   - Update config

## Best Practices

1. Certificate Security
   - Secure storage
   - Regular backups
   - Proper permissions
   - Version control

2. Node Management
   - Document nodes
   - Regular audits
   - Clean unused
   - Test connections

3. Path Management
   - Use absolute paths
   - Validate paths
   - Handle spaces
   - Check permissions

## Error Handling

1. Certificate Errors
   ```bash
   ✗ Invalid certificate format
   # Solution: Check certificate file format
   ```

2. Path Errors
   ```bash
   ✗ Path not found
   # Solution: Verify file paths exist
   ```

3. Permission Errors
   ```bash
   ✗ Permission denied
   # Solution: Check file permissions
   ```

## Admin CLI Integration

### Setup Process

1. Initial Setup
   - Set admin CLI path
   - Discover nodes
   - Import certificates
   - Configure nodes

2. Node Discovery
   - Scan for nodes
   - Validate certificates
   - Update configurations
   - Test connections

3. Updates
   - Check for changes
   - Update certificates
   - Sync configurations
   - Verify updates

## Configuration Updates

### Adding New Node
```bash
# 1. Add node configuration
rm-node config add-node --node-id new-node --cert-path /path/to/cert.pem --key-path /path/to/key.pem

# 2. Verify node
rm-node connection connect --node-id new-node
```

### Updating Node
```bash
# 1. Update certificate paths
rm-node config add-node --node-id existing-node --cert-path /path/to/new-cert.pem --key-path /path/to/new-key.pem

# 2. Verify update
rm-node connection connect --node-id existing-node
```

### Removing Node
```bash
# 1. Disconnect node
rm-node connection disconnect --node-id old-node

# 2. Remove configuration
rm-node config remove-node --node-id old-node
```

## Security Considerations

1. Certificate Storage
   - Secure location
   - Proper permissions
   - Regular backups
   - Access control

2. Key Protection
   - Restricted access
   - Encryption at rest
   - Secure transfer
   - Audit logging

3. Configuration Security
   - Version control
   - Change tracking
   - Access logging
   - Regular audits 