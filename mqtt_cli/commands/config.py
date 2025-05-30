"""
Configuration management commands for MQTT CLI.
"""
import click
import os
import logging
from pathlib import Path
from ..utils.cert_finder import find_node_cert_key_pairs_path
from ..utils.config_manager import ConfigManager
from ..utils.debug_logger import debug_log, debug_step

# Get logger for this module
logger = logging.getLogger(__name__)

@click.group()
def config():
    """Configuration management commands."""
    pass

@config.command('set-broker')
@click.option('--url', required=True, help='MQTT broker URL')
@click.pass_context
@debug_log
def set_broker(ctx, url):
    """Set the MQTT broker URL.
    
    Example: mqtt-cli config set-broker --url mqtt://broker.example.com
    """
    try:
        logger.debug(f"Setting broker URL to: {url}")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.set_broker(url)
        logger.debug("Successfully set broker URL")
        click.echo(click.style(f"✓ Set broker URL to {url}", fg='green'))
    except Exception as e:
        logger.debug(f"Error setting broker URL: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('get-broker')
@click.pass_context
@debug_log
def get_broker(ctx):
    """Get the current MQTT broker URL.
    
    Example: mqtt-cli config get-broker
    """
    try:
        logger.debug("Getting current broker URL")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        broker = config_manager.get_broker()
        logger.debug(f"Retrieved broker URL: {broker}")
        click.echo(f"Current broker URL: {broker}")
    except Exception as e:
        logger.debug(f"Error getting broker URL: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('set-cert-path')
@click.option('--path', required=True, help='Path to Rainmaker admin CLI')
@click.option('--update/--no-update', default=True, 
              help='Update existing nodes if they exist (default: True)')
@click.pass_context
@debug_log
def set_admin_cli(ctx, path, update):
    """Set the Nodes's Certs path and discover nodes.
    
    Example: mqtt-cli config set-admin-cli --path /path/to/admin-cli --update
    """
    try:
        logger.debug(f"Setting admin CLI path to: {path}")
        path = Path(path).resolve()
        if not path.exists():
            logger.debug(f"Path does not exist: {path}")
            click.echo(click.style(f"✗ Path does not exist: {path}", fg='red'), err=True)
            raise click.Abort()
            
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.set_admin_cli_path(str(path))
        logger.debug("Successfully set admin CLI path")
        
        # Auto-discover nodes
        logger.debug("Starting node auto-discovery")
        nodes = find_node_cert_key_pairs_path(path)
        if not nodes:
            logger.debug("No nodes found in admin CLI directory")
            click.echo(click.style("No nodes found in admin CLI directory.", fg='yellow'))
            return
            
        # Track new and updated nodes
        new_nodes = []
        updated_nodes = []
        logger.debug(f"Found {len(nodes)} nodes to process")
        
        # Get broker URL from config or context
        broker_url = config_manager.get_broker() or ctx.obj.get('BROKER')
        logger.debug(f"Using broker URL: {broker_url}")
        
        for node_id, cert_path, key_path in nodes:
            logger.debug(f"Processing node {node_id}")
            existing = config_manager.get_node_paths(node_id)
            if existing:
                if update:
                    logger.debug(f"Updating existing node {node_id}")
                    config_manager.add_node(node_id, cert_path, key_path)
                    updated_nodes.append(node_id)
            else:
                logger.debug(f"Adding new node {node_id}")
                config_manager.add_node(node_id, cert_path, key_path)
                new_nodes.append(node_id)
            
        # Print results
        click.echo(click.style(f"✓ Admin CLI path set to: {path}", fg='green'))
        if new_nodes:
            logger.debug(f"Added {len(new_nodes)} new nodes")
            click.echo(click.style(f"✓ Added {len(new_nodes)} new node(s):", fg='green'))
            for node_id in new_nodes:
                click.echo(f"  - {node_id}")
        if updated_nodes:
            logger.debug(f"Updated {len(updated_nodes)} existing nodes")
            click.echo(click.style(f"✓ Updated {len(updated_nodes)} existing node(s):", fg='blue'))
            for node_id in updated_nodes:
                click.echo(f"  - {node_id}")
        if not new_nodes and not updated_nodes:
            logger.debug("No changes made to node configurations")
            click.echo(click.style("No changes made to node configurations.", fg='yellow'))
            
    except Exception as e:
        logger.debug(f"Error setting admin CLI path: {str(e)}")
        click.echo(click.style(f"✗ Failed to set admin CLI path: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('get-cert-path')
@click.pass_context
@debug_log
def get_admin_cli(ctx):
    """Get the Nodes's Certs path.
    
    Example: mqtt-cli config get-admin-cli
    """
    try:
        logger.debug("Getting admin CLI path")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        path = config_manager.get_admin_cli_path()
        if path:
            logger.debug(f"Retrieved admin CLI path: {path}")
            click.echo(f"Admin CLI path: {path}")
        else:
            logger.debug("Admin CLI path not set")
            click.echo("Admin CLI path not set")
    except Exception as e:
        logger.debug(f"Error getting admin CLI path: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('list-nodes')
@click.pass_context
@debug_log
def list_nodes(ctx):
    """List all configured nodes.
    
    Example: mqtt-cli config list-nodes
    """
    try:
        logger.debug("Listing configured nodes")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        nodes = config_manager.list_nodes()
        
        if not nodes:
            logger.debug("No nodes configured")
            click.echo("No nodes configured")
            return
            
        logger.debug(f"Found {len(nodes)} configured nodes")
        click.echo("\nConfigured Nodes:")
        click.echo("-" * 60)
        for node_id, info in nodes.items():
            logger.debug(f"Node {node_id}: cert={info['cert_path']}, key={info['key_path']}")
            click.echo(f"Node ID: {node_id}")
            click.echo(f"  Certificate: {info['cert_path']}")
            click.echo(f"  Key: {info['key_path']}")
            click.echo("-" * 60)
    except Exception as e:
        logger.debug(f"Error listing nodes: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('add-node')
@click.option('--node-id', required=True, help='Node ID to add')
@click.option('--cert-path', required=True, help='Path to node certificate')
@click.option('--key-path', required=True, help='Path to node key')
@click.pass_context
@debug_log
def add_node(ctx, node_id, cert_path, key_path):
    """Add or update a node's certificate paths.
    
    Example: mqtt-cli config add-node --node-id node123 --cert-path /path/to/cert.pem --key-path /path/to/key.pem
    """
    try:
        logger.debug(f"Adding/updating node {node_id}")
        logger.debug(f"Certificate path: {cert_path}")
        logger.debug(f"Key path: {key_path}")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.add_node(node_id, cert_path, key_path)
        logger.debug(f"Successfully added/updated node {node_id}")
        click.echo(click.style(f"✓ Added/updated node {node_id}", fg='green'))
    except Exception as e:
        logger.debug(f"Error adding/updating node: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('remove-node')
@click.option('--node-id', required=True, help='Node ID to remove')
@click.pass_context
@debug_log
def remove_node(ctx, node_id):
    """Remove a node's configuration.
    
    Example: mqtt-cli config remove-node --node-id node123
    """
    try:
        logger.debug(f"Removing node {node_id}")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        if config_manager.remove_node(node_id):
            logger.debug(f"Successfully removed node {node_id}")
            click.echo(click.style(f"✓ Removed node {node_id}", fg='green'))
        else:
            logger.debug(f"Node {node_id} not found")
            click.echo(click.style(f"✗ Node {node_id} not found", fg='yellow'))
    except Exception as e:
        logger.debug(f"Error removing node: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('reset')
@click.confirmation_option(prompt='Are you sure you want to reset all configuration?')
@click.pass_context
@debug_log
def reset(ctx):
    """Reset all configuration to defaults.
    
    Example: mqtt-cli config reset
    """
    try:
        logger.debug("Resetting all configuration to defaults")
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.reset()
        logger.debug("Successfully reset configuration")
        click.echo(click.style("✓ Configuration reset to defaults", fg='green'))
    except Exception as e:
        logger.debug(f"Error resetting configuration: {str(e)}")
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 