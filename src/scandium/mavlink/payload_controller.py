"""scandium.mavlink.payload_controller

Payload drop servo controller using MAVLink commands.

This module provides a PayloadController class that issues MAV_CMD_DO_SET_SERVO
commands to set a servo PWM for dropping payloads. The controller is defensive,
waits for COMMAND_ACK from the autopilot, and prevents duplicate releases.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Tuple

from pymavlink import mavutil

# MAVLink command id for setting a servo output
MAV_CMD_DO_SET_SERVO = mavutil.mavlink.MAV_CMD_DO_SET_SERVO

logger = logging.getLogger(__name__)


class PayloadController:
    """Controller to command servo outputs for payload release via MAVLink.

    Parameters
    ----------
    mav_connection: pymavlink mavutil.mavlink_connection
        Active pymavlink connection created with mavutil.mavlink_connection(...)
    servo_channel: int
        Servo channel (servo number) to command (default: 9).
    pwm_payload_1: int
        PWM value to send to release payload 1 (default: 1500).
    pwm_payload_2: int
        PWM value to send to release payload 2 (default: 2000).

    Attributes
    ----------
    payload1_released: bool
        True if payload1 has been successfully released (ack received).
    payload2_released: bool
        True if payload2 has been successfully released (ack received).
    """

    def __init__(
        self,
        mav_connection: mavutil.mavlink_connection,
        servo_channel: int = 9,
        pwm_payload_1: int = 1500,
        pwm_payload_2: int = 2000,
    ) -> None:
        self.mav_connection = mav_connection
        self.servo_channel = int(servo_channel)
        self.pwm_payload_1 = int(pwm_payload_1)
        self.pwm_payload_2 = int(pwm_payload_2)

        # State flags to prevent duplicate releases
        self.payload1_released: bool = False
        self.payload2_released: bool = False

    def _wait_for_ack(self, command_id: int, timeout_s: float = 1.0) -> bool:
        """Wait for a COMMAND_ACK for the given command_id.

        Non-blocking polling of the MAVLink port is used. The method returns True if a
        COMMAND_ACK with command == command_id and result == MAV_RESULT_ACCEPTED is
        received within timeout_s seconds. If a COMMAND_ACK is received with the same
        command but a non-accepted result the method returns False immediately. If the
        timeout expires without a matching ACK, returns False.

        Args:
            command_id: integer MAV command id to match in COMMAND_ACK.command
            timeout_s: maximum time to wait (seconds)

        Returns:
            bool: True if ACK accepted, False otherwise
        """
        end_time = time.time() + float(timeout_s)
        MAV_RESULT_ACCEPTED = mavutil.mavlink.MAV_RESULT_ACCEPTED

        while time.time() < end_time:
            try:
                msg = self.mav_connection.recv_match(type='COMMAND_ACK', blocking=False)
            except Exception as exc:
                logger.error("Error receiving COMMAND_ACK: %s", exc)
                return False

            if msg is None:
                time.sleep(0.02)
                continue

            # Extract fields defensively
            try:
                msg_command = int(getattr(msg, 'command', -1))
                msg_result = int(getattr(msg, 'result', -1))
            except Exception:
                logger.warning("Malformed COMMAND_ACK message received: %s", msg)
                continue

            if msg_command != int(command_id):
                logger.debug("Received COMMAND_ACK for other command (got=%s expected=%s)", msg_command, command_id)
                continue

            # Matching command_id
            if msg_result == MAV_RESULT_ACCEPTED:
                logger.info("Received COMMAND_ACK accepted for command %s", command_id)
                return True

            logger.warning("Received COMMAND_ACK for command %s but result=%s (not accepted)", command_id, msg_result)
            return False

        logger.warning("Timeout waiting for COMMAND_ACK for command %s", command_id)
        return False

    def _send_set_servo(self, pwm: int) -> bool:
        """Send MAV_CMD_DO_SET_SERVO to the vehicle using pymavlink API.

        Returns True if the send call completed without raising; this does not
        guarantee the autopilot executed the command (ACK must be awaited).
        """
        try:
            tgt_sys = getattr(self.mav_connection, 'target_system', 0)
            tgt_comp = getattr(self.mav_connection, 'target_component', 0)

            # command_long_send(target_system, target_component, command, confirmation, p1..p7)
            # param1 = servo number, param2 = pwm
            self.mav_connection.mav.command_long_send(
                int(tgt_sys),
                int(tgt_comp),
                int(MAV_CMD_DO_SET_SERVO),
                0,
                float(self.servo_channel),
                float(pwm),
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            )
            logger.info("Sent MAV_CMD_DO_SET_SERVO: channel=%s pwm=%s (tgt_sys=%s tgt_comp=%s)",
                        self.servo_channel, pwm, tgt_sys, tgt_comp)
            return True
        except Exception as exc:
            logger.error("Failed to send MAV_CMD_DO_SET_SERVO: %s", exc)
            return False

    def release_payload_1(self) -> bool:
        """Release payload 1 by sending pwm_payload_1 to servo_channel and awaiting ACK.

        Returns True if the command was sent and a positive COMMAND_ACK was received.
        Prevents duplicate releases by checking payload1_released flag.
        """
        if self.payload1_released:
            logger.info("release_payload_1 called but payload1 already released; skipping")
            return False

        sent = self._send_set_servo(self.pwm_payload_1)
        if not sent:
            logger.error("Failed to send servo command for payload1")
            return False

        ack_ok = self._wait_for_ack(MAV_CMD_DO_SET_SERVO)
        if not ack_ok:
            logger.error("Did not receive accepted COMMAND_ACK for payload1 release")
            return False

        self.payload1_released = True
        logger.info("Payload1 release confirmed and flag set")
        return True

    def release_payload_2(self) -> bool:
        """Release payload 2 by sending pwm_payload_2 to servo_channel and awaiting ACK.

        Returns True if the command was sent and a positive COMMAND_ACK was received.
        Prevents duplicate releases by checking payload2_released flag.
        """
        if self.payload2_released:
            logger.info("release_payload_2 called but payload2 already released; skipping")
            return False

        sent = self._send_set_servo(self.pwm_payload_2)
        if not sent:
            logger.error("Failed to send servo command for payload2")
            return False

        ack_ok = self._wait_for_ack(MAV_CMD_DO_SET_SERVO)
        if not ack_ok:
            logger.error("Did not receive accepted COMMAND_ACK for payload2 release")
            return False

        self.payload2_released = True
        logger.info("Payload2 release confirmed and flag set")
        return True
