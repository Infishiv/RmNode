import click
import json
from pathlib import Path
from .mqtt_operations import MQTTOperations
from .config_manager import ConfigManager
from .ota_handler import OTAHandler

@click.group()
@click.option('--broker', default="a3q0b7ncspt14l-ats.iot.us-east-1.amazonaws.com", help='MQTT broker URL')
@click.option('--node-id', default="VmKK7rtYBdZYhhU8XeNKw4", help='Node ID')
# @click.option('--node-id', required=True, help='Node ID')
@click.option('--cert-folder', default="certs", help='Path to certificate folder')
@click.pass_context
def cli(ctx, broker, node_id, cert_folder):
    """MQTT CLI Client for IoT Operations"""
    ctx.ensure_object(dict)
    ctx.obj['BROKER'] = broker
    ctx.obj['NODE_ID'] = node_id
    ctx.obj['CERT_FOLDER'] = cert_folder
    ctx.obj['MQTT'] = MQTTOperations(broker=broker, node_id=node_id, cert_folder=cert_folder)
    ctx.obj['CONFIG'] = ConfigManager()

@cli.command()
@click.pass_context
def connect(ctx):
    """Connect to MQTT broker"""
    try:
        ctx.obj['MQTT'].connect()
        click.echo("Connected successfully")
    except Exception as e:
        click.echo(f"Connection failed: {str(e)}", err=True)

@cli.command()
@click.pass_context
def disconnect(ctx):
    """Disconnect from MQTT broker"""
    try:
        ctx.obj['MQTT'].disconnect()
        click.echo("Disconnected successfully")
    except Exception as e:
        click.echo(f"Disconnection failed: {str(e)}", err=True)

@cli.command()
@click.argument('topic')
@click.argument('message')
@click.option('--qos', default=1, help='QoS level (0,1)')
@click.pass_context
def publish(ctx, topic, message, qos):
    """Publish a message to a topic"""
    try:
        ctx.obj['MQTT'].publish(topic=topic, payload=message, qos=qos)
        click.echo(f"Published to {topic}: {message}")
    except Exception as e:
        click.echo(f"Publish failed: {str(e)}", err=True)

@cli.command()
@click.argument('topic')
@click.option('--qos', default=1, help='QoS level (0,1)')
@click.pass_context
def subscribe(ctx, topic, qos):
    """Subscribe to a topic"""
    try:
        ctx.obj['MQTT'].subscribe(topic=topic, qos=qos)
        click.echo(f"Subscribed to {topic}")
    except Exception as e:
        click.echo(f"Subscribe failed: {str(e)}", err=True)

@cli.command()
@click.argument('topic')
@click.pass_context
def unsubscribe(ctx, topic):
    """Unsubscribe from a topic"""
    try:
        ctx.obj['MQTT'].unsubscribe(topic=topic)
        click.echo(f"Unsubscribed from {topic}")
    except Exception as e:
        click.echo(f"Unsubscribe failed: {str(e)}", err=True)


@cli.group()
def device():
    """Device configuration commands"""
    pass


@device.command()
@click.argument('device_type', type=click.Choice(['light', 'washer', 'heater'], case_sensitive=False))
@click.pass_context
def make(ctx, device_type):
    """Make node act as specified device (light/washer/heater)"""
    try:
        config_mgr = ctx.obj['CONFIG']
        mqtt = ctx.obj['MQTT']
        node_id = ctx.obj['NODE_ID']

        # Get both config and params
        config, params = config_mgr.make_device(device_type)

        # Publish config
        mqtt.publish(
            topic=f"node/{node_id}/config",
            payload=json.dumps(config),
            qos=1
        )

        # Publish params
        mqtt.publish(
            topic=f"node/{node_id}/params",
            payload=json.dumps(params),
            qos=1
        )

        click.echo(f"Successfully configured node as {device_type}")
        """click.echo("Published config:")
        click.echo(json.dumps(config, indent=2))
        click.echo("Published params:")
        click.echo(json.dumps(params, indent=2))"""

    except Exception as e:
        click.echo(f"Failed to make device: {str(e)}", err=True)


@device.command()
@click.argument('power_state', type=click.Choice(['on', 'off'], case_sensitive=False))
@click.pass_context
def set_param(ctx, power_state):
    """Toggle device power state (on/off)"""
    try:
        config_mgr = ctx.obj['CONFIG']
        mqtt = ctx.obj['MQTT']
        node_id = ctx.obj['NODE_ID']

        # Get current device state
        device_type, config, params = config_mgr.get_current_device()
        new_power_state = power_state.lower() == 'on'

        # Update power state in config
        if 'Power' in config:
            config['Power'] = new_power_state
        elif 'power' in config:
            config['power'] = new_power_state
        else:
            raise Exception("Power parameter not found in device config")

        # Save back to file
        config_mgr.update_device_config(device_type, config)

        # Publish update
        mqtt.publish(
            topic=f"node/{node_id}/config",
            payload=json.dumps(config),
            qos=1
        )

        # Update stored config
        config_mgr.current_config = config
        config_mgr._save_state()

        click.echo(f"Set {device_type} power state to {'ON' if new_power_state else 'OFF'}")
        click.echo("Updated config:")
        click.echo(json.dumps(config, indent=2))
    except Exception as e:
        click.echo(f"Failed to update power state: {str(e)}", err=True)


@device.command()
@click.pass_context
def show(ctx):
    """Show current device configuration"""
    try:
        config_mgr = ctx.obj['CONFIG']
        device_type, config, params = config_mgr.get_current_device()

        click.echo(f"Current device type: {device_type}")
    except Exception as e:
        click.echo(f"Failed to show configuration: {str(e)}", err=True)



@cli.group()
def ota():
    """Over-the-Air (OTA) update commands"""
    pass


@ota.command()
@click.option('--fw-version', default="1.0.0", help='Current firmware version')
@click.option('--timeout', default=60, help='Timeout in seconds (default: 60)')
@click.pass_context
def request(ctx, fw_version, timeout):
    """Request OTA update and wait for URL"""
    try:
        # Initialize with automatic connection
        ota = OTAHandler(ctx.obj['MQTT'], ctx.obj['NODE_ID'])

        click.echo(f"Connecting to broker...")
        ota._ensure_connected()  # Force connection

        click.echo(f"Requesting OTA update (v{fw_version})...")
        job = ota.request_ota(fw_version, timeout)

        if job:
            click.echo(f"OTA Job Received:")
            click.echo(f" ID: {job['ota_job_id']}")
            click.echo(f" URL: {job.get('url')}")
            click.echo(f" Firmware: {job.get('fw_version')}")

            if click.confirm("Send success status automatically?"):
                ota.send_ota_status(job['ota_job_id'])
                click.echo("Success status sent")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@ota.command()
@click.argument('job_id')
@click.option('--status',
              type=click.Choice(['success', 'failed', 'in_progress', 'rejected'], case_sensitive=False),
              default=None,
              help='OTA status (if not specified, will show interactive menu)')
@click.option('--info', default="", help='Additional status info')
@click.pass_context
def status(ctx, job_id, status, info):
    """Send OTA status update (interactive if no status specified)"""
    try:
        ota = OTAHandler(ctx.obj['MQTT'], ctx.obj['NODE_ID'])

        if status:
            # Direct status update if status is provided
            ota.send_ota_status(job_id, status, info)
            click.echo(f"Sent status '{status}' for job {job_id}")
        else:
            # Show interactive menu if no status provided
            ota._show_status_menu(job_id)

    except Exception as e:
        click.echo(f"Failed: {str(e)}", err=True)

if __name__ == '__main__':
    cli(obj={})