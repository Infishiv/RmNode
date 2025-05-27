"""
Device management commands for MQTT CLI.
"""
import click
import json
import asyncio
from ..utils.exceptions import MQTTError, MQTTConnectionError
from ..utils.validators import validate_node_id
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations
import time

@click.group()
def device():
    """Device management commands."""
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

def load_device_config(device_type: str) -> dict:
    """Load device configuration from config files."""
    try:
        with open(f"device_configs/{device_type}_config.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise MQTTError(f"Configuration file for {device_type} not found")

def load_device_params(device_type: str) -> dict:
    """Load device parameters from params files."""
    try:
        with open(f"device_configs/{device_type}_params.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise MQTTError(f"Parameters file for {device_type} not found")

@device.command('make')
@click.option('--node-id', required=True, help='Node ID to configure')
@click.option('--type', 'device_type', required=True, type=click.Choice(['light', 'washer', 'heater'], case_sensitive=False), help='Type of device to create')
@click.pass_context
def make_device(ctx, node_id: str, device_type: str):
    """Create a new device of specified type.
    
    Example: mqtt-cli device make --node-id node123 --type light
    """
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No MQTT client available", fg='red'), err=True)
            raise click.Abort()
        
        # Load device configuration and parameters
        config = load_device_config(device_type.lower())
        params = load_device_params(device_type.lower())
        
        # Update node_id in config
        config['node_id'] = node_id
        
        # Publish device configuration
        config_topic = f"node/{node_id}/config"
        if mqtt_client.publish(config_topic, json.dumps(config), qos=1):
            click.echo(click.style(f"✓ Published device configuration", fg='green'))
            click.echo(json.dumps(config, indent=2))
        else:
            raise MQTTError("Failed to publish device configuration")
            
        # Publish initial parameters
        params_topic = f"node/{node_id}/params"
        if mqtt_client.publish(params_topic, json.dumps(params), qos=1):
            click.echo(click.style(f"✓ Published device parameters", fg='green'))
            click.echo(json.dumps(params, indent=2))
        else:
            raise MQTTError("Failed to publish device parameters")
            
        # Update current state
        try:
            with open("device_configs/current_state.json", 'r+') as f:
                state = json.load(f)
                state['current_device'] = device_type.lower()
                state['current_config'] = config
                state['current_params'] = params
                f.seek(0)
                json.dump(state, f, indent=2)
                f.truncate()
        except Exception as e:
            click.echo(click.style(f"Warning: Failed to update current state: {str(e)}", fg='yellow'))
        
    except MQTTError as e:
        click.echo(click.style(f"✗ Failed to create device: {str(e)}", fg='red'), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@device.command('set-param')
@click.option('--node-id', required=True, help='Node ID to configure')
@click.option('--device-name', required=True, help='Name of the device')
@click.option('--param', required=True, help='Parameter name to set')
@click.option('--value', required=True, help='Value to set')
@click.pass_context
def set_param(ctx, node_id: str, device_name: str, param: str, value: str):
    """Set a device parameter.
    
    Example: mqtt-cli device set-param --node-id node123 --device-name light --param power --value on
    """
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No MQTT client available", fg='red'), err=True)
            raise click.Abort()
        
        # Prepare parameter update
        params = {
            device_name: {
                param: value
            }
        }
        
        # Publish parameter update
        topic = f"node/{node_id}/params"
        if mqtt_client.publish(topic, json.dumps(params), qos=1):
            click.echo(click.style(f"✓ Set {device_name} {param} to {value}", fg='green'))
            click.echo(json.dumps(params, indent=2))
        else:
            raise MQTTError("Failed to publish parameter update")
            
        # Update current state
        try:
            with open("device_configs/current_state.json", 'r+') as f:
                state = json.load(f)
                if 'current_params' not in state:
                    state['current_params'] = {}
                if device_name not in state['current_params']:
                    state['current_params'][device_name] = {}
                state['current_params'][device_name][param] = value
                f.seek(0)
                json.dump(state, f, indent=2)
                f.truncate()
        except Exception as e:
            click.echo(click.style(f"Warning: Failed to update current state: {str(e)}", fg='yellow'))
        
    except MQTTError as e:
        click.echo(click.style(f"✗ Failed to set parameter: {str(e)}", fg='red'), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@device.command('show')
@click.option('--node-id', required=True, help='Node ID to show')
@click.option('--device-name', required=True, help='Name of the device to show')
@click.pass_context
def show_device(ctx, node_id: str, device_name: str):
    """Show device status.
    
    Example: mqtt-cli device show --node-id node123 --device-name light
    """
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No MQTT client available", fg='red'), err=True)
            raise click.Abort()
        
        # Subscribe to status updates
        status_topic = f"node/{node_id}/params"
        
        def on_message(client, userdata, message):
            try:
                params = json.loads(message.payload.decode())
                if device_name in params:
                    click.echo("\nDevice Status:")
                    click.echo("-" * 20)
                    for param, value in params[device_name].items():
                        click.echo(f"{param}: {value}")
                    click.echo("-" * 20)
                else:
                    click.echo(click.style(f"✗ No status found for device {device_name}", fg='yellow'))
            except json.JSONDecodeError:
                click.echo(click.style("✗ Invalid status format", fg='red'), err=True)

        # Subscribe using the standard subscribe method
        mqtt_client.subscribe(status_topic, qos=1, callback=on_message)
        
        # Request status update
        request_topic = f"node/{node_id}/get/params"
        mqtt_client.publish(request_topic, "", qos=1)
        
        click.echo(f"Waiting for {device_name} status...")
        
        # Keep the script running to receive messages
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            click.echo("\nStopped monitoring device status")
        
    except MQTTError as e:
        click.echo(click.style(f"✗ Failed to get device status: {str(e)}", fg='red'), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 