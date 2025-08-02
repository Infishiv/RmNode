"""
Command management for MQTT CLI.
Handles command requests and responses between nodes and cloud.
"""
import click
import json
import asyncio
import sys
import uuid
import logging
import time
import tlv8
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List
from ..utils.exceptions import MQTTError, MQTTConnectionError
from ..utils.validators import validate_node_id
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations
from ..utils.debug_logger import debug_log, debug_step
from ..core.mqtt_client import get_active_mqtt_client

# Import the send command function
from .send_command_fn import publish_tlv8_payload

# Get logger for this module
logger = logging.getLogger(__name__)

# Valid status codes and commands for reference
VALID_STATUS = {
    0: "success",
    1: "failed",
    2: "invalid command", 
    3: "authorization failure",
    4: "not found"
}

VALID_COMMANDS = {
    0: "get all pending requests",
    16: "request file upload url",
    17: "get file download url",
    20: "confirm file upload success"
}

@click.group()
def node_command():
    """Manage command operations between nodes and cloud."""
    pass

@debug_step("Ensuring node connection")
async def ensure_node_connection(ctx, node_id: str) -> bool:
    """Ensure connection to a node is active, connect if needed."""
    try:
        mqtt_client = get_active_mqtt_client(ctx, auto_connect=True, node_id=node_id)
        if mqtt_client:
            ctx.obj['MQTT'] = mqtt_client
            return True
        return False
    except Exception as e:
        logger.debug(f"Connection error: {str(e)}")
        click.echo(click.style(f"✗ Connection error: {str(e)}", fg='red'), err=True)
        return False

@node_command.command('send-command')
@click.option('--node-id', required=True, help='Node ID to send command from')
@click.option('--request-id', required=True, help='Request ID that uniquely identifies the request (T:1, L:22)')
@click.option('--status', required=True, type=int, help='Status: 0=success, 1=failed, 2=invalid command, 3=authorization failure, 4=not found (T:3, L:1)')
@click.option('--command', required=True, type=int, help='Command: 0=get all pending requests, 16=request file upload url, 17=get file download url, 20=confirm file upload success (T:5, L:2)')
@click.option('--metadata', help='JSON object of command data (T:6, L:0-64KB)')
@click.pass_context
@debug_log
def send_command(ctx, node_id: str, request_id: str, status: int, command: int, metadata: str = None):
    """Send a command from node to cloud using TLV8 format.
    
    This command uses the centralized connection management like other CLI commands
    and the single_node_publisher logic for TLV8 conversion.
    
    Examples:
        # Basic command
        node-command send-command --node-id node123 --request-id "req123" --status 0 --command 16
        
        # Command with metadata
        node-command send-command --node-id node123 --request-id "req123" --status 0 --command 16 --metadata '{"file_id": "abc123", "size": 1024}'
    """
    try:
        # Validate node ID
        logger.debug(f"Validating node ID: {node_id}")
        validate_node_id(node_id)
        
        # Get broker and cert_path from context
        broker = ctx.obj.get('BROKER')
        cert_path = ctx.obj.get('CERT_FOLDER')
        
        if not broker:
            logger.debug("No broker found in context")
            click.echo(click.style("✗ No broker URL configured", fg='red'), err=True)
            sys.exit(1)
            
        if not cert_path:
            logger.debug("No certificate path found in context")
            click.echo(click.style("✗ No certificate path configured", fg='red'), err=True)
            sys.exit(1)
        
        logger.debug(f"Using broker: {broker}")
        logger.debug(f"Using cert path: {cert_path}")
        
        # Create payload with TLV8 format
        payload = {
            "1": request_id,           # Request ID (string)
            "3": status,               # Status (integer)
            "5": command               # Command (integer)
        }
        
        # Add metadata if provided
        if metadata:
            try:
                metadata_json = json.loads(metadata)
                payload["6"] = metadata_json  # Metadata (JSON object)
                logger.debug(f"Added metadata: {metadata_json}")
            except json.JSONDecodeError as e:
                logger.debug(f"Invalid metadata JSON: {str(e)}")
                click.echo(click.style(f"✗ Invalid metadata JSON: {str(e)}", fg='red'), err=True)
                sys.exit(1)
        
        logger.debug(f"Created payload: {payload}")
        
        # Display command details
        click.echo("=== Sending Command ===")
        click.echo(f"Node ID: {node_id}")
        click.echo(f"Request ID: {request_id}")
        click.echo(f"Status: {status} ({VALID_STATUS.get(status, 'unknown')})")
        click.echo(f"Command: {command} ({VALID_COMMANDS.get(command, 'unknown')})")
        if metadata:
            click.echo(f"Metadata: {metadata}")
        click.echo("=" * 30)
        
        # Send command using the imported function
        success = publish_tlv8_payload(
            node_id=node_id,
            broker=broker,
            cert_base_path=cert_path,
            payload=payload
        )
        
        if success:
            click.echo(click.style("✓ Command sent successfully!", fg='green'))
            click.echo(f"Request ID: {request_id}")
            click.echo(f"Status: {VALID_STATUS.get(status, 'unknown')}")
            click.echo(f"Command: {VALID_COMMANDS.get(command, 'unknown')}")
            return 0
        else:
            click.echo(click.style("✗ Failed to send command", fg='red'), err=True)
            sys.exit(1)
            
    except Exception as e:
        logger.debug(f"Error in send_command: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@debug_step("Processing received message")
def process_received_message(message) -> dict:
    """Process and format received MQTT message for display."""
    try:
        # Get binary data
        if hasattr(message, 'payload'):
            payload_bytes = message.payload
        else:
            payload_bytes = str(message).encode()
            
        # Try to decode as TLV8
        try:
            decoded = tlv8.decode(payload_bytes)
            if decoded:
                # Convert to readable format
                decoded_dict = {}
                for entry in decoded:
                    if entry.type_id == 1:  # Request ID
                        try:
                            decoded_dict[str(entry.type_id)] = entry.data.decode('utf-8')
                        except:
                            decoded_dict[str(entry.type_id)] = str(entry.data)
                    elif entry.type_id == 3:  # Status
                        try:
                            if isinstance(entry.data, bytes):
                                status = int.from_bytes(entry.data, 'little')
                            else:
                                status = int(entry.data)
                            decoded_dict[str(entry.type_id)] = status
                            decoded_dict['status_desc'] = VALID_STATUS.get(status, "unknown")
                        except:
                            decoded_dict[str(entry.type_id)] = entry.data
                    elif entry.type_id == 5:  # Command
                        try:
                            if isinstance(entry.data, bytes):
                                command = int.from_bytes(entry.data, 'little')
                            else:
                                command = int(entry.data)
                            decoded_dict[str(entry.type_id)] = command
                            decoded_dict['command_desc'] = VALID_COMMANDS.get(command, "unknown")
                        except:
                            decoded_dict[str(entry.type_id)] = entry.data
                    elif entry.type_id == 6:  # Metadata
                        try:
                            if isinstance(entry.data, bytes):
                                decoded_dict[str(entry.type_id)] = json.loads(entry.data.decode('utf-8'))
                            else:
                                decoded_dict[str(entry.type_id)] = json.loads(str(entry.data))
                        except:
                            decoded_dict[str(entry.type_id)] = entry.data
                    else:
                        try:
                            if isinstance(entry.data, bytes):
                                decoded_dict[str(entry.type_id)] = entry.data.decode('utf-8')
                            else:
                                decoded_dict[str(entry.type_id)] = str(entry.data)
                        except:
                            decoded_dict[str(entry.type_id)] = entry.data
                
                return {
                    'type': 'tlv',
                    'content': decoded_dict,
                    'raw': payload_bytes.hex()
                }
        except Exception as e:
            logger.debug(f"TLV8 decode failed: {str(e)}")
            
        # If TLV fails, try JSON
        try:
            payload_str = payload_bytes.decode('utf-8')
            payload_json = json.loads(payload_str)
            return {
                'type': 'json',
                'content': payload_json,
                'raw': payload_str
            }
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
            
        # Fall back to raw display
        return {
            'type': 'binary',
            'content': f"Binary data ({len(payload_bytes)} bytes): {payload_bytes.hex()}",
            'raw': payload_bytes.hex()
        }
            
    except Exception as e:
        logger.debug(f"Error processing message: {str(e)}")
        return {
            'type': 'error',
            'content': f"Error processing message: {str(e)}",
            'raw': str(message)
        }

@node_command.command('monitor')
@click.option('--node-id', required=True, help='Node ID to monitor for commands')
@click.option('--timeout', default=60, type=int, help='Monitoring timeout in seconds (default: 60)')
@click.pass_context
@debug_log
def monitor(ctx, node_id: str, timeout: int):
    """Monitor command requests sent from cloud to nodes.
    
    This command subscribes to node/<node_id>/to-node topic to monitor
    commands sent from the cloud infrastructure to the device.
    
    Messages are automatically processed and decoded from Binary TLV format.
    
    Examples:
        node-command monitor --node-id node123 --timeout 120
        node-command monitor --node-id node123  # Uses default 60s timeout
    """
    try:
        # Create event loop for async operations
        logger.debug("Creating event loop for async operations")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Ensure connection
        logger.debug(f"Ensuring connection to node {node_id}")
        if not loop.run_until_complete(ensure_node_connection(ctx, node_id)):
            click.echo(click.style("✗ Failed to connect", fg='red'), err=True)
            sys.exit(1)
            
        mqtt_client = ctx.obj.get('MQTT')
        if not mqtt_client:
            logger.debug("No active MQTT connection found")
            click.echo(click.style("✗ No MQTT client available", fg='red'), err=True)
            sys.exit(1)
            
        # Topic for monitoring commands from cloud to node
        topic = f"node/{node_id}/to-node"
        logger.debug(f"Subscribing to topic: {topic}")
        
        # Message counter for display
        message_count = 0
        
        def on_command_message(client, userdata, message):
            nonlocal message_count
            message_count += 1
            
            try:
                logger.debug(f"Received command message #{message_count}")
                click.echo(f"\n{'='*70}")
                click.echo(f"Command #{message_count} received from cloud to node {node_id}")
                click.echo(f"Topic: {message.topic}")
                click.echo(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo('='*70)
                
                # Process message
                processed = process_received_message(message)
                
                if processed['type'] == 'tlv':
                    click.echo("Format: Binary TLV")
                    click.echo("\nDecoded Content:")
                    click.echo(json.dumps(processed['content'], indent=2))
                    
                elif processed['type'] == 'json':
                    click.echo("Format: JSON")
                    click.echo("Payload:")
                    click.echo(json.dumps(processed['content'], indent=2))
                    
                elif processed['type'] == 'binary':
                    click.echo("Format: Binary")
                    click.echo(processed['content'])
                    
                else:
                    click.echo("Error processing payload:")
                    click.echo(processed['content'])
                    
                click.echo('-'*70)
                
            except Exception as e:
                logger.debug(f"Error processing command message: {str(e)}")
                click.echo(click.style(f"Error processing message: {str(e)}", fg='red'))
        
        # Subscribe to command topic
        if not mqtt_client.subscribe(topic, qos=1, callback=on_command_message):
            logger.debug(f"Failed to subscribe to topic {topic}")
            click.echo(click.style(f"✗ Failed to subscribe to {topic}", fg='red'), err=True)
            sys.exit(1)
            
        click.echo(f"Monitoring commands from cloud to node {node_id}...")
        click.echo(f"Topic: {topic}")
        click.echo(f"Timeout: {timeout} seconds")
        click.echo("Press Ctrl+C to stop...\n")
        logger.debug("Starting command monitoring loop")
        
        try:
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    logger.debug("Timeout reached")
                    click.echo(click.style(f"\nTimeout reached ({timeout}s). No more commands received.", fg='yellow'))
                    break
                    
                # Check connection health
                if not mqtt_client.ping():
                    logger.debug("Connection lost, attempting to reconnect")
                    click.echo(click.style(f"\nConnection lost, attempting to reconnect...", fg='yellow'))
                    if mqtt_client.reconnect():
                        mqtt_client.subscribe(topic, qos=1, callback=on_command_message)
                        click.echo(click.style("Reconnected successfully", fg='green'))
                    else:
                        click.echo(click.style("Failed to reconnect", fg='red'))
                        break
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.debug("Command monitoring stopped by user")
            click.echo("\nStopping command monitor...")
        finally:
            # Cleanup: Unsubscribe
            logger.debug("Cleaning up MQTT subscription")
            try:
                mqtt_client.unsubscribe(topic)
                logger.debug(f"Unsubscribed from {topic}")
            except:
                logger.debug("Error during unsubscribe")
                pass
            
            click.echo(f"\nCommand monitoring session ended.")
            if message_count > 0:
                click.echo(f"Total commands received: {message_count}")
            else:
                click.echo("No commands were received during this session.")
        
    except Exception as e:
        logger.debug(f"Error in monitor: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1) 