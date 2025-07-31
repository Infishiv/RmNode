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
from dataclasses import dataclass
from typing import Any, Dict, List
from ..utils.exceptions import MQTTError, MQTTConnectionError
from ..utils.validators import validate_node_id
from ..commands.connection import connect_node
from ..utils.config_manager import ConfigManager
from ..mqtt_operations import MQTTOperations
from ..utils.debug_logger import debug_log, debug_step
from ..core.mqtt_client import get_active_mqtt_client

# Get logger for this module
logger = logging.getLogger(__name__)

@dataclass
class TLVEntry:
    type_id: int
    data: Any

class TLVHandler:
    """Handles TLV encoding/decoding according to ESP RainMaker specification."""
    
    # Define TLV structure for node/<node_id>/from-node messages
    TLV_STRUCTURE = {
        1: tlv8.DataType.STRING,    # Request ID (22 bytes)
        3: tlv8.DataType.INTEGER,   # Status (1 byte: 0-4)
        5: tlv8.DataType.INTEGER,   # Command (2 bytes)
        6: tlv8.DataType.STRING     # Data Payload (JSON, 0-64KB)
    }

    # Valid status codes
    VALID_STATUS = {
        0: "success",
        1: "failed",
        2: "invalid command",
        3: "authorization failure",
        4: "not found"
    }

    # Valid commands
    VALID_COMMANDS = {
        0: "get all pending requests",
        1: "request file upload url",
        2: "get file download url",
        3: "confirm file upload success"
    }

    @staticmethod
    def json_to_tlv8(json_data: Dict) -> bytearray:
        """Convert JSON data to TLV8 format using the correct structure from temp folder.
        
        Args:
            json_data: Dictionary with numeric keys matching TLV types
            
        Returns:
            bytearray: Binary TLV formatted data
        """
        try:
            entries = []
            
            for key, value in json_data.items():
                # Convert key to integer (TLV8 type_id)
                type_id = int(key)
                
                # Convert value to appropriate bytes based on type
                if isinstance(value, str):
                    value_bytes = value.encode('utf-8')
                elif isinstance(value, int):
                    # Convert integer to bytes using little endian (match temp folder)
                    value_bytes = value.to_bytes(2, "little")
                elif isinstance(value, bool):
                    value_bytes = b'\x01' if value else b'\x00'
                elif isinstance(value, dict):
                    # For Type 6 (data), convert dict to JSON string
                    value_bytes = json.dumps(value).encode('utf-8')
                else:
                    raise ValueError(f"Unsupported type for value: {type(value)}")
                
                entries.append(tlv8.Entry(type_id, value_bytes))
            
            # Convert to bytearray
            return bytearray(tlv8.encode(entries))
            
        except Exception as e:
            raise ValueError(f"Invalid payload format: {str(e)}")

    @staticmethod
    def encode_command(payload: Dict) -> bytearray:
        """Convert payload to TLV format according to ESP RainMaker specification.
        
        Args:
            payload: Dictionary with numeric keys matching TLV types
            
        Returns:
            bytearray: Binary TLV formatted data
        """
        return TLVHandler.json_to_tlv8(payload)

    @staticmethod
    def decode_message(message: bytes) -> Dict[str, Any]:
        """Decode TLV message to dictionary.
        
        Args:
            message: Binary TLV data
            
        Returns:
            dict: Decoded message with type IDs as string keys
        """
        try:
            result = tlv8.decode(message, TLVHandler.TLV_STRUCTURE)
            decoded = {}
            
            for entry in result:
                if entry.type_id == 1:  # Request ID
                    try:
                        decoded[str(entry.type_id)] = entry.data.decode('utf-8')
                    except AttributeError:
                        decoded[str(entry.type_id)] = str(entry.data)
                elif entry.type_id == 3:  # Status
                    try:
                        if isinstance(entry.data, bytes):
                            status = int.from_bytes(entry.data, 'little')
                        else:
                            status = int(entry.data)
                        decoded[str(entry.type_id)] = status
                        decoded['status_desc'] = TLVHandler.VALID_STATUS.get(status, "unknown")
                    except (TypeError, AttributeError, ValueError):
                        decoded[str(entry.type_id)] = entry.data
                elif entry.type_id == 5:  # Command
                    try:
                        if isinstance(entry.data, bytes):
                            command = int.from_bytes(entry.data, 'little')
                        else:
                            command = int(entry.data)
                        decoded[str(entry.type_id)] = command
                        decoded['command_desc'] = TLVHandler.VALID_COMMANDS.get(command, "unknown")
                    except (TypeError, AttributeError, ValueError):
                        decoded[str(entry.type_id)] = entry.data
                elif entry.type_id == 6:  # JSON data
                    try:
                        if isinstance(entry.data, bytes):
                            decoded[str(entry.type_id)] = json.loads(entry.data.decode('utf-8'))
                        else:
                            decoded[str(entry.type_id)] = json.loads(str(entry.data))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        decoded[str(entry.type_id)] = entry.data
                else:
                    # For other types, try to decode as string first
                    try:
                        if isinstance(entry.data, bytes):
                            decoded[str(entry.type_id)] = entry.data.decode('utf-8')
                        else:
                            decoded[str(entry.type_id)] = str(entry.data)
                    except UnicodeDecodeError:
                        decoded[str(entry.type_id)] = entry.data
                        
            return decoded
        except Exception as e:
            logger.debug(f"TLV decode failed: {str(e)}")
            # Return raw data if TLV decode fails
            return {
                'raw_data': message.hex(),
                'error': str(e)
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
@click.option('--status', required=True, type=click.Choice(['0', '1', '2', '3', '4']), help='Status: 0=success, 1=failed, 2=invalid command, 3=authorization failure, 4=not found (T:3, L:1)')
@click.option('--command', required=True, type=click.Choice(['0', '1', '2', '3']), help='Command: 0=get all pending requests, 1=request file upload url, 2=get file download url, 3=confirm file upload success (T:5, L:2)')
@click.option('--data-file', type=click.Path(exists=True), help='Path to JSON file for command data (T:6, L:0-64KB)')
@click.pass_context
@debug_log
def send_command(ctx, node_id: str, request_id: str, status: str, command: str, data_file: str = None):
    """Send a command from node to cloud.
    
    This command builds a Binary TLV format payload from individual parameters
    according to ESP RainMaker MQTT specification.
    
    TLV Format Requirements:
    - Type 1: Request ID (T:1, L:22, V:string) - Required
    - Type 3: Status (T:3, L:1, V:int) - Required
        0: success
        1: failed
        2: invalid command
        3: authorization failure
        4: not found
    - Type 5: Command (T:5, L:2, V:int) - Required
        0: get all pending requests
        1: request file upload url
        2: get file download url
        3: confirm file upload success
    - Type 6: Data (T:6, L:0-64KB, V:JSON) - Optional
    
    Examples:
        # Basic command
        node-command send-command --node-id node123 --request-id "req123" --status 0 --command 1
        
        # Command with data
        node-command send-command --node-id node123 --request-id "req123" --status 0 --command 1 --data-file data.json
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

        # Build payload from individual parameters
        try:
            logger.debug("Building payload from individual parameters")
            payload_data = {
                '1': request_id,  # Request ID
                '3': int(status),  # Status
                '5': int(command)  # Command
            }
            
            # Add data file if provided
            if data_file:
                logger.debug(f"Reading data file: {data_file}")
                try:
                    with open(data_file, 'r') as f:
                        data_content = json.load(f)
                    payload_data['6'] = data_content
                except Exception as e:
                    logger.debug(f"Invalid data file: {str(e)}")
                    click.echo(click.style(f"✗ Invalid data file: {str(e)}", fg='red'), err=True)
                    sys.exit(1)
                    
        except Exception as e:
            logger.debug(f"Error building payload: {str(e)}")
            click.echo(click.style(f"✗ Error building payload: {str(e)}", fg='red'), err=True)
            sys.exit(1)
        
        # Convert to TLV format
        try:
            final_payload = TLVHandler.encode_command(payload_data)
            logger.debug(f"TLV payload created: {final_payload.hex()}")
        except Exception as e:
            logger.debug(f"TLV conversion failed: {str(e)}")
            click.echo(click.style(f"✗ TLV conversion failed: {str(e)}", fg='red'), err=True)
            sys.exit(1)
        
        # Publish to from-node topic
        topic = f"node/{node_id}/from-node"
        logger.debug(f"Publishing Binary TLV to topic: {topic}")
        if mqtt_client.publish(topic, final_payload, qos=1):
            logger.debug("Binary TLV command published successfully")
            click.echo(click.style(f"✓ Sent Binary TLV command from node {node_id} to cloud", fg='green'))
            click.echo("\nCommand Details:")
            click.echo("-" * 60)
            click.echo(f"Topic: {topic}")
            click.echo(f"Node ID: {node_id}")
            click.echo("\nTLV Fields:")
            click.echo(f"  Type 1 (Request ID): {payload_data.get('1', 'missing')}")
            click.echo(f"  Type 3 (Status): {payload_data.get('3', 'missing')} - {TLVHandler.VALID_STATUS.get(payload_data.get('3'), 'unknown')}")
            click.echo(f"  Type 5 (Command): {payload_data.get('5', 'missing')} - {TLVHandler.VALID_COMMANDS.get(payload_data.get('5'), 'unknown')}")
            if '6' in payload_data:
                click.echo(f"  Type 6 (Data): {json.dumps(payload_data.get('6'), indent=2)}")
            click.echo("\nTLV Binary:")
            click.echo(f"Size: {len(final_payload)} bytes")
            click.echo(f"Hex: {final_payload.hex()}")
            click.echo("-" * 60)
            click.echo("\nCommand Parameters:")
            click.echo(f"  --request-id: {request_id}")
            click.echo(f"  --status: {status} ({TLVHandler.VALID_STATUS.get(int(status), 'unknown')})")
            click.echo(f"  --command: {command} ({TLVHandler.VALID_COMMANDS.get(int(command), 'unknown')})")
            if data_file:
                click.echo(f"  --data-file: {data_file}")
            click.echo("-" * 60)
            return 0
        else:
            logger.debug("Failed to publish Binary TLV command")
            raise MQTTError("Failed to send Binary TLV command")
            
    except MQTTError as e:
        logger.debug(f"MQTT error in send_command: {str(e)}")
        click.echo(click.style(f"✗ Failed to send command: {str(e)}", fg='red'), err=True)
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
            
        # Try to decode as TLV
        try:
            decoded = TLVHandler.decode_message(payload_bytes)
            if decoded:
                return {
                    'type': 'tlv',
                    'content': decoded,
                    'raw': payload_bytes.hex()
                }
        except Exception as e:
            logger.debug(f"TLV decode failed: {str(e)}")
            
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