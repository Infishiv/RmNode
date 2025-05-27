"""
User-node mapping commands for ESP RainMaker.

This module provides commands for managing user-node mappings and sending alerts.
"""
import click
import json
import time
import asyncio
from ..utils.exceptions import MQTTError
from ..utils.validators import validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations

@click.group()
def user():
    """User-node mapping and alert management commands.
    
    This command group provides functionality to:
    - Map users to nodes with authentication
    - Send alerts to specific nodes
    - Manage user-node relationships
    
    Example usage:
        mqtt-cli user map --node-id node123 --user-id user456 --secret-key abc123
        mqtt-cli user alert --node-id node123 --message "System update required"
    """
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

@user.command('map')
@click.option('--node-id', required=True, help='Node ID to map the user to')
@click.option('--user-id', required=True, help='User ID to map to the node')
@click.option('--secret-key', required=True, help='Secret key for authentication')
@click.option('--reset', is_flag=True, help='Reset the existing mapping')
@click.option('--timeout', default=300, type=int, help='Mapping timeout in seconds (default: 300)')
@click.pass_context
def map_user(ctx, node_id, user_id, secret_key, reset, timeout):
    """Map a user to a node with authentication.
    
    This command creates or updates a mapping between a user and a node.
    The mapping requires a secret key for authentication.
    
    Examples:
        mqtt-cli user map --node-id node123 --user-id user456 --secret-key abc123
        mqtt-cli user map --node-id node123 --user-id user456 --secret-key abc123 --reset
        mqtt-cli user map --node-id node123 --user-id user456 --secret-key abc123 --timeout 600
    """
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
        
        mapping = {
            "node_id": node_id,
            "user_id": user_id,
            "secret_key": secret_key,
            "reset": reset,
            "timeout": timeout
        }

        topic = f"node/{node_id}/user/mapping"
        if mqtt_client.publish(topic, json.dumps(mapping), qos=1):
            click.echo(click.style(f"✓ Created user mapping for node {node_id}", fg='green'))
            click.echo("\nMapping Details:")
            click.echo(f"Node ID: {node_id}")
            click.echo(f"User ID: {user_id}")
            click.echo(f"Reset: {reset}")
            click.echo(f"Timeout: {timeout} seconds")
        else:
            click.echo(click.style("✗ Failed to publish user mapping", fg='red'), err=True)
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@user.command('alert')
@click.option('--node-id', required=True, help='Node ID to send the alert to')
@click.option('--message', required=True, help='Alert message to send')
@click.pass_context
def send_alert(ctx, node_id, message):
    """Send an alert message to a node.
    
    This command sends an alert message to a specific node.
    The alert will be delivered via MQTT and can be used for notifications
    or system messages.
    
    Examples:
        mqtt-cli user alert --node-id node123 --message "System update required"
        mqtt-cli user alert --node-id node123 --message "Battery low"
    """
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
        
        payload = {
            "nodeId": node_id,
            "messageBody": {
                "message": message
            }
        }

        topic = f"node/{node_id}/alert"
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style(f"✓ Sent alert for node {node_id}", fg='green'))
            click.echo("\nAlert Details:")
            click.echo(f"Node ID: {node_id}")
            click.echo(f"Message: {message}")
            click.echo("\nFull Payload:")
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(click.style("✗ Failed to publish alert", fg='red'), err=True)
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 