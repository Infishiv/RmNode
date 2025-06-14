"""
MQTT CLI - A command-line interface for MQTT operations.
"""
import click
import logging
import sys
from pathlib import Path
from .utils.connection_manager import ConnectionManager
from .utils.config_manager import ConfigManager

# Configure logging - only show errors by default
logging.basicConfig(
    level=logging.ERROR,  # Changed from INFO to ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable AWS IoT SDK logging except for errors
for logger_name in ['AWSIoTPythonSDK', 
                   'AWSIoTPythonSDK.core',
                   'AWSIoTPythonSDK.core.protocol.internal.clients',
                   'AWSIoTPythonSDK.core.protocol.mqtt_core',
                   'AWSIoTPythonSDK.core.protocol.internal.workers',
                   'AWSIoTPythonSDK.core.protocol.internal.defaults',
                   'AWSIoTPythonSDK.core.protocol.internal.events']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

# Import command groups
from .commands.connection import connection
from .commands.messaging import messaging
from .commands.device import device
from .commands.ota import ota
from .commands.node_config import node
from .commands.user_mapping import user
from .commands.time_series import tsdata
from .commands.config import config

@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('--config-dir', 
              type=click.Path(file_okay=False, dir_okay=True),
              help='Configuration directory path')
@click.option('--debug', is_flag=True, help='Enable debug mode with detailed logging')
@click.option('--broker', 
              help='MQTT broker endpoint to use')
@click.option('--cert-path',
              type=click.Path(exists=True, dir_okay=True, file_okay=True),
              help='Direct certificate path to use instead of stored configuration')
@click.option('--mac',
              help='12-digit alphanumeric MAC address to find certificates')
@click.pass_context
def cli(ctx, config_dir, debug, broker, cert_path, mac):
    """MQTT CLI - A command-line interface for MQTT operations."""
    try:
        # Initialize context object
        ctx.ensure_object(dict)
        
        # Configure logging based on debug flag
        if debug:
            # Set root logger to DEBUG
            logging.getLogger().setLevel(logging.DEBUG)
            # Enable debug logging for AWS IoT SDK
            for logger_name in ['AWSIoTPythonSDK', 
                              'AWSIoTPythonSDK.core',
                              'AWSIoTPythonSDK.core.protocol.internal.clients',
                              'AWSIoTPythonSDK.core.protocol.mqtt_core',
                              'AWSIoTPythonSDK.core.protocol.internal.workers',
                              'AWSIoTPythonSDK.core.protocol.internal.defaults',
                              'AWSIoTPythonSDK.core.protocol.internal.events']:
                logging.getLogger(logger_name).setLevel(logging.DEBUG)
            click.echo("Debug mode enabled - detailed logging activated")
        
        # Set up configuration directory
        if config_dir:
            ctx.obj['CONFIG_DIR'] = Path(config_dir)
        else:
            # Use .rmnode as default config directory
            ctx.obj['CONFIG_DIR'] = Path('.rmnode')
            
        # Create config directory if it doesn't exist
        ctx.obj['CONFIG_DIR'].mkdir(parents=True, exist_ok=True)
        
        # Initialize configuration manager
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        
        # Set broker from command line option or config
        if broker:
            ctx.obj['BROKER'] = broker
            # Update broker in config if provided
            config_manager.set_broker(broker)
        else:
            # Use broker from config
            ctx.obj['BROKER'] = config_manager.get_broker()
        
        # Set up certificate folder and MAC address
        if cert_path:
            ctx.obj['CERT_PATH'] = Path(cert_path)
            ctx.obj['CERT_FOLDER'] = str(ctx.obj['CERT_PATH'])
            # Store MAC address in context if provided
            if mac:
                ctx.obj['MAC_ADDRESS'] = mac
        else:
            # Use certs folder in config directory
            ctx.obj['CERT_FOLDER'] = str(ctx.obj['CONFIG_DIR'] / 'certs')
            Path(ctx.obj['CERT_FOLDER']).mkdir(parents=True, exist_ok=True)

        # Initialize connection manager
        conn_manager = ConnectionManager(ctx.obj['CONFIG_DIR'])
        
        # Update broker in active connection if exists
        active_node = conn_manager.get_active_node()
        if active_node:
            conn_manager.update_connection_broker(active_node, ctx.obj['BROKER'])
        
        # Store managers in context
        ctx.obj['CONFIG_MANAGER'] = config_manager
        ctx.obj['CONNECTION_MANAGER'] = conn_manager
        
        # Store debug flag in context for other commands to access
        ctx.obj['DEBUG'] = debug
        
    except Exception as e:
        click.echo(f"Initialization error: {str(e)}", err=True)
        sys.exit(1)

# Register command groups
cli.add_command(connection)  # Basic MQTT connection management
cli.add_command(messaging)   # Basic MQTT pub/sub operations
cli.add_command(device)      # Device management
cli.add_command(ota)         # OTA update operations
cli.add_command(node)        # Node configuration and presence
cli.add_command(user)        # User-node mapping
cli.add_command(tsdata)      # Time series data operations
cli.add_command(config)      # Configuration management
    
if __name__ == '__main__':
    try:
        cli(obj={})
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    sys.exit(0)