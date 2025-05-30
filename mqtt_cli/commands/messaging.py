"""
Messaging commands for MQTT CLI.
"""
import click
import json
import sys
import logging
from ..utils.exceptions import MQTTConnectionError
from ..utils.debug_logger import debug_log, debug_step

# Get logger for this module
logger = logging.getLogger(__name__)

@click.group()
def messaging():
    """Messaging commands."""
    pass

@messaging.command('subscribe')
@click.option('--topic', required=True, help='Topic to subscribe to')
@click.option('--qos', default=1, type=int, help='QoS level (0,1)')
@click.pass_context
@debug_log
def subscribe(ctx, topic, qos):
    """Subscribe to a topic.
    
    Example: mqtt-cli messaging subscribe --topic my/topic/# --qos 1
    """
    try:
        if 'MQTT' not in ctx.obj:
            logger.debug("No MQTT connection found")
            raise Exception("Not connected. Use 'connect' first")
            
        logger.debug(f"Subscribing to topic '{topic}' with QoS {qos}")
        ctx.obj['MQTT'].subscribe(topic=topic, qos=qos)
        logger.debug(f"Successfully subscribed to topic '{topic}'")
        click.echo(click.style(f"✓ Subscribed to {topic}", fg='green'))
        return 0
    except Exception as e:
        logger.debug(f"Subscribe failed: {str(e)}")
        click.echo(click.style(f"✗ Subscribe failed: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@messaging.command('publish')
@click.option('--topic', required=True, help='Topic to publish to')
@click.option('--message', required=True, help='Message to publish')
@click.option('--qos', default=1, type=int, help='QoS level (0,1)')
@click.pass_context
@debug_log
def publish(ctx, topic, message, qos):
    """Publish a message to a topic.
    
    Example: mqtt-cli messaging publish --topic my/topic --message "Hello MQTT" --qos 1
    """
    try:
        if 'MQTT' not in ctx.obj:
            logger.debug("No MQTT connection found")
            raise Exception("Not connected. Use 'connect' first")
            
        logger.debug(f"Publishing to topic '{topic}' with QoS {qos}")
        logger.debug(f"Message content: {message}")
        ctx.obj['MQTT'].publish(topic=topic, message=message, qos=qos)
        logger.debug(f"Successfully published to topic '{topic}'")
        click.echo(click.style(f"✓ Published to {topic}", fg='green'))
        return 0
    except Exception as e:
        logger.debug(f"Publish failed: {str(e)}")
        click.echo(click.style(f"✗ Publish failed: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@messaging.command('monitor')
@click.option('--topic', required=True, help='Topic pattern to monitor')
@click.option('--qos', default=1, type=int, help='QoS level (0,1)')
@click.pass_context
@debug_log
def monitor(ctx, topic, qos):
    """Monitor messages on a topic pattern.
    
    Example: mqtt-cli messaging monitor --topic my/topic/# --qos 1
    """
    try:
        if 'MQTT' not in ctx.obj:
            logger.debug("No MQTT connection found")
            raise Exception("Not connected. Use 'connect' first")
            
        logger.debug(f"Starting monitoring for topic pattern '{topic}' with QoS {qos}")
        click.echo(f"Monitoring topic: {topic}")
        click.echo("Press Ctrl+C to stop...")
        
        def callback(client, userdata, message):
            try:
                logger.debug(f"Received message on topic: {message.topic}")
                payload = message.payload.decode()
                try:
                    # Try to parse and pretty print JSON
                    data = json.loads(payload)
                    payload = json.dumps(data, indent=2)
                    logger.debug("Message payload is valid JSON")
                except json.JSONDecodeError:
                    # Not JSON, use raw payload
                    logger.debug("Message payload is not JSON format")
                    pass
                click.echo(f"\nTopic: {message.topic}")
                click.echo(f"Message: {payload}")
            except Exception as e:
                logger.debug(f"Error processing message: {str(e)}")
                click.echo(f"Error processing message: {str(e)}")
        
        logger.debug("Setting up subscription with callback")
        ctx.obj['MQTT'].subscribe(topic=topic, qos=qos, callback=callback)
        logger.debug("Monitoring started successfully")
        
        # Keep the main thread alive
        while True:
            pass
            
    except KeyboardInterrupt:
        logger.debug("Monitoring stopped by user (Ctrl+C)")
        click.echo("\nMonitoring stopped")
        return 0
    except Exception as e:
        logger.debug(f"Monitor failed: {str(e)}")
        click.echo(click.style(f"✗ Monitor failed: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@messaging.command('unsubscribe')
@click.option('--topic', required=True, help='Topic to unsubscribe from')
@click.pass_context
@debug_log
def unsubscribe(ctx, topic):
    """Unsubscribe from a topic.
    
    Example: mqtt-cli messaging unsubscribe --topic my/topic/#
    """
    try:
        if 'MQTT' not in ctx.obj:
            logger.debug("No MQTT connection found")
            raise Exception("Not connected. Use 'connect' first")
            
        logger.debug(f"Unsubscribing from topic '{topic}'")
        ctx.obj['MQTT'].unsubscribe(topic)
        logger.debug(f"Successfully unsubscribed from topic '{topic}'")
        click.echo(click.style(f"✓ Unsubscribed from {topic}", fg='green'))
        return 0
    except Exception as e:
        logger.debug(f"Unsubscribe failed: {str(e)}")
        click.echo(click.style(f"✗ Unsubscribe failed: {str(e)}", fg='red'), err=True)
        sys.exit(1)

@messaging.command('list-subscriptions')
@click.pass_context
@debug_log
def list_subscriptions(ctx):
    """List all active subscriptions.
    
    Example: mqtt-cli messaging list-subscriptions
    """
    try:
        if 'MQTT' not in ctx.obj:
            logger.debug("No MQTT connection found")
            raise Exception("Not connected. Use 'connect' first")
            
        logger.debug("Retrieving active subscriptions")
        subscriptions = ctx.obj['MQTT'].list_subscriptions()
        logger.debug(f"Found {len(subscriptions)} active subscriptions")
        
        if not subscriptions:
            logger.debug("No active subscriptions found")
            click.echo("No active subscriptions")
            return 0
            
        click.echo("\nActive Subscriptions:")
        click.echo("-" * 40)
        for topic in subscriptions:
            logger.debug(f"Active subscription: {topic}")
            click.echo(f"- {topic}")
        click.echo("-" * 40)
        return 0
    except Exception as e:
        logger.debug(f"Failed to list subscriptions: {str(e)}")
        click.echo(click.style(f"✗ Failed to list subscriptions: {str(e)}", fg='red'), err=True)
        sys.exit(1) 