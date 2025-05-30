"""
Time series data commands for MQTT CLI.
"""
import click
import json
import time
import asyncio
import sys
import logging
from typing import Optional, List, Union
from ..utils.exceptions import MQTTError
from ..utils.validators import validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations
from ..utils.debug_logger import debug_log, debug_step

# Get logger for this module
logger = logging.getLogger(__name__)

@click.group()
def tsdata():
    """Time series data commands for sending metrics to nodes."""
    pass

@debug_step("Ensuring node connection")
async def ensure_node_connection(ctx, node_id: str) -> bool:
    """Ensure connection to a node is active, connect if needed."""
    try:
        # Get config manager
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        cert_paths = config_manager.get_node_paths(node_id)
        if not cert_paths:
            logger.debug(f"Node {node_id} not found in configuration")
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            return False
            
        cert_path, key_path = cert_paths
        
        # Get broker URL from config
        broker_url = config_manager.get_broker()
        
        # Create new MQTT client
        mqtt_client = MQTTOperations(
            broker=broker_url,
            node_id=node_id,
            cert_path=cert_path,
            key_path=key_path
        )
        
        # Connect
        if mqtt_client.connect():
            logger.debug(f"Connected to node {node_id}")
            ctx.obj['MQTT'] = mqtt_client
            return True
        logger.debug(f"Failed to connect to node {node_id}")
        return False
    except Exception as e:
        logger.debug(f"Connection error: {str(e)}")
        click.echo(click.style(f"✗ Connection error: {str(e)}", fg='red'), err=True)
        return False

@tsdata.command('send')
@click.argument('node_id')
@click.argument('param_name')
@click.argument('value')
@click.option('--data-type', '-t', type=click.Choice(['bool', 'int', 'float', 'string', 'array', 'object']), 
              default='float', help='Data type of the metric')
@click.option('--simple', is_flag=True, help='Use simplified time series data format with lesser aggregations')
@click.option('--expiry-days', '-d', type=int, help='Optional expiration days for data retention (simple format only)')
@click.option('--basic-ingest', is_flag=True, help='Use basic ingest topic ($aws/rules/esp_*_ts_ingest/...) to save costs')
@click.pass_context
@debug_log
def send_tsdata(ctx, node_id, param_name, value, data_type, simple, expiry_days, basic_ingest):
    """Send time series data to a node.
    
    For simple format (--simple flag):
    - Sends data in a simplified format with lesser aggregations
    - Supports optional expiration days
    - Uses version 2021-09-13 format
    
    For standard format (default):
    - Sends full time series data with all aggregations
    - Supports multiple records and overwrite options
    - Uses version 2021-09-13 format
    """
    try:
        # Create event loop for async operations
        logger.debug("Creating event loop for async operations")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        logger.debug(f"Ensuring connection to node {node_id}")
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            sys.exit(1)
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            logger.debug("No active MQTT connection found")
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            sys.exit(1)

        logger.debug(f"Validating node ID: {node_id}")
        validate_node_id(node_id)
        
        # Convert value to the correct type
        try:
            logger.debug(f"Converting value to type {data_type}")
            if data_type == 'bool':
                value = value.lower() in ('true', '1', 'yes', 'on')
            elif data_type == 'int':
                value = int(value)
            elif data_type == 'float':
                value = float(value)
            elif data_type == 'array':
                value = json.loads(value)
                if not isinstance(value, list):
                    raise ValueError("Value must be a valid JSON array")
            elif data_type == 'object':
                value = json.loads(value)
                if not isinstance(value, dict):
                    raise ValueError("Value must be a valid JSON object")
            logger.debug(f"Value converted successfully: {value}")
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Value conversion failed: {str(e)}")
            click.echo(click.style(f"✗ Invalid value for type {data_type}: {str(e)}", fg='red'), err=True)
            sys.exit(1)
        
        timestamp = int(time.time())
        
        if simple:
            logger.debug("Using simple time series format")
            payload = {
                "name": param_name,
                "dt": data_type,
                "t": timestamp,
                "v": {"value": value}
            }
            if expiry_days is not None:
                logger.debug(f"Adding expiry days: {expiry_days}")
                payload["d"] = expiry_days
                
            topic = "$aws/rules/esp_simple_ts_ingest/node/" if basic_ingest else "node/"
            topic += f"{node_id}/simple_tsdata"
        else:
            logger.debug("Using standard time series format")
            payload = {
                "ts_data_version": "2021-09-13",
                "ts_data": [{
                    "name": param_name,
                    "dt": data_type,
                    "ow": False,
                    "records": [{
                        "v": {"value": value},
                        "t": timestamp
                    }]
                }]
            }
            topic = "$aws/rules/esp_ts_ingest/node/" if basic_ingest else "node/"
            topic += f"{node_id}/tsdata"

        logger.debug(f"Publishing to topic: {topic}")
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            logger.debug("Time series data published successfully")
            click.echo(click.style(f"✓ Sent time series data for node {node_id}", fg='green'))
            click.echo(json.dumps(payload, indent=2))
            return 0
        else:
            logger.debug("Failed to publish time series data")
            click.echo(click.style("✗ Failed to publish time series data", fg='red'), err=True)
            sys.exit(1)
        
    except Exception as e:
        logger.debug(f"Error in send_tsdata: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@tsdata.command('batch')
@click.argument('node_id')
@click.argument('param_name')
@click.argument('values', nargs=-1)
@click.option('--data-type', '-t', type=click.Choice(['bool', 'int', 'float', 'string', 'array', 'object']), 
              default='float', help='Data type of the metric (as per 2021-09-13 spec)')
@click.option('--interval', default=30, help='Time interval between records in seconds')
@click.option('--basic-ingest', is_flag=True, help='Use basic ingest topic ($aws/rules/esp_ts_ingest/...) to save costs')
@click.pass_context
@debug_log
def send_batch_tsdata(ctx, node_id, param_name, values, data_type, interval, basic_ingest):
    """Send multiple time series data points in batch.
    
    This command uses the standard time series format (2021-09-13) to send multiple
    data points with specified intervals between them. Each value will be assigned
    a timestamp starting from current time and incrementing by the specified interval.
    
    The data will be sent using the full time series format with all aggregations enabled.
    For cost optimization, use the --basic-ingest flag to use the AWS Rules ingest topic.
    """
    try:
        # Create event loop for async operations
        logger.debug("Creating event loop for async operations")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        logger.debug(f"Ensuring connection to node {node_id}")
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            sys.exit(1)
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            logger.debug("No active MQTT connection found")
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            sys.exit(1)

        logger.debug(f"Validating node ID: {node_id}")
        validate_node_id(node_id)
        
        # Convert values to the correct type
        converted_values = []
        try:
            logger.debug(f"Converting {len(values)} values to type {data_type}")
            for val in values:
                if data_type == 'bool':
                    val = val.lower() in ('true', '1', 'yes', 'on')
                elif data_type == 'int':
                    val = int(val)
                elif data_type == 'float':
                    val = float(val)
                elif data_type == 'array':
                    val = json.loads(val)
                    if not isinstance(val, list):
                        raise ValueError("Value must be a valid JSON array")
                elif data_type == 'object':
                    val = json.loads(val)
                    if not isinstance(val, dict):
                        raise ValueError("Value must be a valid JSON object")
                converted_values.append(val)
            logger.debug("Values converted successfully")
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Value conversion failed: {str(e)}")
            click.echo(click.style(f"✗ Invalid value for type {data_type}: {str(e)}", fg='red'), err=True)
            sys.exit(1)
            
        # Create records with timestamps
        logger.debug("Creating records with timestamps")
        base_timestamp = int(time.time())
        records = []
        for i, val in enumerate(converted_values):
            records.append({
                "v": {"value": val},
                "t": base_timestamp + (i * interval)
            })
            
        payload = {
            "ts_data_version": "2021-09-13",
            "ts_data": [{
                "name": param_name,
                "dt": data_type,
                "ow": False,
                "records": records
            }]
        }
        
        topic = "$aws/rules/esp_ts_ingest/node/" if basic_ingest else "node/"
        topic += f"{node_id}/tsdata"
        
        logger.debug(f"Publishing batch data to topic: {topic}")
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            logger.debug("Batch time series data published successfully")
            click.echo(click.style(f"✓ Sent batch time series data for node {node_id}", fg='green'))
            click.echo(json.dumps(payload, indent=2))
            return 0
        else:
            logger.debug("Failed to publish batch time series data")
            click.echo(click.style("✗ Failed to publish time series data", fg='red'), err=True)
            sys.exit(1)
            
    except Exception as e:
        logger.debug(f"Error in send_batch_tsdata: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1) 