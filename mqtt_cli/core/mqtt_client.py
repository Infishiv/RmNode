"""
MQTT client operations for MQTT CLI.
"""
import click
import sys
from ..mqtt_operations import MQTTOperations
from ..utils.cert_finder import get_cert_and_key_paths

def connect_single_node(broker: str, node_id: str, base_path: str) -> tuple:
    """Helper function to connect a single node"""
    try:
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
    
    if 'NODE_ID' not in ctx.obj and auto_connect and node_id:
        click.echo(click.style(f"Auto-connecting to node {node_id}...", fg='yellow'))
        broker = ctx.obj['BROKER']
        base_path = ctx.obj['CERT_FOLDER']
        result = connect_single_node(broker, node_id, base_path)
        _, mqtt_client, error = result
        
        if error:
            click.echo(click.style(f"✗ Auto-connect failed: {error}", fg='red'), err=True)
            sys.exit(1)
        
        connection_manager.add_connection(node_id, mqtt_client)
        ctx.obj['NODE_ID'] = node_id
        ctx.obj['MQTT'] = mqtt_client

    if 'NODE_ID' not in ctx.obj:
        click.echo(click.style("✗ No active node connection", fg='red'), err=True)
        sys.exit(1)

    node_id = ctx.obj['NODE_ID']
    mqtt_client = connection_manager.get_connection(node_id)
    
    if not mqtt_client:
        click.echo(click.style(f"✗ No connection found for active node {node_id}", fg='red'), err=True)
        sys.exit(1)

    return mqtt_client 