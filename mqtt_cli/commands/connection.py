"""
Connection management commands for MQTT CLI.
"""
import click
import asyncio
import sys
import logging
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from ..core.mqtt_client import connect_single_node
from ..mqtt_operations import MQTTOperations
from ..utils.validators import validate_broker_url, validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..utils.config_manager import ConfigManager
from ..utils.cert_finder import get_cert_and_key_paths, get_root_cert_path, get_cert_paths_from_direct_path
from ..utils.debug_logger import debug_log, debug_step

# Get logger for this module
logger = logging.getLogger(__name__)

class SharedConnectionManager:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.state_file = os.path.join(config_dir, 'connection_state.json')
        self._ensure_state_file()

    def _ensure_state_file(self):
        """Create state file if it doesn't exist"""
        if not os.path.exists(self.state_file):
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            self._save_state({})

    def _load_state(self):
        """Load connection state from file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error loading state: {str(e)}")
            return {}

    def _save_state(self, state):
        """Save connection state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.debug(f"Error saving state: {str(e)}")

    def register_connection(self, node_id, broker_url):
        """Register a new connection"""
        state = self._load_state()
        state[node_id] = {
            'broker': broker_url,
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid()
        }
        self._save_state(state)

    def unregister_connection(self, node_id):
        """Remove a connection registration"""
        state = self._load_state()
        if node_id in state:
            del state[node_id]
            self._save_state(state)
            return True
        return False

    def is_connected(self, node_id):
        """Check if a node is registered as connected"""
        state = self._load_state()
        return node_id in state

    def get_all_connections(self):
        """Get all registered connections"""
        return self._load_state()

@click.group()
def connection():
    """Connection management commands."""
    pass

@debug_step("Verifying MQTT connection status")
def verify_connection(mqtt_client):
    """Verify if the connection is active and reconnect if needed."""
    try:
        if not mqtt_client or not mqtt_client.is_connected():
            logger.debug("MQTT client is not connected")
            return False
        # Try a ping to verify connection is truly alive
        if not mqtt_client.ping():
            logger.debug("Ping failed, attempting reconnection")
            mqtt_client.reconnect()
        return mqtt_client.is_connected()
    except Exception as e:
        logger.debug(f"Connection verification failed: {str(e)}")
        return False

@debug_log
async def connect_node(ctx, node_id, broker=None, timeout=None):
    """Connect to a single node asynchronously."""
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        shared_manager = SharedConnectionManager(ctx.obj['CONFIG_DIR'])
        
        # Get broker URL from config or parameter
        broker_url = broker or config_manager.get_broker()
        logger.debug(f"Using broker URL: {broker_url}")
        
        # Get root certificate path
        root_path = get_root_cert_path(ctx.obj['CONFIG_DIR'])
        logger.debug(f"Root certificate path: {root_path}")
        
        # Get certificate paths
        try:
            if ctx.obj.get('CERT_PATH'):
                # Use direct certificate path if provided
                cert_path, key_path = get_cert_paths_from_direct_path(ctx.obj['CERT_PATH'], node_id)
                logger.debug(f"Using certificates from direct path: {cert_path}, {key_path}")
            else:
                # Use stored configuration
                cert_paths = config_manager.get_node_paths(node_id)
                if not cert_paths:
                    logger.debug(f"Certificate paths not found for node {node_id}")
                    click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
                    return False
                cert_path, key_path = cert_paths
        except FileNotFoundError as e:
            logger.debug(f"Certificate error: {str(e)}")
            click.echo(click.style(f"✗ {str(e)}", fg='red'), err=True)
            return False
        
        try:
            logger.debug(f"Initializing MQTT client for node {node_id}")
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
                shared_manager.register_connection(node_id, broker_url)
                logger.debug(f"Successfully connected to node {node_id}")
                click.echo(click.style(f"✓ Connected to {node_id}", fg='green'))
                
                if timeout:
                    # Calculate disconnect time
                    disconnect_time = datetime.now() + timedelta(seconds=timeout)
                    click.echo(click.style(f"Connection will automatically close at {disconnect_time.strftime('%H:%M:%S')}", fg='yellow'))
                    
                    # Create a task to disconnect after timeout
                    async def disconnect_after_timeout():
                        await asyncio.sleep(timeout)
                        if connection_manager.get_connection(node_id):
                            connection_manager.remove_connection(node_id)
                            shared_manager.unregister_connection(node_id)
                            click.echo(click.style(f"\n✓ Auto-disconnected from {node_id} after {timeout} seconds", fg='yellow'))
                            if ctx.obj.get('NODE_ID') == node_id:
                                ctx.obj['MQTT'] = None
                                ctx.obj['NODE_ID'] = None
                    
                    asyncio.create_task(disconnect_after_timeout())
                
                return True
            else:
                logger.debug(f"Failed to connect to node {node_id}")
                click.echo(click.style(f"✗ Failed to connect to {node_id}", fg='red'), err=True)
                return False
                
        except Exception as e:
            logger.debug(f"Connection error for node {node_id}: {str(e)}")
            click.echo(click.style(f"✗ Connection failed for {node_id}: {str(e)}", fg='red'), err=True)
            return False
            
    except Exception as e:
        logger.debug(f"General error for node {node_id}: {str(e)}")
        click.echo(click.style(f"✗ Error for {node_id}: {str(e)}", fg='red'), err=True)
        return False

@connection.command('connect')
@click.option('--node-id', required=True, help='Node ID(s) to connect to. Can be single ID or comma-separated list')
@click.option('--broker', help="Override default MQTT broker URL")
@click.option('--timeout', type=int, help="Time in seconds after which the connection will automatically close")
@click.pass_context
@debug_log
def connect(ctx, node_id, broker, timeout):
    """Connect to one or more nodes using stored configuration.
    
    Examples:
        mqtt-cli connection connect --node-id node123
        mqtt-cli connection connect --node-id "node123,node456,node789"
        mqtt-cli connection connect --node-id node123 --timeout 3600
    """
    try:
        # Create event loop for async operations
        logger.debug("Creating event loop for async operations")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Split node_id if it contains commas
        node_ids = [n.strip() for n in node_id.split(',')]
        logger.debug(f"Processing connection for nodes: {node_ids}")
        
        if timeout:
            logger.debug(f"Connection timeout set to {timeout} seconds")
            if len(node_ids) > 1:
                click.echo(click.style("Note: Timeout will be applied to all connections", fg='yellow'))
        
        # Create tasks for each node connection
        tasks = [connect_node(ctx, n, broker, timeout) for n in node_ids]
        
        # Run all connections in parallel
        logger.debug("Starting parallel connection tasks")
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        # Keep the event loop running if we have a timeout
        if timeout and any(results):
            click.echo(click.style("\nKeeping connection alive until timeout...", fg='yellow'))
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                click.echo("\nConnection terminated by user")
            finally:
                loop.close()
        else:
            loop.close()
            
        logger.debug("Event loop closed")
        
        # For single node, return appropriate exit code
        if len(node_ids) == 1:
            return 0 if results[0] else sys.exit(1)
            
    except Exception as e:
        logger.debug(f"Connection error: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        if len(node_id.split(',')) == 1:  # Only exit for single node
            sys.exit(1)

@connection.command('disconnect')
@click.option('--node-id', help='Specific node ID to disconnect')
@click.option('--all', is_flag=True, help='Disconnect all nodes')
@click.pass_context
@debug_log
def disconnect(ctx, node_id, all):
    """Disconnect from one or all nodes."""
    connection_manager = ctx.obj['CONNECTION_MANAGER']
    shared_manager = SharedConnectionManager(ctx.obj['CONFIG_DIR'])
    
    try:
        if all:
            logger.debug("Disconnecting all nodes")
            # Disconnect all nodes
            results = connection_manager.disconnect_all()
            state = shared_manager.get_all_connections()
            for node_id in list(state.keys()):
                shared_manager.unregister_connection(node_id)
                click.echo(click.style(f"✓ Disconnected from {node_id}", fg='green'))
            ctx.obj['MQTT'] = None
            ctx.obj['NODE_ID'] = None
        elif node_id:
            logger.debug(f"Disconnecting specific node: {node_id}")
            # Check if node is registered in shared state
            if shared_manager.is_connected(node_id):
                # Disconnect specific node
                if connection_manager.remove_connection(node_id):
                    shared_manager.unregister_connection(node_id)
                    logger.debug(f"Successfully disconnected from {node_id}")
                    click.echo(click.style(f"✓ Disconnected from {node_id}", fg='green'))
                    if ctx.obj.get('NODE_ID') == node_id:
                        ctx.obj['MQTT'] = None
                        ctx.obj['NODE_ID'] = None
                    return 0
                else:
                    # If local connection manager doesn't have it, just remove from shared state
                    shared_manager.unregister_connection(node_id)
                    click.echo(click.style(f"✓ Disconnected from {node_id}", fg='green'))
                    return 0
            else:
                logger.debug(f"No connection found for {node_id}")
                click.echo(click.style(f"✗ No connection found for {node_id}", fg='red'))
                if not all:
                    sys.exit(1)
        else:
            # Disconnect active node
            active_node = ctx.obj.get('NODE_ID')
            if not active_node:
                logger.debug("No active connection to disconnect")
                click.echo(click.style("ℹ No active connection to disconnect", fg='yellow'))
                return
                
            logger.debug(f"Disconnecting active node: {active_node}")
            if connection_manager.remove_connection(active_node):
                shared_manager.unregister_connection(active_node)
                logger.debug(f"Successfully disconnected from active node {active_node}")
                click.echo(click.style(f"✓ Disconnected from {active_node}", fg='green'))
                ctx.obj['MQTT'] = None
                ctx.obj['NODE_ID'] = None
                return 0
            else:
                logger.debug(f"Failed to disconnect from active node {active_node}")
                click.echo(click.style(f"✗ Failed to disconnect from {active_node}", fg='red'))
                sys.exit(1)
                
    except Exception as e:
        logger.debug(f"Disconnect error: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        if not all and node_id:  # Only exit for single node operations
            sys.exit(1)

@connection.command('list')
@click.option('--all', is_flag=True, help='Show all configured nodes, not just active connections')
@click.pass_context
@debug_log
def list_connections(ctx, all):
    """List active connections and configured nodes."""
    try:
        conn_manager = ctx.obj.get('CONNECTION_MANAGER')
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        
        logger.debug("Retrieving configured nodes")
        # Get all configured nodes
        configured_nodes = config_manager.list_nodes()
        logger.debug(f"Found {len(configured_nodes)} configured nodes")
        
        # Get active connections and verify their status
        active_connections = {}
        if conn_manager:
            logger.debug("Checking active connections")
            for node_id, client in conn_manager.connections.items():
                logger.debug(f"Verifying connection for {node_id}")
                is_connected = verify_connection(client)
                if not is_connected:
                    logger.debug(f"Connection lost for {node_id}, attempting reconnect")
                    # Try to reconnect if connection is lost
                    try:
                        client.reconnect()
                        is_connected = client.is_connected()
                        logger.debug(f"Reconnection {'successful' if is_connected else 'failed'}")
                    except Exception as e:
                        logger.debug(f"Reconnection failed: {str(e)}")
                        is_connected = False
                active_connections[node_id] = is_connected
        
        if not configured_nodes and not active_connections:
            logger.debug("No nodes found in configuration or active connections")
            click.echo(click.style("No nodes configured or connected", fg='yellow'))
            return 0

        logger.debug("Displaying node status")
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
                return 0
                
            for node_id, is_connected in active_connections.items():
                status = "✓" if is_connected else "✗"
                status_color = 'green' if is_connected else 'red'
                active = " (active)" if node_id == conn_manager.active_node else ""
                connection = "Connected" if is_connected else "Disconnected"
                click.echo(f"{click.style(status, fg=status_color):<10} {node_id:<40} {connection:<10}{active}")
        
        click.echo("-" * 60)
        return 0
        
    except Exception as e:
        logger.debug(f"Error listing connections: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@connection.command('switch')
@click.option('--node-id', required=True, help='Node ID to switch to')
@click.pass_context
@debug_log
def switch_node(ctx, node_id):
    """Switch active connection to a different node."""
    try:
        connection_manager = ctx.obj['CONNECTION_MANAGER']
        logger.debug(f"Attempting to switch to node: {node_id}")
        
        # Check if node is already connected
        mqtt_client = connection_manager.get_connection(node_id)
        if not mqtt_client:
            logger.debug(f"Node {node_id} not connected, attempting connection")
            # If not connected, try to connect
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if not loop.run_until_complete(connect_node(ctx, node_id)):
                logger.debug(f"Failed to connect to node {node_id}")
                sys.exit(1)
            loop.close()
            mqtt_client = connection_manager.get_connection(node_id)
        
        # Verify connection is active
        if verify_connection(mqtt_client):
            logger.debug(f"Successfully switched to node {node_id}")
            ctx.obj['NODE_ID'] = node_id
            ctx.obj['MQTT'] = mqtt_client
            click.echo(click.style(f"✓ Switched to {node_id}", fg='green'))
            return 0
        else:
            logger.debug(f"Connection verification failed for node {node_id}")
            click.echo(click.style(f"✗ Could not switch to {node_id}: Connection failed", fg='red'))
            sys.exit(1)
            
    except Exception as e:
        logger.debug(f"Error switching nodes: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1) 