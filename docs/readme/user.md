# User Management

## Commands

### Map User

Map a user to a node with authentication.

```bash
rm-node user map [OPTIONS]

Options:
  --node-id TEXT     Node ID to map the user to [required]
  --user-id TEXT     User ID to map to the node [required]
  --secret-key TEXT  Secret key for authentication [required]
  --reset           Reset the existing mapping
  --timeout INTEGER Time in seconds before mapping expires (default: 300)
  -h, --help        Show this help message

Examples:
  # Create new mapping
  rm-node user map --node-id node123 --user-id user456 --secret-key abc123

  # Reset existing mapping
  rm-node user map --node-id node123 --user-id user456 --secret-key abc123 --reset

  # Create mapping with custom timeout
  rm-node user map --node-id node123 --user-id user456 --secret-key abc123 --timeout 600
```

### Send Alert

Send an alert to a user mapped to a node.

```bash
rm-node user alert [OPTIONS]

Options:
  --node-id TEXT     Node ID to send alert to [required]
  --message TEXT      Alert message [required]
  -h, --help          Show this help message

Examples:
  # Send alert to node123
  rm-node user alert --node-id node123 --message "System update required"
```

## User-Node Mapping

### Mapping Process

1. Authentication
   - User provides secret key
   - CLI validates authentication
   - Creates secure mapping

2. Timeout Handling
   - Default timeout: 300 seconds (5 minutes)
   - Custom timeout can be specified
   - Mapping expires after timeout

3. Reset Process
   - Removes existing mapping
   - Creates fresh mapping
   - Resets timeout counter

## Security Considerations

1. Secret Key Management
   - Use strong secret keys
   - Rotate keys regularly
   - Never share keys in plain text

2. Mapping Timeouts
   - Use appropriate timeout values
   - Consider device usage patterns
   - Handle timeout expiration gracefully

3. Authentication
   - Validate all mapping requests
   - Log authentication attempts
   - Monitor for suspicious activity

## Best Practices

1. User Management
   - Document user-node mappings
   - Regular mapping audits
   - Clean up expired mappings

2. Security
   - Use unique secret keys
   - Implement key rotation
   - Monitor mapping activities

3. Timeout Management
   - Set appropriate timeouts
   - Handle timeout expiration
   - Notify users of expiring mappings

## Error Handling

1. Authentication Errors
   ```bash
   ✗ Invalid secret key
   # Solution: Verify secret key and try again
   ```

2. Mapping Errors
   ```bash
   ✗ Mapping already exists
   # Solution: Use --reset flag to create new mapping
   ```

3. Timeout Errors
   ```bash
   ✗ Invalid timeout value
   # Solution: Use positive integer value for timeout
   ```

## Topics Used

1. Mapping
   - `user/{user_id}/mapping/request`
   - `user/{user_id}/mapping/response`
   - `user/{user_id}/mapping/status`

2. Authentication
   - `user/{user_id}/auth/request`
   - `user/{user_id}/auth/response`

## Example Mapping Flow

1. Initial Request
```bash
rm-node user map --node-id node123 --user-id user456 --secret-key abc123
```

2. Success Response
```
✓ Created mapping for user user456 to node node123
Mapping Details:
- Timeout: 300 seconds
- Expires: 2024-01-01 12:05:00
```

3. Reset Mapping
```bash
rm-node user map --node-id node123 --user-id user456 --secret-key abc123 --reset
```

4. Reset Response
```
✓ Reset mapping for user user456 to node node123
New Mapping Details:
- Timeout: 300 seconds
- Expires: 2024-01-01 12:10:00
```

## Mapping States

1. Active
   - Mapping is current and valid
   - Within timeout period
   - Authentication successful

2. Expired
   - Timeout period elapsed
   - Requires new mapping
   - Authentication required

3. Reset
   - Previous mapping cleared
   - New mapping created
   - Fresh timeout period 