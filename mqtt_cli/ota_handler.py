# ota_handler.py (updated)
import json
import time
import logging
from typing import Optional, Dict, Union


class OTAHandler:
    def __init__(self, mqtt_client, node_id: str):
        self.mqtt_client = mqtt_client
        self.node_id = node_id
        self.logger = logging.getLogger("ota_handler")
        self._subscription_messages = {}
        self._connected = False

    def _ensure_connected(self):
        """Ensure we're connected before operations"""
        if not self._connected:
            self.mqtt_client.connect()
            self._connected = True

    def request_ota(self, fw_version: str = "1.0.0", timeout: int = 30) -> Optional[Dict]:
        """Request OTA update and wait for URL"""
        self._ensure_connected()

        otaurl_topic = f"node/{self.node_id}/otaurl"
        otafetch_topic = f"node/{self.node_id}/otafetch"

        try:
            # Clear previous state
            self._subscription_messages.clear()

            # Subscribe first to avoid missing messages
            self.mqtt_client.subscribe(
                topic=otaurl_topic,
                callback=self._message_callback
            )
            time.sleep(1)  # Small delay to ensure subscription is active

            # Then publish the request
            payload = {"fw_version": fw_version}
            self.logger.info(f"Publishing OTA request for version {fw_version}")
            self.mqtt_client.publish(
                topic=otafetch_topic,
                payload=json.dumps(payload),
                qos=1
            )

            # Wait with progress updates
            self.logger.info(f"Waiting for OTA URL (timeout: {timeout}s)")
            start_time = time.time()

            while time.time() - start_time < timeout:
                msg = self._subscription_messages.get(otaurl_topic)
                if msg:
                    try:
                        job = json.loads(msg.decode() if isinstance(msg, bytes) else msg)
                        self.logger.info(f" Received OTA job: {job.get('ota_job_id')}")

                        # Show interactive menu for status update
                        self._show_status_menu(job['ota_job_id'])
                        return job
                    except json.JSONDecodeError:
                        self.logger.error("⚠Invalid OTA message format")
                        continue

                time.sleep(1)
                if int(time.time() - start_time) % 5 == 0:
                    self.logger.info(f"Still waiting... {int(time.time() - start_time)}s elapsed")

            self.logger.warning(f"Timeout waiting for OTA URL")
            return None

        except Exception as e:
            self.logger.error(f"OTA request failed: {str(e)}")
            raise

    def _show_status_menu(self, job_id: str):
        """Show interactive menu for status update"""
        import click

        while True:
            click.echo("\nSelect OTA status to send:")
            click.echo("1. Success")
            click.echo("2. Failed")
            click.echo("3. In Progress")
            click.echo("4. Rejected")
            click.echo("5. Exit")

            choice = click.prompt("Enter your choice (1-5)", type=int)

            status_map = {
                1: "success",
                2: "failed",
                3: "in_progress",
                4: "rejected"
            }

            if choice == 5:
                break

            if choice in status_map:
                status = status_map[choice]
                info = click.prompt("Enter additional info (optional)", default="", show_default=False)

                try:
                    if self.send_ota_status(job_id, status, info):
                        click.echo(f"\nSuccessfully sent {status} status for job {job_id}")
                        click.echo(f"   Additional info: {info if info else 'None'}")
                    else:
                        click.echo("\nFailed to send status update", err=True)
                except Exception as e:
                    click.echo(f"\nError: {str(e)}", err=True)
            else:
                click.echo("Invalid choice, please try again")

    def send_ota_status(self, job_id: str, status: str, additional_info: str = "") -> bool:
        """
        Send OTA status update with four possible statuses

        Args:
            job_id: OTA job identifier
            status: Status value (success/failed/in_progress/rejected)
            additional_info: Optional status details

        Returns:
            True if publish was successful
        """
        otastatus_topic = f"node/{self.node_id}/otastatus"

        try:
            if status not in ["success", "failed", "in_progress", "rejected"]:
                raise ValueError("Invalid status. Must be one of: success, failed, in_progress, rejected")

            payload = {
                "status": status,
                "ota_job_id": job_id,
                "additional_info": additional_info,
                "timestamp": int(time.time())  # Add timestamp for tracking
            }

            self.logger.info(f"Sending OTA status: {status} for job {job_id}")
            self._ensure_connected()  # Ensure we're connected before publishing

            # Publish with QoS 1 to ensure delivery
            result = self.mqtt_client.publish(
                topic=otastatus_topic,
                payload=json.dumps(payload),
                qos=1
            )

            if not result:
                self.logger.error("Failed to publish OTA status")
                return False

            self.logger.info(f"Status published successfully to {otastatus_topic}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send OTA status: {str(e)}")
            raise




    def _message_callback(self, client, userdata, message):
        """Callback for handling incoming messages"""
        self._subscription_messages[message.topic] = message.payload