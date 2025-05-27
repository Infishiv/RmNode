"""
Node configuration and presence management commands.
"""
import click
import json
import time
from ..utils.exceptions import MQTTError
from ..utils.validators import validate_node_id
from ..utils.config_manager import ConfigManager

@click.group()
def node():
    """Node configuration and presence commands."""
    pass

# Node Presence Commands
@node.group()
def presence():
    """Node presence management commands."""
    pass

@presence.command('connected')
@click.option('--node-id', required=True, help='Node ID to mark as connected')
@click.option('--ip-address', default='192.168.1.100', help='Node IP address')
@click.pass_context
def node_connected(ctx, node_id, ip_address):
    """Send node connected event.
    
    Example: mqtt-cli node presence connected --node-id node123 --ip-address 192.168.1.100
    """
    try:
        # Verify node exists in configuration
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        if not config_manager.get_node_paths(node_id):
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            raise click.Abort()
            
        if ctx.obj.get('NODE_ID') != node_id:
            click.echo(click.style(f"✗ Not connected to node {node_id}. Connect first using 'connection connect --node-id {node_id}'", fg='red'), err=True)
            raise click.Abort()

        payload = {
            "clientId": "rainmaker-node",
            "clientInitiatedDisconnect": True,
            "eventType": "connected",
            "principalIdentifier": node_id,
            "sessionIdentifier": f"session-{int(time.time())}",
            "timestamp": int(time.time() * 1000),
            "versionNumber": 0,
            "ipAddress": ip_address
        }

        topic = f"$aws/events/presence/connected/{node_id}"
        mqtt_client.publish(topic, json.dumps(payload), qos=1)
        click.echo(click.style(f"✓ Sent connected event for node {node_id}", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@presence.command('disconnected')
@click.option('--node-id', required=True, help='Node ID to mark as disconnected')
@click.pass_context
def node_disconnected(ctx, node_id):
    """Send node disconnected event.
    
    Example: mqtt-cli node presence disconnected --node-id node123
    """
    try:
        # Verify node exists in configuration
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        if not config_manager.get_node_paths(node_id):
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            raise click.Abort()
            
        if ctx.obj.get('NODE_ID') != node_id:
            click.echo(click.style(f"✗ Not connected to node {node_id}. Connect first using 'connection connect --node-id {node_id}'", fg='red'), err=True)
            raise click.Abort()

        payload = {
            "clientId": "rainmaker-node",
            "clientInitiatedDisconnect": True,
            "eventType": "disconnected",
            "principalIdentifier": node_id,
            "sessionIdentifier": f"session-{int(time.time())}",
            "timestamp": int(time.time() * 1000),
            "versionNumber": 0,
            "disconnectReason": "CLIENT_INITIATED_DISCONNECT"
        }

        topic = f"$aws/events/presence/disconnected/{node_id}"
        mqtt_client.publish(topic, json.dumps(payload), qos=1)
        click.echo(click.style(f"✓ Sent disconnected event for node {node_id}", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

# Node Configuration Commands
@node.group()
def config():
    """Node configuration commands."""
    pass

@config.command('set')
@click.option('--node-id', required=True, help='Node ID to configure')
@click.option('--name', default='ESP RainMaker Device', help='Node name')
@click.option('--model', default='esp32_device', help='Node model')
@click.option('--type', default='Generic Device', help='Node type')
@click.option('--fw-version', default='1.0.0', help='Firmware version')
@click.pass_context
def set_config(ctx, node_id, name, model, type, fw_version):
    """Set node configuration.
    
    Example: mqtt-cli node config set --node-id node123 --name "My ESP Device" --model esp32_device --type "Light" --fw-version 1.0.0
    """
    try:
        # Verify node exists in configuration
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        if not config_manager.get_node_paths(node_id):
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            raise click.Abort()
            
        if ctx.obj.get('NODE_ID') != node_id:
            click.echo(click.style(f"✗ Not connected to node {node_id}. Connect first using 'connection connect --node-id {node_id}'", fg='red'), err=True)
            raise click.Abort()
        
        config = {
            "node_id": node_id,
            "config_version": time.strftime("%Y-%m-%d"),
            "info": {
                "name": name,
                "model": model,
                "platform": "esp32",
                "fw_version": fw_version,
                "type": type
            },
            "attributes": [
                {
                    "name": "cmd-resp",
                    "value": "1"
                }
            ]
        }

        topic = f"node/{node_id}/config"
        mqtt_client.publish(topic, json.dumps(config), qos=1)
        click.echo(click.style(f"✓ Set configuration for node {node_id}", fg='green'))
        click.echo(json.dumps(config, indent=2))
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@node.group()
def params():
    """Node parameters commands."""
    pass

@params.command('set-local')
@click.option('--node-id', required=True, help='Node ID to configure')
@click.option('--device-name', required=True, help='Name of the device')
@click.option('--param', required=True, help='Parameter name to set')
@click.option('--value', required=True, help='Value to set')
@click.option('--group-id', help='Optional group ID')
@click.pass_context
def set_local_params(ctx, node_id, device_name, param, value, group_id):
    """Set local parameters for a node.
    
    Example: mqtt-cli node params set-local --node-id node123 --device-name light --param power --value on
    """
    try:
        # Verify node exists in configuration
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        if not config_manager.get_node_paths(node_id):
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            raise click.Abort()
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            raise click.Abort()
            
        if ctx.obj.get('NODE_ID') != node_id:
            click.echo(click.style(f"✗ Not connected to node {node_id}. Connect first using 'connection connect --node-id {node_id}'", fg='red'), err=True)
            raise click.Abort()
        
        params = {
            device_name: {
                param: value
            }
        }

        # Choose topic based on whether group_id is provided
        topic = f"node/{node_id}/params/local"
        if group_id:
            topic = f"{topic}/{group_id}"

        mqtt_client.publish(topic, json.dumps(params), qos=1)
        click.echo(click.style(f"✓ Set local parameters for node {node_id}", fg='green'))
        click.echo(json.dumps(params, indent=2))
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 