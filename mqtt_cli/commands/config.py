"""
Configuration management commands for MQTT CLI.
"""
import click
import os
from pathlib import Path
from ..utils.cert_finder import find_node_cert_key_pairs_path
from ..utils.config_manager import ConfigManager

@click.group()
def config():
    """Configuration management commands."""
    pass

@config.command('set-broker')
@click.option('--url', required=True, help='MQTT broker URL')
@click.pass_context
def set_broker(ctx, url):
    """Set the MQTT broker URL.
    
    Example: mqtt-cli config set-broker --url mqtt://broker.example.com
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.set_broker(url)
        click.echo(click.style(f"✓ Set broker URL to {url}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('get-broker')
@click.pass_context
def get_broker(ctx):
    """Get the current MQTT broker URL.
    
    Example: mqtt-cli config get-broker
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        broker = config_manager.get_broker()
        click.echo(f"Current broker URL: {broker}")
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('set-cert-path')
@click.option('--path', required=True, help='Path to Rainmaker admin CLI')
@click.option('--update/--no-update', default=True, 
              help='Update existing nodes if they exist (default: True)')
@click.pass_context
def set_admin_cli(ctx, path, update):
    """Set the Nodes's Certs path and discover nodes.
    
    Example: mqtt-cli config set-admin-cli --path /path/to/admin-cli --update
    """
    try:
        path = Path(path).resolve()
        if not path.exists():
            click.echo(click.style(f"✗ Path does not exist: {path}", fg='red'), err=True)
            raise click.Abort()
            
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.set_admin_cli_path(str(path))
        
        # Auto-discover nodes
        nodes = find_node_cert_key_pairs_path(path)
        if not nodes:
            click.echo(click.style("No nodes found in admin CLI directory.", fg='yellow'))
            return
            
        # Track new and updated nodes
        new_nodes = []
        updated_nodes = []
        
        # Get broker URL from config or context
        broker_url = config_manager.get_broker() or ctx.obj.get('BROKER')
        
        for node_id, cert_path, key_path in nodes:
            existing = config_manager.get_node_paths(node_id)
            if existing:
                if update:
                    config_manager.add_node(node_id, cert_path, key_path)
                    updated_nodes.append(node_id)
            else:
                config_manager.add_node(node_id, cert_path, key_path)
                new_nodes.append(node_id)
            
        # Print results
        click.echo(click.style(f"✓ Admin CLI path set to: {path}", fg='green'))
        if new_nodes:
            click.echo(click.style(f"✓ Added {len(new_nodes)} new node(s):", fg='green'))
            for node_id in new_nodes:
                click.echo(f"  - {node_id}")
        if updated_nodes:
            click.echo(click.style(f"✓ Updated {len(updated_nodes)} existing node(s):", fg='blue'))
            for node_id in updated_nodes:
                click.echo(f"  - {node_id}")
        if not new_nodes and not updated_nodes:
            click.echo(click.style("No changes made to node configurations.", fg='yellow'))
            
    except Exception as e:
        click.echo(click.style(f"✗ Failed to set admin CLI path: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('get-cert-path')
@click.pass_context
def get_admin_cli(ctx):
    """Get the Nodes's Certs path.
    
    Example: mqtt-cli config get-admin-cli
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        path = config_manager.get_admin_cli_path()
        if path:
            click.echo(f"Admin CLI path: {path}")
        else:
            click.echo("Admin CLI path not set")
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('list-nodes')
@click.pass_context
def list_nodes(ctx):
    """List all configured nodes.
    
    Example: mqtt-cli config list-nodes
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        nodes = config_manager.list_nodes()
        
        if not nodes:
            click.echo("No nodes configured")
            return
            
        click.echo("\nConfigured Nodes:")
        click.echo("-" * 60)
        for node_id, info in nodes.items():
            click.echo(f"Node ID: {node_id}")
            click.echo(f"  Certificate: {info['cert_path']}")
            click.echo(f"  Key: {info['key_path']}")
            click.echo("-" * 60)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('add-node')
@click.option('--node-id', required=True, help='Node ID to add')
@click.option('--cert-path', required=True, help='Path to node certificate')
@click.option('--key-path', required=True, help='Path to node key')
@click.pass_context
def add_node(ctx, node_id, cert_path, key_path):
    """Add or update a node's certificate paths.
    
    Example: mqtt-cli config add-node --node-id node123 --cert-path /path/to/cert.pem --key-path /path/to/key.pem
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.add_node(node_id, cert_path, key_path)
        click.echo(click.style(f"✓ Added/updated node {node_id}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('remove-node')
@click.option('--node-id', required=True, help='Node ID to remove')
@click.pass_context
def remove_node(ctx, node_id):
    """Remove a node's configuration.
    
    Example: mqtt-cli config remove-node --node-id node123
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        if config_manager.remove_node(node_id):
            click.echo(click.style(f"✓ Removed node {node_id}", fg='green'))
        else:
            click.echo(click.style(f"✗ Node {node_id} not found", fg='yellow'))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@config.command('reset')
@click.confirmation_option(prompt='Are you sure you want to reset all configuration?')
@click.pass_context
def reset(ctx):
    """Reset all configuration to defaults.
    
    Example: mqtt-cli config reset
    """
    try:
        config_manager = ConfigManager(ctx.obj['CONFIG_DIR'])
        config_manager.reset()
        click.echo(click.style("✓ Configuration reset to defaults", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'), err=True)
        raise click.Abort() 