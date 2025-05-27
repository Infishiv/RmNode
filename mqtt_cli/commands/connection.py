"""
Connection management commands for MQTT CLI.
"""
import click
import asyncio
from pathlib import Path
from ..core.mqtt_client import connect_single_node
from ..mqtt_operations import MQTTOperations
from ..utils.validators import validate_broker_url, validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..utils.config_manager import ConfigManager
from ..utils.cert_finder import get_cert_and_key_paths, get_root_cert_path

@click.group()
def connection():
    """Connection management commands."""
    pass

def verify_connection(mqtt_client):
    """Verify if the connection is active and reconnect if needed."""
    try:
        if not mqtt_client or not mqtt_client.is_connected():
            return False
        # Try a ping to verify connection is truly alive
        if not mqtt_client.ping():
            mqtt_client.reconnect()
        return mqtt_client.is_connected()
    except Exception:
        return False

async def connect_node(ctx, node_id, broker=None):
    """Connect to a single node asynchronously."""
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        cert_path, key_path = config_manager.get_node_paths(node_id)
        
        if not cert_path or not key_path:
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            return False
            
        # Get broker URL from config or parameter
        broker_url = broker or config_manager.get_broker()
        
        # Get root certificate path
        root_path = get_root_cert_path(ctx.obj['CONFIG_DIR'])
        
        try:
            mqtt_client = MQTTOperations(
                broker=broker_url,
                node_id=node_id,
                cert_path=cert_path,
                key_path=key_path,
                root_path=root_path
            )
            
            if await asyncio.get_event_loop().run_in_executor(None, mqtt_client.connect):
                connection_manager = ctx.obj['CONNECTION_MANAGER']
                connection_manager.add_connection(node_id, broker_url, cert_path, key_path, mqtt_client)
                click.echo(click.style(f"✓ Connected to {node_id}", fg='green'))
                return True
            else:
                click.echo(click.style(f"✗ Failed to connect to {node_id}", fg='red'), err=True)
                return False
                
        except Exception as e:
            click.echo(click.style(f"✗ Connection failed for {node_id}: {str(e)}", fg='red'), err=True)
            return False
            
    except Exception as e:
        click.echo(click.style(f"✗ Error for {node_id}: {str(e)}", fg='red'), err=True)
        return False

@connection.command('connect')
@click.option('--node-id', required=True, help='Node ID(s) to connect to. Can be single ID or comma-separated list')
@click.option('--broker', help="Override default MQTT broker URL")
@click.option('--debug', is_flag=True, help="Show debug information")
@click.pass_context
def connect(ctx, node_id, broker, debug):
    """Connect to one or more nodes using stored configuration.
    
    Examples:
        mqtt-cli connection connect --node-id node123
        mqtt-cli connection connect --node-id "node123,node456,node789"
    """
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Split node_id if it contains commas
        node_ids = [n.strip() for n in node_id.split(',')]
        
        # Create tasks for each node connection
        tasks = [connect_node(ctx, n, broker) for n in node_ids]
        
        # Run all connections in parallel
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        # Set the first successful connection as active
        for n, success in zip(node_ids, results):
            if success:
                ctx.obj['NODE_ID'] = n
                ctx.obj['MQTT'] = ctx.obj['CONNECTION_MANAGER'].get_connection(n)
                break
                
        loop.close()
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@connection.command('disconnect')
@click.option('--node-id', help='Specific node ID to disconnect')
@click.option('--all', is_flag=True, help='Disconnect all nodes')
@click.pass_context
def disconnect(ctx, node_id, all):
    """Disconnect from one or all nodes."""
    connection_manager = ctx.obj['CONNECTION_MANAGER']
    
    if all:
        # Disconnect all nodes
        results = connection_manager.disconnect_all()
        for node_id, success in results.items():
            if success:
                click.echo(click.style(f"✓ Disconnected from {node_id}", fg='green'))
            else:
                click.echo(click.style(f"✗ Failed to disconnect from {node_id}", fg='red'))
        ctx.obj['MQTT'] = None
        ctx.obj['NODE_ID'] = None
    elif node_id:
        # Disconnect specific node
        if connection_manager.remove_connection(node_id):
            click.echo(click.style(f"✓ Disconnected from {node_id}", fg='green'))
            if ctx.obj.get('NODE_ID') == node_id:
                ctx.obj['MQTT'] = None
                ctx.obj['NODE_ID'] = None
        else:
            click.echo(click.style(f"✗ No connection found for {node_id}", fg='red'))
    else:
        # Disconnect active node
        active_node = ctx.obj.get('NODE_ID')
        if not active_node:
            click.echo(click.style("ℹ No active connection to disconnect", fg='yellow'))
            return
            
        if connection_manager.remove_connection(active_node):
            click.echo(click.style(f"✓ Disconnected from {active_node}", fg='green'))
            ctx.obj['MQTT'] = None
            ctx.obj['NODE_ID'] = None
        else:
            click.echo(click.style(f"✗ Failed to disconnect from {active_node}", fg='red'))

@connection.command('list')
@click.option('--all', is_flag=True, help='Show all configured nodes, not just active connections')
@click.pass_context
def list_connections(ctx, all):
    """List active connections and configured nodes."""
    conn_manager = ctx.obj.get('CONNECTION_MANAGER')
    config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
    
    # Get all configured nodes
    configured_nodes = config_manager.list_nodes()
    
    # Get active connections and verify their status
    active_connections = {}
    if conn_manager:
        for node_id, client in conn_manager.connections.items():
            is_connected = verify_connection(client)
            if not is_connected:
                # Try to reconnect if connection is lost
                try:
                    client.reconnect()
                    is_connected = client.is_connected()
                except:
                    is_connected = False
            active_connections[node_id] = is_connected
    
    if not configured_nodes and not active_connections:
        click.echo(click.style("No nodes configured or connected", fg='yellow'))
        return

    click.echo("\nNode Status:")
    click.echo("-" * 60)
    
    # Print header
    click.echo(f"{'Status':<10} {'Node ID':<40} {'Connection':<10}")
    click.echo("-" * 60)
    
    # Show all nodes if --all flag is used
    if all:
        for node_id in configured_nodes:
            is_connected = active_connections.get(node_id, False)
            status = "✓" if is_connected else "✗"
            status_color = 'green' if is_connected else 'red'
            active = " (active)" if conn_manager and node_id == conn_manager.active_node else ""
            connection = "Connected" if is_connected else "Configured"
            click.echo(f"{click.style(status, fg=status_color):<10} {node_id:<40} {connection:<10}{active}")
    else:
        # Show only active connections
        if not active_connections:
            click.echo(click.style("No active connections", fg='yellow'))
            return
            
        for node_id, is_connected in active_connections.items():
            status = "✓" if is_connected else "✗"
            status_color = 'green' if is_connected else 'red'
            active = " (active)" if node_id == conn_manager.active_node else ""
            connection = "Connected" if is_connected else "Disconnected"
            click.echo(f"{click.style(status, fg=status_color):<10} {node_id:<40} {connection:<10}{active}")
    
    click.echo("-" * 60)

@connection.command('switch')
@click.option('--node-id', required=True, help='Node ID to switch to')
@click.pass_context
def switch_node(ctx, node_id):
    """Switch active connection to specified node.
    
    Example: mqtt-cli connection switch --node-id node123
    """
    conn_manager = ctx.obj.get('CONNECTION_MANAGER')
    config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
    
    try:
        # Verify node exists in configuration
        if not config_manager.get_node_paths(node_id):
            click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
            return
            
        # Check if node is connected
        if not conn_manager or node_id not in conn_manager.connections:
            click.echo(click.style(f"✗ Node {node_id} is not connected. Connect it first using 'connection connect'", fg='red'), err=True)
            return

        # Verify connection is active
        mqtt_client = conn_manager.get_connection(node_id)
        if not verify_connection(mqtt_client):
            click.echo(click.style(f"✗ Connection to {node_id} is not active. Attempting to reconnect...", fg='yellow'))
            try:
                mqtt_client.reconnect()
                if not mqtt_client.is_connected():
                    click.echo(click.style(f"✗ Failed to reconnect to {node_id}", fg='red'), err=True)
                    return
            except Exception as e:
                click.echo(click.style(f"✗ Failed to reconnect to {node_id}: {str(e)}", fg='red'), err=True)
                return

        conn_manager.active_node = node_id
        conn_manager._save()
        click.echo(click.style(f"✓ Switched to node {node_id}", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 