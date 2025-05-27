"""
Messaging commands for MQTT CLI.
"""
import click
import json
from ..utils.exceptions import MQTTConnectionError

@click.group()
def messaging():
    """Messaging commands."""
    pass

@messaging.command('subscribe')
@click.option('--topic', required=True, help='Topic to subscribe to')
@click.option('--qos', default=1, type=int, help='QoS level (0,1)')
@click.pass_context
def subscribe(ctx, topic, qos):
    """Subscribe to a topic.
    
    Example: mqtt-cli messaging subscribe --topic my/topic/# --qos 1
    """
    try:
        if 'MQTT' not in ctx.obj:
            raise Exception("Not connected. Use 'connect' first")
            
        ctx.obj['MQTT'].subscribe(topic=topic, qos=qos)
        click.echo(click.style(f"✓ Subscribed to {topic}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Subscribe failed: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@messaging.command('publish')
@click.option('--topic', required=True, help='Topic to publish to')
@click.option('--message', required=True, help='Message to publish')
@click.option('--qos', default=1, type=int, help='QoS level (0,1)')
@click.pass_context
def publish(ctx, topic, message, qos):
    """Publish a message to a topic.
    
    Example: mqtt-cli messaging publish --topic my/topic --message "Hello MQTT" --qos 1
    """
    try:
        if 'MQTT' not in ctx.obj:
            raise Exception("Not connected. Use 'connect' first")
            
        ctx.obj['MQTT'].publish(topic=topic, message=message, qos=qos)
        click.echo(click.style(f"✓ Published to {topic}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Publish failed: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@messaging.command('monitor')
@click.option('--topic', required=True, help='Topic pattern to monitor')
@click.option('--qos', default=1, type=int, help='QoS level (0,1)')
@click.pass_context
def monitor(ctx, topic, qos):
    """Monitor messages on a topic pattern.
    
    Example: mqtt-cli messaging monitor --topic my/topic/# --qos 1
    """
    try:
        if 'MQTT' not in ctx.obj:
            raise Exception("Not connected. Use 'connect' first")
            
        click.echo(f"Monitoring topic: {topic}")
        click.echo("Press Ctrl+C to stop...")
        
        def callback(client, userdata, message):
            try:
                payload = message.payload.decode()
                try:
                    # Try to parse and pretty print JSON
                    data = json.loads(payload)
                    payload = json.dumps(data, indent=2)
                except json.JSONDecodeError:
                    # Not JSON, use raw payload
                    pass
                click.echo(f"\nTopic: {message.topic}")
                click.echo(f"Message: {payload}")
            except Exception as e:
                click.echo(f"Error processing message: {str(e)}")
        
        ctx.obj['MQTT'].subscribe(topic=topic, qos=qos, callback=callback)
        
        # Keep the main thread alive
        while True:
            pass
            
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped")
    except Exception as e:
        click.echo(click.style(f"✗ Monitor failed: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@messaging.command('unsubscribe')
@click.option('--topic', required=True, help='Topic to unsubscribe from')
@click.pass_context
def unsubscribe(ctx, topic):
    """Unsubscribe from a topic.
    
    Example: mqtt-cli messaging unsubscribe --topic my/topic/#
    """
    try:
        if 'MQTT' not in ctx.obj:
            raise Exception("Not connected. Use 'connect' first")
            
        ctx.obj['MQTT'].unsubscribe(topic)
        click.echo(click.style(f"✓ Unsubscribed from {topic}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Unsubscribe failed: {str(e)}", fg='red'), err=True)
        raise click.Abort()

@messaging.command('list-subscriptions')
@click.pass_context
def list_subscriptions(ctx):
    """List all active subscriptions.
    
    Example: mqtt-cli messaging list-subscriptions
    """
    try:
        if 'MQTT' not in ctx.obj:
            raise Exception("Not connected. Use 'connect' first")
            
        subscriptions = ctx.obj['MQTT'].list_subscriptions()
        if not subscriptions:
            click.echo("No active subscriptions")
            return
            
        click.echo("\nActive Subscriptions:")
        click.echo("-" * 40)
        for topic in subscriptions:
            click.echo(f"- {topic}")
        click.echo("-" * 40)
    except Exception as e:
        click.echo(click.style(f"✗ Failed to list subscriptions: {str(e)}", fg='red'), err=True)
        raise click.Abort() 