# OTA Update Management

The OTA (Over-The-Air) command group provides functionality for managing firmware updates and device software upgrades.

## Commands

### Update

Request an OTA update for a node.

```bash
rm-node ota update [OPTIONS]

Options:
  --node-id TEXT       Node ID to update [required]
  --firmware-file PATH Path to firmware file [required]
  --version TEXT       Firmware version [required]
  --force             Force update even if version is older
  --timeout INTEGER   Update timeout in seconds (default: 300)
  -h, --help          Show this help message

Examples:
  # Basic update
  rm-node ota update --node-id node123 --firmware-file firmware.bin --version 1.2.0

  # Force update
  rm-node ota update --node-id node123 --firmware-file firmware.bin --version 1.1.0 --force

  # Update with custom timeout
  rm-node ota update --node-id node123 --firmware-file firmware.bin --version 1.2.0 --timeout 600
```

### Status

Check OTA update status.

```bash
rm-node ota status [OPTIONS]

Options:
  --node-id TEXT  Node ID to check [required]
  --wait         Wait for update to complete
  -h, --help     Show this help message

Examples:
  # Check current status
  rm-node ota status --node-id node123

  # Wait for update completion
  rm-node ota status --node-id node123 --wait
```

## Update Process

1. Preparation
   - Validate firmware file
   - Check version compatibility
   - Verify node connection

2. Upload
   - Transfer firmware file
   - Monitor upload progress
   - Verify file integrity

3. Installation
   - Initiate firmware installation
   - Monitor installation progress
   - Handle installation errors

4. Verification
   - Verify successful update
   - Check new firmware version
   - Validate device operation

## Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 0 | IDLE | No update in progress |
| 1 | DOWNLOADING | Downloading firmware |
| 2 | VERIFYING | Verifying firmware integrity |
| 3 | INSTALLING | Installing firmware |
| 4 | COMPLETED | Update completed successfully |
| 5 | FAILED | Update failed |

## Best Practices

1. Pre-Update
   - Backup current firmware
   - Test update on test device
   - Verify firmware compatibility
   - Check device battery/power

2. During Update
   - Monitor progress closely
   - Don't interrupt power
   - Keep stable connection
   - Log all status changes

3. Post-Update
   - Verify device operation
   - Check all functions
   - Monitor for issues
   - Keep update logs

## Error Handling

1. Connection Errors
   ```bash
   ✗ Failed to connect to node
   # Solution: Check node connection and try again
   ```

2. File Errors
   ```bash
   ✗ Invalid firmware file
   # Solution: Verify file format and integrity
   ```

3. Version Errors
   ```bash
   ✗ Version downgrade not allowed
   # Solution: Use --force flag if downgrade is intended
   ```

4. Timeout Errors
   ```bash
   ✗ Update timeout
   # Solution: Increase timeout value or check connection stability
   ```

## Topics Used

1. Update Control
   - `node/{node_id}/ota/request`
   - `node/{node_id}/ota/response`
   - `node/{node_id}/ota/status`

2. Progress Monitoring
   - `node/{node_id}/ota/progress`
   - `node/{node_id}/ota/error`

## Example Update Flow

1. Start Update
```bash
rm-node ota update --node-id node123 --firmware-file v1.2.0.bin --version 1.2.0
```

2. Monitor Progress
```bash
rm-node ota status --node-id node123 --wait

Progress: ⣾ Downloading firmware (45%)
Progress: ⣽ Verifying firmware
Progress: ⣻ Installing firmware
✓ Update completed successfully
```

3. Verify Version
```bash
✓ Device running firmware version 1.2.0
```

## Recovery Procedures

1. Failed Update
   - Check error logs
   - Retry update
   - Use force flag if needed
   - Contact support if persistent

2. Interrupted Update
   - Check device status
   - Resume update if possible
   - Retry from beginning
   - Use recovery firmware

3. Version Mismatch
   - Verify correct firmware
   - Check compatibility
   - Use force update
   - Document exceptions

## Security Considerations

1. Firmware Validation
   - Verify firmware source
   - Check digital signatures
   - Validate checksums
   - Use secure transfer

2. Access Control
   - Authenticate updates
   - Log update attempts
   - Monitor suspicious activity
   - Implement rollback protection

3. Network Security
   - Use secure connections
   - Encrypt firmware files
   - Protect update server
   - Monitor network traffic 