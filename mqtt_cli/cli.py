"""
MQTT CLI Main Module
"""
import click
import os
import logging
import sys
from pathlib import Path

# Import command groups
from .commands.connection import connection
from .commands.messaging import messaging
from .commands.device import device
from .commands.node_config import node
from .commands.time_series import tsdata
from .commands.ota import ota
from .commands.user_mapping import user
from .commands.config import config

# Import utilities
from .utils.config_manager import ConfigManager
from .utils.connection_manager import ConnectionManager

@click.group()
@click.option('--config-dir',
              type=click.Path(file_okay=False, dir_okay=True),
              default=click.get_app_dir('mqtt_cli'),
              help='Configuration directory')
@click.option('--debug',
              is_flag=True,
              help='Enable debug logging')
@click.option('--broker',
              help='MQTT broker URL (overrides configuration)')
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
        
        # Set up configuration directory
        config_dir = Path(config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        ctx.obj['CONFIG_DIR'] = config_dir
        
        # Set up debug logging if requested
        if debug:
            logging.basicConfig(level=logging.DEBUG, 
                              format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            click.echo("Debug mode enabled - detailed logging activated")
            
        # Initialize config manager
        config_manager = ConfigManager(config_dir)
        ctx.obj['CONFIG_MANAGER'] = config_manager
        
        # Initialize connection manager
        connection_manager = ConnectionManager(config_dir)
        ctx.obj['CONNECTION_MANAGER'] = connection_manager
        
        # Store debug flag in context
        ctx.obj['DEBUG'] = debug
        
        # Set up broker URL
        if broker:
            # Use broker from command line
            ctx.obj['BROKER'] = broker
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
            # Store MAC address in context if provided (for config-based cert search)
            if mac:
                ctx.obj['MAC_ADDRESS'] = mac
                
    except Exception as e:
        click.echo(click.style(f"✗ Initialization error: {str(e)}", fg='red'), err=True)
        sys.exit(1)

# Add command groups
cli.add_command(connection)
cli.add_command(messaging)
cli.add_command(device)
cli.add_command(node)
cli.add_command(tsdata)
cli.add_command(ota)
cli.add_command(user)
cli.add_command(config)

if __name__ == '__main__':
    cli()