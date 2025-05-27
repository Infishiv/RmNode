"""
Time series data commands for MQTT CLI.
"""
import click
import json
import time
import asyncio
from typing import Optional, List, Union
from ..utils.exceptions import MQTTError
from ..utils.validators import validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations

@click.group()
def tsdata():
    """Time series data commands."""
    pass

async def ensure_node_connection(ctx, node_id: str) -> bool:
    """Ensure connection to a node is active, connect if needed."""
    try:
        # Get config manager
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        cert_paths = config_manager.get_node_paths(node_id)
        if not cert_paths:
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
            ctx.obj['MQTT'] = mqtt_client
            return True
        return False
    except Exception as e:
        click.echo(click.style(f"✗ Connection error: {str(e)}", fg='red'), err=True)
        return False

@tsdata.command('send')
@click.argument('node_id')
@click.argument('param_name')
@click.argument('value')
@click.option('--data-type', '-t', type=click.Choice(['bool', 'int', 'float', 'string', 'array', 'object']), 
              default='float', help='Data type of the metric')
@click.option('--simple', is_flag=True, help='Use simple format')
@click.option('--expiry-days', '-d', type=int, help='Optional expiration days (simple format only)')
@click.option('--basic-ingest', is_flag=True, help='Use basic ingest topic to save costs')
@click.pass_context
def send_tsdata(ctx, node_id, param_name, value, data_type, simple, expiry_days, basic_ingest):
    """Send time series data."""
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
            return
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            return

        validate_node_id(node_id)
        
        # Convert value to the correct type
        try:
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
        except (ValueError, json.JSONDecodeError) as e:
            click.echo(click.style(f"✗ Invalid value for type {data_type}: {str(e)}", fg='red'), err=True)
            return
        
        timestamp = int(time.time())
        
        if simple:
            payload = {
                "name": param_name,
                "dt": data_type,
                "t": timestamp,
                "v": {"value": value}
            }
            if expiry_days is not None:
                payload["d"] = expiry_days
                
            topic = "$aws/rules/esp_simple_ts_ingest/node/" if basic_ingest else "node/"
            topic += f"{node_id}/simple_tsdata"
        else:
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

        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style(f"✓ Sent time series data for node {node_id}", fg='green'))
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(click.style("✗ Failed to publish time series data", fg='red'), err=True)
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@tsdata.command('batch')
@click.argument('node_id')
@click.argument('param_name')
@click.argument('values', nargs=-1)
@click.option('--data-type', '-t', type=click.Choice(['bool', 'int', 'float', 'string', 'array', 'object']), 
              default='float', help='Data type of the metric')
@click.option('--interval', default=30, help='Time interval between records in seconds')
@click.option('--basic-ingest', is_flag=True, help='Use basic ingest topic to save costs')
@click.pass_context
def send_batch_tsdata(ctx, node_id, param_name, values, data_type, interval, basic_ingest):
    """Send batch time series data."""
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
            return
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            return

        validate_node_id(node_id)
        
        # Convert values to the correct type
        converted_values = []
        try:
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
        except (ValueError, json.JSONDecodeError) as e:
            click.echo(click.style(f"✗ Invalid value for type {data_type}: {str(e)}", fg='red'), err=True)
            return
        
        base_timestamp = int(time.time())
        records = []
        
        for i, value in enumerate(converted_values):
            records.append({
                "v": {"value": value},
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
        
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style(f"✓ Sent batch time series data for node {node_id}", fg='green'))
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(click.style("✗ Failed to publish batch time series data", fg='red'), err=True)
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 