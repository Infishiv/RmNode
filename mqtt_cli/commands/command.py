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
from ..utils.exceptions import MQTTError, MQTTConnectionError
from ..utils.validators import validate_node_id
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations
from ..utils.debug_logger import debug_log, debug_step
from ..core.mqtt_client import get_active_mqtt_client

# Get logger for this module
logger = logging.getLogger(__name__)

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

@debug_step("Converting payload for transmission")
def convert_payload_for_send(payload: dict) -> bytes:
    """Convert payload to Binary TLV format before sending.
    
    This function converts JSON payload to Binary TLV (Tag, Length, Value) format
    as required by ESP RainMaker MQTT specification for from-node topic.
    
    TLV Format:
    - Tag: 1 byte (identifies the field type)
    - Length: 2 bytes (length of value in network byte order)
    - Value: variable length data
    """
    try:
        import struct
        
        # Convert JSON to TLV binary format
        if isinstance(payload, dict):
            json_payload = json.dumps(payload)
        else:
            json_payload = json.dumps(json.loads(str(payload)))
        
        # Create TLV structure
        # Tag 0x01 = JSON payload data
        tag = 0x01
        value_bytes = json_payload.encode('utf-8')
        length = len(value_bytes)
        
        # Pack as binary: Tag(1 byte) + Length(2 bytes, big-endian) + Value
        tlv_binary = struct.pack('>BH', tag, length) + value_bytes
        
        logger.debug(f"Converted to Binary TLV format: Tag=0x{tag:02x}, Length={length}, Value={json_payload}")
        return tlv_binary
        
    except (json.JSONDecodeError, TypeError, struct.error) as e:
        logger.debug(f"TLV conversion failed: {str(e)}")
        raise MQTTError(f"Invalid payload format for TLV conversion: {str(e)}")

@debug_step("Processing received message")
def process_received_message(message) -> dict:
    """Process and format received MQTT message for display.
    
    This function handles the conversion after receiving messages,
    parsing both Binary TLV format and JSON for user display.
    """
    try:
        import struct
        
        if hasattr(message, 'payload'):
            payload_bytes = message.payload
        else:
            payload_bytes = str(message).encode()
        
        # First try to parse as Binary TLV format
        try:
            if len(payload_bytes) >= 3:  # Minimum TLV size (1+2+0)
                # Unpack TLV header: Tag(1 byte) + Length(2 bytes, big-endian)
                tag, length = struct.unpack('>BH', payload_bytes[:3])
                
                if len(payload_bytes) >= 3 + length:
                    value_bytes = payload_bytes[3:3+length]
                    value_str = value_bytes.decode('utf-8')
                    
                    # Try to parse the value as JSON
                    try:
                        value_json = json.loads(value_str)
                        return {
                            'type': 'tlv_json',
                            'content': value_json,
                            'raw': payload_bytes.hex(),
                            'tlv_info': {
                                'tag': f"0x{tag:02x}",
                                'length': length,
                                'value': value_str
                            }
                        }
                    except json.JSONDecodeError:
                        return {
                            'type': 'tlv_raw',
                            'content': value_str,
                            'raw': payload_bytes.hex(),
                            'tlv_info': {
                                'tag': f"0x{tag:02x}",
                                'length': length,
                                'value': value_str
                            }
                        }
        except (struct.error, UnicodeDecodeError):
            pass  # Not TLV format, try other parsing methods
        
        # Try to parse as regular JSON string
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
        try:
            payload_str = payload_bytes.decode('utf-8')
            return {
                'type': 'raw',
                'content': payload_str,
                'raw': payload_str
            }
        except UnicodeDecodeError:
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

@node_command.command('send-command')
@click.option('--node-id', required=True, help='Node ID to send command from')
@click.option('--json-payload', required=True, type=click.Path(exists=True), help='Path to JSON file to send from node to cloud')
@click.pass_context
@debug_log
def send_command(ctx, node_id: str, json_payload: str):
    """Send a JSON file as a command from node to cloud.
    
    This command publishes the contents of a JSON file to node/<node_id>/from-node topic.
    No TLV or binary conversion is performed; the file is sent as plain JSON.
    
    Examples:
        node-command send-command --node-id node123 --json-payload ./payload.json
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

        # Read and validate JSON file
        try:
            logger.debug(f"Reading JSON file: {json_payload}")
            with open(json_payload, 'r') as f:
                payload = json.load(f)
        except Exception as e:
            logger.debug(f"Invalid JSON file: {str(e)}")
            click.echo(click.style(f"✗ Invalid JSON file: {str(e)}", fg='red'), err=True)
            sys.exit(1)
        
        # Publish to from-node topic as JSON
        topic = f"node/{node_id}/from-node"
        logger.debug(f"Publishing JSON to topic: {topic}")
        if mqtt_client.publish(topic, json.dumps(payload), qos=1):
            logger.debug("JSON command published successfully")
            click.echo(click.style(f"✓ Sent JSON command from node {node_id} to cloud", fg='green'))
            click.echo("\nCommand Details:")
            click.echo("-" * 60)
            click.echo(f"Topic: {topic}")
            click.echo(f"Node ID: {node_id}")
            click.echo(f"Format: JSON")
            click.echo("\nPayload:")
            click.echo(json.dumps(payload, indent=2))
            click.echo("-" * 60)
            return 0
        else:
            logger.debug("Failed to publish JSON command")
            raise MQTTError("Failed to send JSON command")
            
    except MQTTError as e:
        logger.debug(f"MQTT error in send_command: {str(e)}")
        click.echo(click.style(f"✗ Failed to send command: {str(e)}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        logger.debug(f"Error in send_command: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@node_command.command('monitor')
@click.option('--node-id', required=True, help='Node ID to monitor for commands')
@click.option('--timeout', default=60, type=int, help='Monitoring timeout in seconds (default: 60)')
@click.pass_context
@debug_log
def monitor(ctx, node_id: str, timeout: int):
    """Monitor command requests sent from cloud to nodes.
    
    This command subscribes to node/<node_id>/to-node topic to monitor
    commands sent from the cloud infrastructure to the device.
    
    Messages are automatically processed and converted from Binary TLV or JSON format for display.
    
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
            click.echo(click.style("✗ No active MQTT connection", fg='red'), err=True)
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
                
                # Process message using TLV/JSON conversion
                processed = process_received_message(message)
                
                if processed['type'] == 'tlv_json':
                    click.echo("Format: Binary TLV with JSON content")
                    click.echo(f"TLV Tag: {processed['tlv_info']['tag']}")
                    click.echo(f"TLV Length: {processed['tlv_info']['length']}")
                    click.echo("Payload (JSON):")
                    click.echo(json.dumps(processed['content'], indent=2))
                    
                    # Check if it's a device parameter format
                    if isinstance(processed['content'], dict):
                        for key, value in processed['content'].items():
                            if isinstance(value, dict):
                                click.echo(f"\nDevice: {key}")
                                for param, param_value in value.items():
                                    click.echo(f"  {param}: {param_value} ({type(param_value).__name__})")
                                    
                elif processed['type'] == 'tlv_raw':
                    click.echo("Format: Binary TLV with raw content")
                    click.echo(f"TLV Tag: {processed['tlv_info']['tag']}")
                    click.echo(f"TLV Length: {processed['tlv_info']['length']}")
                    click.echo("Payload (Raw):")
                    click.echo(processed['content'])
                    
                elif processed['type'] == 'json':
                    click.echo("Format: JSON")
                    click.echo("Payload (JSON):")
                    click.echo(json.dumps(processed['content'], indent=2))
                    
                elif processed['type'] == 'binary':
                    click.echo("Format: Binary")
                    click.echo(processed['content'])
                    
                elif processed['type'] == 'raw':
                    click.echo("Format: Raw text")
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
        click.echo(f"Format detection: Binary TLV and JSON supported")
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
                click.echo("All messages were processed with Binary TLV/JSON format detection.")
            else:
                click.echo("No commands were received during this session.")
        
    except Exception as e:
        logger.debug(f"Error in monitor: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        sys.exit(1) 