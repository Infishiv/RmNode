"""
Node configuration and parameters management.

This module provides commands for managing node configuration and parameters.
"""
import click
import json
import sys
import time
import asyncio
import uuid
import os
import logging
import shutil
from pathlib import Path
from ..utils.exceptions import MQTTError
from ..utils.validators import validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations
from ..utils.debug_logger import debug_log, debug_step

# Get logger for this module
logger = logging.getLogger(__name__)

# Get the path to the node_configs directory
CONFIGS_DIR = Path(__file__).parent / 'node_configs'

@debug_step("Creating node configuration")
def create_node_specific_config(node_id: str, name: str = None) -> dict:
    """Create a node-specific configuration based on the default template.
    
    Args:
        node_id: The ID of the node
        name: Optional name for the node (defaults to "ESP RainMaker Node-{node_id}")
        
    Returns:
        dict: Node-specific configuration
    """
    default_config_path = CONFIGS_DIR / "default_config.json"
    if not default_config_path.exists():
        logger.debug("Default configuration template not found")
        raise MQTTError("Default configuration template not found")
        
    try:
        with open(default_config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.debug(f"Invalid JSON in default config: {str(e)}")
        raise MQTTError("Invalid default configuration template")
        
    # Update node-specific fields
    config['node_id'] = node_id
    if name:
        config['info']['name'] = name
    else:
        config['info']['name'] = f"ESP RainMaker Node-{node_id}"
    
    logger.debug(f"Created configuration for node {node_id}")
    return config

@debug_step("Saving configuration")
def save_node_config(node_id: str, config: dict) -> None:
    """Save node-specific configuration to file.
    
    Args:
        node_id: The ID of the node
        config: Configuration dictionary to save
    """
    config_file = CONFIGS_DIR / f"{node_id}_config.json"
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        logger.debug(f"Configuration saved to {config_file}")
    except Exception as e:
        logger.debug(f"Failed to save configuration: {str(e)}")
        raise MQTTError(f"Failed to save configuration: {str(e)}")

@debug_step("Retrieving configuration")
def get_stored_config(node_id: str, create_if_missing: bool = True) -> dict:
    """Get stored configuration for a node.
    
    Args:
        node_id: The ID of the node
        create_if_missing: Whether to create a node-specific config if none exists
        
    Returns:
        dict: Node configuration
    """
    config_file = CONFIGS_DIR / f"{node_id}_config.json"
    
    # If node-specific config doesn't exist and create_if_missing is True
    if not config_file.exists() and create_if_missing:
        logger.debug(f"Creating new configuration for node {node_id}")
        config = create_node_specific_config(node_id)
        save_node_config(node_id, config)
        return config
        
    # If node-specific config exists, use it
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.debug(f"Loaded configuration for node {node_id}")
            return config
        except json.JSONDecodeError as e:
            logger.debug(f"Invalid JSON in config file: {str(e)}")
            raise MQTTError(f"Invalid configuration file for node {node_id}")
            
    # If we get here, no config exists and we're not creating one
    logger.debug(f"No configuration found for node {node_id}")
    raise MQTTError(f"No configuration found for node {node_id}")

@debug_step("Retrieving parameters")
def get_stored_params(node_id: str) -> dict:
    """Get stored parameters for a node."""
    params_file = CONFIGS_DIR / f"{node_id}_params.json"
    
    if not params_file.exists():
        params_file = CONFIGS_DIR / "default_params.json"
        if not params_file.exists():
            logger.debug("No parameters found")
            raise MQTTError("No default parameters found")
            
    try:
        with open(params_file, 'r') as f:
            params = json.load(f)
        logger.debug(f"Loaded parameters from {params_file}")
        return params
    except json.JSONDecodeError as e:
        logger.debug(f"Invalid JSON in parameters file: {str(e)}")
        raise MQTTError("Invalid parameters file")

@debug_log
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

@click.group()
def node():
    """Node configuration and parameters management commands."""
    pass

@node.command('config')
@click.option('--node-id', required=True, help='Node ID to configure')
@click.option('--config-file', type=click.Path(exists=True), help='JSON file containing node configuration')
@click.option('--use-stored', is_flag=True, help='Use stored configuration for the node')
@click.option('--name', help='Custom name for the node (only used with --use-stored)')
@click.pass_context
@debug_log
def set_config(ctx, node_id, config_file, use_stored, name):
    """Set node configuration.
    
    Example: mqtt-cli node config --node-id node123 --config-file config.json
    Or use stored config: mqtt-cli node config --node-id node123 --use-stored
    Or with custom name: mqtt-cli node config --node-id node123 --use-stored --name "Living Room Node"
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

        # Get configuration
        if use_stored:
            try:
                logger.debug("Using stored configuration")
                # If name is provided, create a new config with that name
                if name:
                    logger.debug(f"Creating new configuration with custom name: {name}")
                    config = create_node_specific_config(node_id, name)
                    save_node_config(node_id, config)
                else:
                    logger.debug("Loading existing stored configuration")
                    config = get_stored_config(node_id)
                click.echo(click.style("✓ Using stored configuration", fg='green'))
            except MQTTError as e:
                logger.debug(f"Error with stored configuration: {str(e)}")
                click.echo(click.style(f"✗ {str(e)}", fg='red'), err=True)
                sys.exit(1)
        else:
            if not config_file:
                logger.debug("No configuration source specified")
                click.echo(click.style("✗ Either --config-file or --use-stored must be specified", fg='red'), err=True)
                sys.exit(1)
                
            # Read and validate config file
            logger.debug(f"Loading configuration from file: {config_file}")
            with open(config_file, 'r') as f:
                config = json.load(f)

        # Basic validation
        logger.debug("Validating configuration")
        required_fields = ['node_id', 'info', 'devices']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            logger.debug(f"Missing required fields in configuration: {missing_fields}")
            click.echo(click.style(f"✗ Missing required fields: {', '.join(missing_fields)}", fg='red'), err=True)
            sys.exit(1)

        # Validate node_id matches
        if config['node_id'] != node_id:
            logger.debug(f"Configuration node_id mismatch: {config['node_id']} != {node_id}")
            click.echo(click.style(f"✗ Config file node_id '{config['node_id']}' does not match specified node_id '{node_id}'", fg='red'), err=True)
            sys.exit(1)

        # Save the configuration locally if it came from a custom config file
        if not use_stored:
            logger.debug("Saving custom configuration locally")
            save_node_config(node_id, config)
            click.echo(click.style("✓ Saved configuration locally", fg='green'))

        # Simple topic structure
        topic = f"node/{node_id}/config"
        
        # Publish config
        if mqtt_client.publish(topic, json.dumps(config), qos=1):
            click.echo(click.style(f"✓ Published configuration for node {node_id}", fg='green'))
            click.echo("\nConfiguration:")
            click.echo(json.dumps(config, indent=2))
            return 0
        else:
            click.echo(click.style("✗ Failed to publish configuration", fg='red'), err=True)
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        click.echo(click.style(f"✗ Invalid JSON in config file: {str(e)}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@node.command('params')
@click.option('--node-id', required=True, help='Node ID to set parameters for')
@click.option('--params-file', type=click.Path(exists=True), help='JSON file containing parameters')
@click.option('--device-name', required=True, help='Name of the device to set parameters for')
@click.option('--use-stored', is_flag=True, help='Use stored parameters for the node')
@click.pass_context
@debug_log
def set_params(ctx, node_id: str, params_file: str, device_name: str, use_stored: bool):
    """Set parameters for a specific device on a node.
    
    Example: mqtt-cli node params --node-id node123 --device-name switch1 --params-file params.json
    Or use stored: mqtt-cli node params --node-id node123 --device-name switch1 --use-stored
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
            
        # Get parameters
        if use_stored:
            try:
                logger.debug("Using stored parameters")
                params = get_stored_params(node_id)
                click.echo(click.style("✓ Using stored parameters", fg='green'))
            except MQTTError as e:
                logger.debug(f"Error with stored parameters: {str(e)}")
                click.echo(click.style(f"✗ {str(e)}", fg='red'), err=True)
                sys.exit(1)
        else:
            if not params_file:
                logger.debug("No parameters source specified")
                click.echo(click.style("✗ Either --params-file or --use-stored must be specified", fg='red'), err=True)
                sys.exit(1)
                
            # Read and validate params file
            logger.debug(f"Loading parameters from file: {params_file}")
            with open(params_file, 'r') as f:
                params = json.load(f)
                
        # Basic validation
        logger.debug("Validating parameters")
        if not isinstance(params, dict):
            logger.debug("Parameters must be a dictionary")
            click.echo(click.style("✗ Parameters must be a dictionary", fg='red'), err=True)
            sys.exit(1)
            
        # Validate device exists in params
        if device_name not in params:
            click.echo(click.style(f"✗ Device '{device_name}' not found in parameters", fg='red'), err=True)
            sys.exit(1)

        # Get device parameters
        device_params = params[device_name]

        # Simple topic structure for device parameters
        topic = f"node/{node_id}/params"

        # Prepare payload with device name
        payload = {
            device_name: device_params
        }

        # Publish parameters
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style(f"✓ Set parameters for device {device_name} on node {node_id}", fg='green'))
            click.echo("\nParameters:")
            click.echo(json.dumps(payload, indent=2))
            return 0
        else:
            click.echo(click.style("✗ Failed to publish parameters", fg='red'), err=True)
            sys.exit(1)
        
    except Exception as e:
        logger.debug(f"Error in set_params: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@node.command('monitor')
@click.option('--node-id', required=True, help='Node ID to monitor')
@click.option('--timeout', default=60, type=int, help='Monitoring timeout in seconds')
@click.pass_context
@debug_log
def monitor_node(ctx, node_id: str, timeout: int):
    """Monitor node status and parameters.
    
    Example: mqtt-cli node monitor --node-id node123 --timeout 120
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
            
        click.echo(f"Monitoring node {node_id} for {timeout} seconds...")
        click.echo("Press Ctrl+C to stop...")
        
        def on_message(client, userdata, message):
            try:
                logger.debug(f"Received message on topic: {message.topic}")
                payload = message.payload.decode()
                try:
                    # Try to parse and pretty print JSON
                    data = json.loads(payload)
                    payload = json.dumps(data, indent=2)
                    logger.debug("Message payload is valid JSON")
                except json.JSONDecodeError:
                    logger.debug("Message payload is not JSON format")
                    pass
                    
                click.echo(f"\nTopic: {message.topic}")
                click.echo(f"Message: {payload}")
            except Exception as e:
                logger.debug(f"Error processing message: {str(e)}")
                click.echo(f"Error processing message: {str(e)}")
                
        # Subscribe to all node-related topics
        topic = f"{node_id}/#"
        logger.debug(f"Subscribing to topic: {topic}")
        mqtt_client.subscribe(topic=topic, callback=on_message)
        
        # Keep the main thread alive for the specified timeout
        try:
            time.sleep(timeout)
        except KeyboardInterrupt:
            logger.debug("Monitoring stopped by user (Ctrl+C)")
            click.echo("\nMonitoring stopped")
            return 0
            
    except Exception as e:
        logger.debug(f"Error in monitor_node: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@node.group()
def presence():
    """Node presence management commands."""
    pass

@presence.command('connected')
@click.option('--node-id', required=True, help='Node ID to mark as connected')
@click.option('--client-id', default='rainmaker-node', help='ID of the connected device')
@click.option('--client-initiated', is_flag=True, default=True, help='Whether the disconnect was initiated by the client')
@click.option('--principal-id', help='Principal identifier (certificate ID) of the device')
@click.option('--session-id', help='Session identifier for the connection')
@click.option('--ip-address', default='192.168.1.100', help='IP address of the connected device')
@click.option('--version', type=int, default=0, help='Version number of the event')
@click.pass_context
@debug_log
def node_connected(ctx, node_id, client_id, client_initiated, principal_id, session_id, ip_address, version):
    """Mark a node as connected.
    
    Example: mqtt-cli node presence connected --node-id node123
    """
    try:
        logger.debug(f"Marking node {node_id} as connected")
        logger.debug(f"Connection details: client_id={client_id}, ip={ip_address}, session={session_id}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        logger.debug(f"Ensuring connection to node {node_id}")
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            sys.exit(1)
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            return

        # Get certificate ID from cert file if not provided
        if not principal_id:
            try:
                config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
                cert_paths = config_manager.get_node_paths(node_id)
                if cert_paths:
                    cert_path = cert_paths[0]
                    # Extract certificate ID from the path
                    principal_id = cert_path.split('/')[-2].split('-')[-1]
            except Exception:
                principal_id = node_id

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # Prepare payload according to AWS IoT Core presence event schema
        payload = {
            "clientId": client_id,
            "clientInitiatedDisconnect": client_initiated,
            "eventType": "connected",
            "principalIdentifier": principal_id,
            "sessionIdentifier": session_id,
            "timestamp": int(time.time() * 1000),
            "versionNumber": version,
            "ipAddress": ip_address
        }

        # AWS IoT Core presence event topic
        topic = f"$aws/events/presence/connected/{node_id}"
        
        # Publish event
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style(f"✓ Published connected event for node {node_id}", fg='green'))
            click.echo("\nPayload:")
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(click.style("✗ Failed to publish connected event", fg='red'), err=True)
        
    except Exception as e:
        logger.debug(f"Error in node_connected: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@presence.command('disconnected')
@click.option('--node-id', required=True, help='Node ID to mark as disconnected')
@click.option('--client-id', default='rainmaker-node', help='ID of the disconnected device')
@click.option('--client-initiated', is_flag=True, default=True, help='Whether the disconnect was initiated by the client')
@click.option('--principal-id', help='Principal identifier (certificate ID) of the device')
@click.option('--session-id', help='Session identifier for the connection')
@click.option('--disconnect-reason', default='CLIENT_INITIATED_DISCONNECT', help='Reason for disconnection')
@click.option('--version', type=int, default=0, help='Version number of the event')
@click.pass_context
@debug_log
def node_disconnected(ctx, node_id, client_id, client_initiated, principal_id, session_id, disconnect_reason, version):
    """Mark a node as disconnected.
    
    Example: mqtt-cli node presence disconnected --node-id node123
    """
    try:
        logger.debug(f"Marking node {node_id} as disconnected")
        logger.debug(f"Disconnection details: client_id={client_id}, reason={disconnect_reason}, session={session_id}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        logger.debug(f"Ensuring connection to node {node_id}")
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            sys.exit(1)
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
            return

        # Get certificate ID from cert file if not provided
        if not principal_id:
            try:
                config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
                cert_paths = config_manager.get_node_paths(node_id)
                if cert_paths:
                    cert_path = cert_paths[0]
                    # Extract certificate ID from the path
                    principal_id = cert_path.split('/')[-2].split('-')[-1]
            except Exception:
                principal_id = node_id

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # Prepare payload according to AWS IoT Core presence event schema
        payload = {
            "clientId": client_id,
            "clientInitiatedDisconnect": client_initiated,
            "eventType": "disconnected",
            "principalIdentifier": principal_id,
            "sessionIdentifier": session_id,
            "timestamp": int(time.time() * 1000),
            "versionNumber": version,
            "disconnectReason": disconnect_reason
        }

        # AWS IoT Core presence event topic
        topic = f"$aws/events/presence/disconnected/{node_id}"
        
        # Publish event
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style(f"✓ Published disconnected event for node {node_id}", fg='green'))
            click.echo("\nPayload:")
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(click.style("✗ Failed to publish disconnected event", fg='red'), err=True)
        
    except Exception as e:
        logger.debug(f"Error in node_disconnected: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@node.command('init-params')
@click.option('--node-id', required=True, help='Node ID to initialize parameters for')
@click.option('--params-file', type=click.Path(exists=True), help='JSON file containing initial parameters')
@click.option('--use-stored', is_flag=True, help='Use stored parameters for the node')
@click.pass_context
@debug_log
def init_params(ctx, node_id: str, params_file: str, use_stored: bool):
    """Initialize node parameters.
    
    Example: mqtt-cli node init-params --node-id node123 --params-file init_params.json
    Or use stored: mqtt-cli node init-params --node-id node123 --use-stored
    """
    try:
        logger.debug(f"Initializing parameters for node {node_id}")
        
        # Create event loop for async operations
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
            
        # Get parameters
        if use_stored:
            try:
                logger.debug("Using stored parameters")
                params = get_stored_params(node_id)
                click.echo(click.style("✓ Using stored parameters", fg='green'))
            except MQTTError as e:
                logger.debug(f"Error with stored parameters: {str(e)}")
                click.echo(click.style(f"✗ {str(e)}", fg='red'), err=True)
                sys.exit(1)
        else:
            if not params_file:
                logger.debug("No parameters source specified")
                click.echo(click.style("✗ Either --params-file or --use-stored must be specified", fg='red'), err=True)
                sys.exit(1)
                
            # Read and validate params file
            logger.debug(f"Loading parameters from file: {params_file}")
            with open(params_file, 'r') as f:
                params = json.load(f)
                
        # Topic for initial parameters
        topic = f"node/{node_id}/params/init"
        logger.debug(f"Publishing to topic: {topic}")
        
        # Publish parameters
        if mqtt_client.publish(topic, json.dumps(params), qos=1):
            logger.debug("Parameters published successfully")
            click.echo(click.style(f"✓ Initialized parameters for node {node_id}", fg='green'))
            click.echo("\nParameters:")
            click.echo(json.dumps(params, indent=2))
            return 0
        else:
            logger.debug("Failed to publish parameters")
            click.echo(click.style("✗ Failed to initialize parameters", fg='red'), err=True)
            sys.exit(1)
            
    except Exception as e:
        logger.debug(f"Error in init_params: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@node.command('group-params')
@click.option('--node-ids', required=True, help='Comma-separated list of node IDs')
@click.option('--params-file', type=click.Path(exists=True), help='JSON file containing parameters')
@click.option('--use-stored', is_flag=True, help='Use stored parameters')
@click.pass_context
@debug_log
def group_params(ctx, node_ids: str, params_file: str, use_stored: bool):
    """Set parameters for a group of nodes.
    
    Example: mqtt-cli node group-params --node-ids "node1,node2,node3" --params-file group_params.json
    Or use stored: mqtt-cli node group-params --node-ids "node1,node2,node3" --use-stored
    """
    try:
        # Split node IDs
        node_list = [n.strip() for n in node_ids.split(',')]
        logger.debug(f"Processing group parameters for nodes: {node_list}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get parameters
        if use_stored:
            try:
                logger.debug("Using stored parameters")
                params = get_stored_params(node_list[0])  # Use first node's params as template
                click.echo(click.style("✓ Using stored parameters", fg='green'))
            except MQTTError as e:
                logger.debug(f"Error with stored parameters: {str(e)}")
                click.echo(click.style(f"✗ {str(e)}", fg='red'), err=True)
                sys.exit(1)
        else:
            if not params_file:
                logger.debug("No parameters source specified")
                click.echo(click.style("✗ Either --params-file or --use-stored must be specified", fg='red'), err=True)
                sys.exit(1)
                
            # Read and validate params file
            logger.debug(f"Loading parameters from file: {params_file}")
            with open(params_file, 'r') as f:
                params = json.load(f)
                
        # Process each node
        for node_id in node_list:
            logger.debug(f"Processing node: {node_id}")
            try:
                # Ensure connection to this node
                logger.debug(f"Ensuring connection to node {node_id}")
                if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
                    logger.debug(f"Skipping node {node_id} due to connection failure")
                    continue
                    
                mqtt_client = ctx.obj.get('MQTT')
                if not mqtt_client:
                    logger.debug(f"No active MQTT connection for node {node_id}")
                    click.echo(click.style(f"✗ No active MQTT connection for node {node_id}", fg='red'), err=True)
                    continue
                    
                # Topic for group parameters
                topic = f"node/{node_id}/params/group"
                logger.debug(f"Publishing to topic: {topic}")
                
                # Publish parameters
                if mqtt_client.publish(topic, json.dumps(params), qos=1):
                    logger.debug(f"Parameters published successfully for node {node_id}")
                    click.echo(click.style(f"✓ Updated parameters for node {node_id}", fg='green'))
                else:
                    logger.debug(f"Failed to publish parameters for node {node_id}")
                    click.echo(click.style(f"✗ Failed to update parameters for node {node_id}", fg='red'), err=True)
                    
            except Exception as e:
                logger.debug(f"Error processing node {node_id}: {str(e)}")
                click.echo(click.style(f"✗ Error for node {node_id}: {str(e)}", fg='red'), err=True)
                continue
                
    except Exception as e:
        logger.debug(f"Error in group_params: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1) 