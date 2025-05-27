"""
OTA (Over-The-Air) update commands for MQTT CLI.
"""
import click
import json
import time
import os
from pathlib import Path
from ..utils.exceptions import MQTTOTAError
from ..utils.validators import validate_version, validate_timeout
from typing import Optional
from ..utils.validators import validate_node_id
from ..utils.exceptions import MQTTConnectionError
from ..commands.connection import connect_node
from ..mqtt_operations import MQTTOperations
from ..utils.config_manager import ConfigManager

@click.group()
def ota():
    """OTA update management commands."""
    pass

@ota.command('fetch')
@click.option('--node-id', required=True, help='Node ID to fetch OTA update for')
@click.option('--fw-version', required=True, help='Current firmware version')
@click.option('--network-id', help='Network ID for Thread-based OTA')
@click.pass_context
def fetch_ota(ctx, node_id: str, fw_version: str, network_id: Optional[str]):
    """Request OTA update for a node.
    
    Example: mqtt-cli ota fetch --node-id node123 --fw-version 1.0.0 --network-id net123
    """
    try:
        # Get the connection manager
        connection_manager = ctx.obj.get('CONNECTION_MANAGER')
        if not connection_manager:
            click.echo(click.style("✗ Connection manager not initialized", fg='red'), err=True)
            raise click.Abort()

        # Get or establish connection
        mqtt_client = connection_manager.get_connection(node_id)
        if not mqtt_client:
            # Get config manager
            config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
            cert_paths = config_manager.get_node_paths(node_id)
            if not cert_paths:
                click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
                raise click.Abort()
                
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
            
            # Connect and store the connection
            if mqtt_client.connect():
                connection_manager.add_connection(node_id, broker_url, cert_path, key_path, mqtt_client)
            else:
                click.echo(click.style("✗ Failed to connect to node", fg='red'), err=True)
                raise click.Abort()

        # Prepare payload
        payload = {
            "fw_version": fw_version
        }
        if network_id:
            payload["network_id"] = network_id
            
        # Publish to OTA fetch topic
        topic = f"node/{node_id}/otafetch"
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            click.echo(click.style("✓ OTA fetch request sent", fg='green'))
        else:
            click.echo(click.style("✗ Failed to send OTA fetch request", fg='red'), err=True)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@ota.command('status')
@click.option('--node-id', required=True, help='Node ID(s) to update status for. Can be single ID or comma-separated list')
@click.option('--status', 
              type=click.Choice(['in-progress', 'success', 'rejected', 'failed', 'delayed']), 
              required=True, 
              help='OTA update status')
@click.option('--job-id', required=True, help='OTA job ID')
@click.option('--network-id', help='Network ID')
@click.option('--info', help='Additional information about the OTA status')
@click.pass_context
def update_status(ctx, node_id: str, status: str, job_id: str, network_id: str, info: Optional[str]):
    """Update OTA status for one or more nodes.
    
    Examples:
        mqtt-cli ota status --node-id node123 --status in-progress --job-id job123 --info "25% complete"
        mqtt-cli ota status --node-id "node123,node456" --status in-progress --job-id job123
    """
    try:
        # Split node_id if it contains commas
        node_ids = [n.strip() for n in node_id.split(',')]
        
        # Process each node in parallel
        for node_id in node_ids:
            try:
                # Get the connection manager
                connection_manager = ctx.obj.get('CONNECTION_MANAGER')
                if not connection_manager:
                    click.echo(click.style("✗ Connection manager not initialized", fg='red'), err=True)
                    raise click.Abort()

                # Get or establish connection
                mqtt_client = connection_manager.get_connection(node_id)
                if not mqtt_client:
                    # Get config manager
                    config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
                    cert_paths = config_manager.get_node_paths(node_id)
                    if not cert_paths:
                        click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
                        continue
                        
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
                    
                    # Connect and store the connection
                    if mqtt_client.connect():
                        connection_manager.add_connection(node_id, broker_url, cert_path, key_path, mqtt_client)
                    else:
                        click.echo(click.style(f"✗ Failed to connect to node {node_id}", fg='red'), err=True)
                        continue
                
                # Prepare payload
                payload = {
                    "status": status,
                    "ota_job_id": job_id
                }
                if network_id:
                    payload["network_id"] = network_id
                if info:
                    payload["additional_info"] = info
                    
                # Publish to OTA status topic
                topic = f"node/{node_id}/otastatus"
                if mqtt_client.publish(topic, json.dumps(payload), qos=1):
                    click.echo(click.style(f"✓ OTA status updated for node {node_id}", fg='green'))
                else:
                    click.echo(click.style(f"✗ Failed to update OTA status for node {node_id}", fg='red'), err=True)
                    
            except Exception as e:
                click.echo(click.style(f"✗ Error for node {node_id}: {str(e)}", fg='red'), err=True)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@ota.command('request')
@click.option('--node-id', required=True, help='Node ID(s) to request OTA update for. Can be single ID or comma-separated list')
@click.option('--timeout', default=60, type=int, help='Timeout in seconds (default: 60)')
@click.pass_context
def request(ctx, node_id: str, timeout: int):
    """Listen for OTA URL responses from one or more nodes and update status.
    
    Examples:
        mqtt-cli ota request --node-id node123 --timeout 120
        mqtt-cli ota request --node-id "node123,node456" --timeout 120
    """
    try:
        validate_timeout(timeout)
        
        # Split node_id if it contains commas
        node_ids = [n.strip() for n in node_id.split(',')]
        
        # Track responses and MQTT clients for each node
        responses_received = {node_id: False for node_id in node_ids}
        mqtt_clients = {}
        
        def publish_status_update(node_id, job_id, status, network_id=None, info=None):
            """Helper function to publish status updates with improved retry logic"""
            status_map = {
                "1": {"status": "success", "info": "Update completed successfully"},
                "2": {"status": "failed", "info": "Update failed"},
                "3": {"status": "in-progress", "info": "Update in progress"},
                "4": {"status": "rejected", "info": "Update rejected"},
                "5": {"status": "delayed", "info": "Update delayed"}
            }
            
            # Get the status and info from the map
            if status in status_map:
                status_info = status_map[status]
                status = status_info["status"]
                info = status_info["info"]

            try:
                mqtt_client = mqtt_clients.get(node_id)
                if not mqtt_client:
                    click.echo(click.style(f"✗ No MQTT client found for node {node_id}", fg='red'), err=True)
                    return False

                # Prepare payload
                payload = {
                    "status": status,
                    "ota_job_id": job_id
                }
                if network_id:
                    payload["network_id"] = network_id
                if info:
                    payload["additional_info"] = info

                # Publish to OTA status topic with enhanced retry logic
                topic = f"node/{node_id}/otastatus"
                max_retries = 3
                retry_delay = 2  # seconds between retries

                for attempt in range(max_retries):
                    try:
                        # Check connection before publishing
                        if not mqtt_client.is_connected():
                            click.echo(click.style(f"\nReconnecting to node {node_id} (attempt {attempt + 1}/{max_retries})...", fg='yellow'))
                            if not mqtt_client.reconnect():
                                if attempt < max_retries - 1:
                                    time.sleep(retry_delay)
                                    continue
                                else:
                                    click.echo(click.style(f"✗ Failed to reconnect to node {node_id}", fg='red'), err=True)
                                    return False

                        # Try to publish
                        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
                            click.echo(click.style(f"\nStatus Update Details:"))
                            click.echo(click.style(f"Node ID: {node_id}"))
                            click.echo(click.style(f"OTA Job ID: {job_id}"))
                            click.echo(click.style(f"Status: {status}"))
                            return True
                        
                        if attempt < max_retries - 1:
                            click.echo(click.style(f"Retrying status update (attempt {attempt + 2}/{max_retries})...", fg='yellow'))
                            time.sleep(retry_delay)
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            click.echo(click.style(f"Error during publish (attempt {attempt + 1}): {str(e)}", fg='yellow'))
                            time.sleep(retry_delay)
                        else:
                            click.echo(click.style(f"✗ Error during publish: {str(e)}", fg='red'), err=True)
                            return False

                click.echo(click.style(f"✗ Failed to publish status update after {max_retries} attempts", fg='red'), err=True)
                return False
                
            except Exception as e:
                click.echo(click.style(f"✗ Error updating status: {str(e)}", fg='red'), err=True)
                return False

        def on_ota_response(client, userdata, message):
            try:
                topic_parts = message.topic.split('/')
                if len(topic_parts) >= 2:
                    current_node = topic_parts[1]
                    if current_node not in node_ids:
                        return
                        
                click.echo("\n" + "="*50)
                click.echo(f"Received OTA response from node {current_node}")
                click.echo("="*50)
                
                try:
                    response = json.loads(message.payload.decode())
                    click.echo(json.dumps(response, indent=2))
                    click.echo("-"*50)
                    
                    if not response.get('ota_job_id'):
                        click.echo(click.style("No OTA job ID in response", fg='yellow'))
                        return
                        
                    # Prompt for status update
                    while True:
                        click.echo("\nSelect OTA status to send:")
                        click.echo("1. success")
                        click.echo("2. failed")
                        click.echo("3. in-progress")
                        click.echo("4. rejected")
                        click.echo("5. delayed")
                        click.echo("0. Skip status update")
                        
                        try:
                            choice = input("\nEnter your choice (0-5): ").strip()
                            
                            if choice == "0":
                                click.echo("Skipping status update")
                                break
                                
                            if choice in ["1", "2", "3", "4", "5"]:
                                if publish_status_update(current_node, response['ota_job_id'], choice):
                                    responses_received[current_node] = True
                                    break
                            else:
                                click.echo(click.style("Invalid choice. Please select 0-5", fg='red'))
                                
                        except KeyboardInterrupt:
                            click.echo("\nStatus update cancelled")
                            break
                        except Exception as e:
                            click.echo(click.style(f"Error: {str(e)}", fg='red'))
                            break
                            
                except json.JSONDecodeError:
                    click.echo(click.style("Invalid JSON in response", fg='red'))
                    click.echo("Raw payload: " + message.payload.decode())
                    
            except Exception as e:
                click.echo(click.style(f"Error processing response: {str(e)}", fg='red'))
 
        # Process each node
        connection_manager = ctx.obj.get('CONNECTION_MANAGER')
        if not connection_manager:
            click.echo(click.style("✗ Connection manager not initialized", fg='red'), err=True)
            raise click.Abort()

        for node_id in node_ids:
            try:
                mqtt_client = connection_manager.get_connection(node_id)
                if not mqtt_client:
                    config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
                    cert_paths = config_manager.get_node_paths(node_id)
                    if not cert_paths:
                        click.echo(click.style(f"✗ Node {node_id} not found in configuration", fg='red'), err=True)
                        continue
                        
                    broker_url = config_manager.get_broker()
                    cert_path, key_path = cert_paths
                    
                    mqtt_client = MQTTOperations(
                        broker=broker_url,
                        node_id=node_id,
                        cert_path=cert_path,
                        key_path=key_path
                    )
                    
                    if mqtt_client.connect():
                        connection_manager.add_connection(node_id, broker_url, cert_path, key_path, mqtt_client)
                    else:
                        click.echo(click.style(f"✗ Failed to connect to node {node_id}", fg='red'), err=True)
                        continue

                # Store MQTT client reference
                mqtt_clients[node_id] = mqtt_client
 
                # Subscribe to response topic
                response_topic = f"node/{node_id}/otaurl"
                if not mqtt_client.subscribe(response_topic, qos=1, callback=on_ota_response):
                    click.echo(click.style(f"✗ Failed to subscribe to response topic for node {node_id}", fg='red'), err=True)
                    continue
                    
                click.echo(f"Listening for OTA updates on {response_topic}...")
                
            except Exception as e:
                click.echo(click.style(f"✗ Error for node {node_id}: {str(e)}", fg='red'), err=True)
 
        click.echo("\nMonitoring all nodes. Press Ctrl+C to stop...")
 
        try:
            # Keep the MQTT loop running
            start_time = time.time()
            while True:
                if all(responses_received.values()):
                    click.echo(click.style("\nAll nodes have responded and status updates completed",fg='green'))
                    break
                    
                if time.time() - start_time > timeout:
                    pending_nodes = [n for n, received in responses_received.items() if not received]
                    if pending_nodes:
                        click.echo(click.style(f"\nTimeout reached. No response from: {', '.join(pending_nodes)}", fg='yellow'))
                    break

                # Check connection health for each client
                for node_id, mqtt_client in mqtt_clients.items():
                    if not mqtt_client.ping():
                        click.echo(click.style(f"\nConnection lost for node {node_id}, attempting to reconnect...", fg='yellow'))
                        mqtt_client.reconnect()
                    
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            click.echo("\nStopping OTA listener...")
        finally:
            # Cleanup: Unsubscribe and disconnect clients
            for node_id, mqtt_client in mqtt_clients.items():
                try:
                    mqtt_client.unsubscribe(f"node/{node_id}/otaurl")
                except:
                    pass
        
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()