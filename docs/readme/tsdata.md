# Time Series Data Commands

The time series data command group provides functionality for sending metrics and time series data to nodes.

## Commands

### 1. Send

Send a single time series data point.

```bash
mqtt-cli tsdata send [OPTIONS]

Options:
  --node-id TEXT                                Node ID to send data to [required]
  --param-name TEXT                             Name of the parameter to send [required]
  --value TEXT                                  Value to send [required]
  --data-type [bool|int|float|string|array|object]  Data type of the metric (default: float)
  --basic-ingest                               Use basic ingest topic to save costs
  -h, --help                                   Show this help message

Examples:
  # Send temperature reading
  mqtt-cli tsdata send --node-id node123 --param-name temperature --value 25.5

  # Send boolean status
  mqtt-cli tsdata send --node-id node123 --param-name status --value true --data-type bool

  # Send JSON configuration
  mqtt-cli tsdata send --node-id node123 --param-name config --value '{"mode":"auto"}' --data-type object
```

### 2. Batch

Send multiple time series data points in batch.

```bash
mqtt-cli tsdata batch [OPTIONS]

Options:
  --node-id TEXT                                Node ID to send data to [required]
  --param-name TEXT                             Name of the parameter to send [required]
  --values TEXT                                 List of values to send [required]
  --data-type [bool|int|float|string|array|object]  Data type of the metric (default: float)
  --interval INTEGER                            Time interval between records in seconds (default: 30)
  --basic-ingest                               Use basic ingest topic to save costs
  -h, --help                                   Show this help message

Examples:
  # Send temperature readings
  mqtt-cli tsdata batch --node-id node123 --param-name temperature --values 25.5 26.0 26.5 --interval 60

  # Send status changes
  mqtt-cli tsdata batch --node-id node123 --param-name status --values true false true --data-type bool

  # Send configuration changes
  mqtt-cli tsdata batch --node-id node123 --param-name config --values '{"mode":"auto"}' '{"mode":"manual"}' --data-type object
```

## Data Types

The CLI supports the following data types (as per 2021-09-13 spec):

1. `bool`: Boolean values (true/false)
2. `int`: Integer numbers
3. `float`: Floating-point numbers
4. `string`: Text strings
5. `array`: JSON arrays
6. `object`: JSON objects

## Time Series Format

### Single Data Point
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "param_name": "temperature",
  "value": 25.5,
  "data_type": "float"
}
```

### Batch Data Points
```json
{
  "data": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "value": 25.5
    },
    {
      "timestamp": "2024-01-01T12:01:00Z",
      "value": 26.0
    }
  ],
  "param_name": "temperature",
  "data_type": "float"
}
```

## Topics

### Standard Topics
- `node/{node_id}/data/timeseries`
- `node/{node_id}/data/timeseries/batch`

### Basic Ingest Topics (Cost-Optimized)
- `$aws/rules/esp_ts_ingest/node/{node_id}/data`
- `$aws/rules/esp_ts_ingest/node/{node_id}/batch`

## Best Practices

1. Data Collection
   - Use consistent data types
   - Set appropriate intervals
   - Validate data before sending
   - Use batch for multiple points

2. Cost Optimization
   - Use basic ingest topics
   - Batch data when possible
   - Choose appropriate intervals
   - Monitor data volume

3. Data Quality
   - Validate data ranges
   - Handle missing values
   - Use appropriate precision
   - Document data formats

## Error Handling

1. Data Format Errors
   ```bash
   ✗ Invalid data format
   # Solution: Check value matches data type
   ```

2. Connection Errors
   ```bash
   ✗ Failed to send data
   # Solution: Verify node connection
   ```

3. Batch Errors
   ```bash
   ✗ Invalid batch format
   # Solution: Check values array format
   ```

## Example Use Cases

1. Temperature Monitoring
```bash
# Send current temperature
mqtt-cli tsdata send --node-id node123 --param-name temperature --value 25.5

# Send temperature history
mqtt-cli tsdata batch --node-id node123 --param-name temperature --values "25.5 26.0 26.5" --interval 300
```

2. Device Status Tracking
```bash
# Send current status
mqtt-cli tsdata send --node-id node123 --param-name status --value true --data-type bool

# Send status history
mqtt-cli tsdata batch --node-id node123 --param-name status --values "true false true" --data-type bool --interval 3600
```

3. Configuration Changes
```bash
# Send current config
mqtt-cli tsdata send --node-id node123 --param-name config --value '{"mode":"auto"}' --data-type object

# Send config history
mqtt-cli tsdata batch --node-id node123 --param-name config --values '{"mode":"auto"}' '{"mode":"manual"}' --data-type object
```

## Performance Considerations

1. Batch Processing
   - Reduces network overhead
   - More efficient storage
   - Better cost optimization
   - Improved throughput

2. Data Types
   - Use appropriate types
   - Minimize string usage
   - Optimize object size
   - Consider storage costs

3. Intervals
   - Balance frequency needs
   - Consider data importance
   - Optimize storage costs
   - Handle time zones

## Data Retention

1. Standard Ingest
   - Full data retention
   - All aggregations enabled
   - Higher storage costs
   - Better data analysis

2. Basic Ingest
   - Cost-optimized storage
   - Limited aggregations
   - Reduced query capability
   - Lower storage costs 