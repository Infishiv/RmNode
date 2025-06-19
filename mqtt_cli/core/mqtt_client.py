"""
MQTT client operations for MQTT CLI.
"""
import click
import sys
from ..mqtt_operations import MQTTOperations
from ..utils.cert_finder import get_cert_and_key_paths, get_cert_paths_from_direct_path

def connect_single_node(broker: str, node_id: str, base_path: str, direct_cert_path: str = None) -> tuple:
    """Helper function to connect a single node"""
    try:
        # If direct_cert_path is provided, use it with MAC address or node_details search
        if direct_cert_path:
            cert_path, key_path = get_cert_paths_from_direct_path(direct_cert_path, node_id)
        else:
            cert_path, key_path = get_cert_and_key_paths(base_path, node_id)
            
        mqtt_client = MQTTOperations(
            broker=broker,
            node_id=node_id,
            cert_path=cert_path,
            key_path=key_path
        )
        if mqtt_client.connect():
            return (node_id, mqtt_client, None)
        return (node_id, None, "Connection failed")
    except Exception as e:
        return (node_id, None, str(e))

def get_active_mqtt_client(ctx, auto_connect=False, node_id=None):
    """Helper to get active MQTT client with checks, supports auto connect"""
    connection_manager = ctx.obj['CONNECTION_MANAGER']
    config_manager = ctx.obj.get('CONFIG_MANAGER')
    
    if 'NODE_ID' not in ctx.obj and auto_connect and node_id:
        click.echo(click.style(f"Auto-connecting to node {node_id}...", fg='yellow'))
        broker = ctx.obj.get('BROKER')
        cert_path = ctx.obj.get('CERT_PATH')
        
        try:
            # Try direct certificate path first if provided
            if cert_path:
                cert_path, key_path = get_cert_paths_from_direct_path(cert_path, node_id)
                # Store certificate paths in config for future use
                if config_manager:
                    config_manager.add_node(node_id, cert_path, key_path)
            # Otherwise try stored configuration
            elif config_manager:
                cert_paths = config_manager.get_node_paths(node_id)
                if cert_paths:
                    cert_path, key_path = cert_paths
                else:
                    # If not in config, try default location using node_details structure
                    base_path = ctx.obj['CERT_FOLDER']
                    cert_path, key_path = get_cert_and_key_paths(base_path, node_id)
                    # Store certificate paths in config for future use
                    config_manager.add_node(node_id, cert_path, key_path)
            else:
                raise FileNotFoundError(f"No certificate configuration found for node {node_id}")
                
            # Create MQTT client
            mqtt_client = MQTTOperations(
                broker=broker,
                node_id=node_id,
                cert_path=cert_path,
                key_path=key_path
            )
            
            if mqtt_client.connect():
                connection_manager.add_connection(node_id, broker, cert_path, key_path, mqtt_client)
                ctx.obj['NODE_ID'] = node_id
                ctx.obj['MQTT'] = mqtt_client
                return mqtt_client
            else:
                click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
                sys.exit(1)
                
        except Exception as e:
            click.echo(click.style(f"✗ Auto-connect failed: {str(e)}", fg='red'), err=True)
            sys.exit(1)

    if 'NODE_ID' not in ctx.obj:
        click.echo(click.style("✗ No active node connection", fg='red'), err=True)
        sys.exit(1)

    node_id = ctx.obj['NODE_ID']
    mqtt_client = connection_manager.get_connection(node_id)
    
    if not mqtt_client:
        click.echo(click.style(f"✗ No connection found for active node {node_id}", fg='red'), err=True)
        sys.exit(1)

    return mqtt_client 