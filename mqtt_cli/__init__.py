"""
MQTT CLI tool for device management.
"""
import os
import click
from pathlib import Path
from .commands.connection import connection
from .commands.ota import ota
from .utils.connection_manager import ConnectionManager
from .utils.config_manager import ConfigManager
from .mqtt_operations import MQTTOperations

__all__ = ['MQTTOperations', 'ConfigManager']

@click.group()
@click.pass_context
def cli(ctx):
    """MQTT CLI tool for device management."""
    # Initialize context
    ctx.ensure_object(dict)
    
    # Set up config directory
    config_dir = Path.home() / '.mqtt-cli'
    config_dir.mkdir(exist_ok=True)
    ctx.obj['CONFIG_DIR'] = config_dir
    
    # Initialize connection manager
    ctx.obj['CONNECTION_MANAGER'] = ConnectionManager(config_dir)
    
    # Load active connection if any
    active_connection = ctx.obj['CONNECTION_MANAGER'].get_active_connection()
    if active_connection:
        ctx.obj['MQTT'] = active_connection
        ctx.obj['NODE_ID'] = ctx.obj['CONNECTION_MANAGER'].active_node

# Register command groups
cli.add_command(connection)
cli.add_command(ota)