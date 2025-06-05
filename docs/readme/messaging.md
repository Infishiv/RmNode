# MQTT Messaging

## Commands

### Publish

Publish a message to an MQTT topic.

```bash
rm-node messaging publish [OPTIONS]

Options:
  --topic TEXT     MQTT topic to publish to [required]
  --message TEXT   Message to publish [required]
  --qos INTEGER   Quality of Service (0, 1, or 2) (default: 0)
  --retain        Retain message on broker
  -h, --help      Show this help message

Examples:
  # Basic publish
  rm-node messaging publish --topic "device/temperature" --message "25.5"

  # Publish with QoS and retain
  rm-node messaging publish --topic "device/status" --message "online" --qos 1 --retain

  # Publish JSON message
  rm-node messaging publish --topic "device/config" --message '{"mode":"auto","temp":22}'
```

### Subscribe

Subscribe to MQTT topics and receive messages.

```bash
rm-node messaging subscribe [OPTIONS]

Options:
  --topic TEXT     MQTT topic(s) to subscribe to [required]
  --qos INTEGER   Quality of Service (0, 1, or 2) (default: 0)
  --timeout INTEGER Time in seconds to keep subscription active
  -h, --help      Show this help message

Examples:
  # Basic subscribe
  rm-node messaging subscribe --topic "device/#"

  # Subscribe with QoS
  rm-node messaging subscribe --topic "device/+/temperature" --qos 1

  # Subscribe with timeout
  rm-node messaging subscribe --topic "device/status" --timeout 300
```

### Monitor

Monitor messages on MQTT topics with advanced filtering.

```bash
rm-node messaging monitor [OPTIONS]

Options:
  --topic TEXT      MQTT topic pattern to monitor [required]
  --filter TEXT     JSON path filter for messages
  --format TEXT     Output format (json, table, raw)
  --timeout INTEGER Time in seconds to monitor
  -h, --help       Show this help message

Examples:
  # Basic monitoring
  rm-node messaging monitor --topic "device/#"

  # Monitor with JSON filter
  rm-node messaging monitor --topic "device/+" --filter "$.temperature"

  # Monitor with custom format
  rm-node messaging monitor --topic "device/status" --format table
```

## Topic Patterns

### Wildcards

1. Single-Level (+)
   - Matches one topic level
   - Example: `device/+/temperature`
   - Matches:
     - `device/living-room/temperature`
     - `device/kitchen/temperature`
   - Doesn't match:
     - `device/living-room/sensor/temperature`

2. Multi-Level (#)
   - Matches multiple topic levels
   - Must be last character
   - Example: `device/#`
   - Matches:
     - `device/temperature`
     - `device/living-room/temperature`
     - `device/kitchen/sensor/temperature`

### Common Patterns

1. Device Topics
   ```
   device/{device-id}/temperature
   device/{device-id}/humidity
   device/{device-id}/status
   ```

2. Group Topics
   ```
   group/{group-id}/devices
   group/{group-id}/status
   group/{group-id}/command
   ```

3. System Topics
   ```
   $SYS/broker/clients/connected
   $SYS/broker/messages/sent
   $SYS/broker/uptime
   ```

## Message Formats

### Plain Text
```bash
rm-node messaging publish --topic "sensor/temperature" --message "25.5"
```

### JSON
```bash
rm-node messaging publish --topic "device/config" --message '{
  "mode": "auto",
  "temperature": 22,
  "humidity": 45
}'
```

### Binary
```bash
rm-node messaging publish --topic "device/data" --message "$(cat data.bin | base64)"
```

## Quality of Service (QoS)

1. QoS 0 (At most once)
   - No acknowledgment
   - Fastest delivery
   - May lose messages
   - Best for frequent updates

2. QoS 1 (At least once)
   - Acknowledged delivery
   - May duplicate messages
   - Good balance of reliability

3. QoS 2 (Exactly once)
   - Guaranteed delivery
   - No duplicates
   - Highest overhead
   - Best for critical messages

## Best Practices

1. Topic Design
   - Use hierarchical structure
   - Keep topics short
   - Use descriptive names
   - Plan for scalability

2. Message Design
   - Use consistent formats
   - Validate message structure
   - Include timestamps
   - Consider payload size

3. Subscription Management
   - Clean up subscriptions
   - Use appropriate QoS
   - Handle disconnections
   - Monitor message flow

## Error Handling

1. Connection Errors
   ```bash
   ✗ Failed to connect to broker
   # Solution: Check broker connection
   ```

2. Topic Errors
   ```bash
   ✗ Invalid topic format
   # Solution: Verify topic pattern
   ```

3. Message Errors
   ```bash
   ✗ Invalid message format
   # Solution: Check message structure
   ```

## Monitoring Output

### JSON Format
```json
{
  "topic": "device/temperature",
  "message": "25.5",
  "qos": 0,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Table Format
```
| Timestamp            | Topic              | QoS | Message |
|---------------------|-------------------|-----|---------|
| 2024-01-01 12:00:00 | device/temperature | 0   | 25.5    |
```

### Raw Format
```
device/temperature: 25.5
```

## Performance Tips

1. Publishing
   - Use appropriate QoS
   - Batch related messages
   - Compress large payloads
   - Monitor rate limits

2. Subscribing
   - Use specific topics
   - Handle message volume
   - Process efficiently
   - Clean up resources

3. Monitoring
   - Use filters wisely
   - Choose right format
   - Set timeouts
   - Handle large volumes 