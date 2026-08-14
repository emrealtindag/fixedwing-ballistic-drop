"""scandium.mavlink.payload_controller

Payload drop servo controller using MAVLink commands.

This module provides a PayloadReleaseStatus dataclass to track release state
and a PayloadController class that issues MAV_CMD_DO_SET_SERVO commands to
set a servo PWM for dropping payloads. The controller is defensive and will
not resend commands for already-released payloads; it also handles several
common transport interfaces (pymavlink connection, or a project MavlinkTransport
wrapper exposing convenient methods).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import time
import logging

# MAVLink command id for setting a servo output
MAV_CMD_DO_SET_SERVO = 183

logger = logging.getLogger(__name__)


@dataclass
class PayloadReleaseStatus:
    """Status of payload releases.

    Attributes
    ----------
    payload1_released: bool
        True if payload 1 has been released.
    payload2_released: bool
        True if payload 2 has been released.
    last_release_timestamp: float
        Unix timestamp (seconds) of the last release event, 0.0 if none.
    total_released_count: int
        Total number of releases performed.
    """

    payload1_released: bool = False
    payload2_released: bool = False
    last_release_timestamp: float = 0.0
    total_released_count: int = 0


class PayloadController:
    """Controller to command servo outputs for payload release via MAVLink.

    The controller accepts either a raw pymavlink connection or a project-specific
    MavlinkTransport wrapper. It will attempt to use common interfaces found on
    such objects to send a MAV_CMD_DO_SET_SERVO command or call convenience
    methods if available.

    Parameters
    ----------
    mav_transport: Any
        MAVLink transport object. Expected to be one of:
          - a pymavlink connection where `.mav.command_long_send` is available
          - an object exposing `.command_long_send` directly
          - a wrapper exposing `.set_servo(servo_channel, pwm)` or `.set_servo_pwm(...)`
    servo_channel: int
        Servo channel (servo number) to command (default: 9).
    pwm_payload_1: int
        PWM value to send to release payload 1 (default: 1500).
    pwm_payload_2: int
        PWM value to send to release payload 2 (default: 2000).
    """

    def __init__(
        self,
        mav_transport: Any,
        servo_channel: int = 9,
        pwm_payload_1: int = 1500,
        pwm_payload_2: int = 2000,
    ) -> None:
        self.transport = mav_transport
        self.servo_channel = int(servo_channel)
        self.pwm_payload_1 = int(pwm_payload_1)
        self.pwm_payload_2 = int(pwm_payload_2)
        self._status = PayloadReleaseStatus()

    @property
    def status(self) -> PayloadReleaseStatus:
        """Current release status snapshot."""
        return self._status

    def _send_set_servo(self, pwm: int) -> bool:
        """Send MAV_CMD_DO_SET_SERVO to the vehicle using available transport APIs.

        Attempts multiple common interfaces and logs detailed errors. Returns
        True if a send was attempted without raising an exception (note that
        this does not guarantee the vehicle executed the command).
        """
        # Defensive checks
        pwm_val = int(pwm)

        # 1) Try pymavlink-style connection with .mav.command_long_send
        try:
            mavobj = getattr(self.transport, "mav", None)
            if mavobj is not None and hasattr(mavobj, "command_long_send"):
                # Determine target system/component if provided on transport
                target_system = getattr(self.transport, "target_system", 1)
                target_component = getattr(self.transport, "target_component", 1)
                # command_long_send(target_system, target_component, command, confirmation, p1..p7)
                mavobj.command_long_send(
                    int(target_system),
                    int(target_component),
                    MAV_CMD_DO_SET_SERVO,
                    0,  # confirmation
                    int(self.servo_channel),
                    pwm_val,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                logger.debug("Sent MAV_CMD_DO_SET_SERVO via transport.mav.command_long_send: channel=%s pwm=%s",
                             self.servo_channel, pwm_val)
                return True
        except Exception as exc:  # pragma: no cover - transport dependent
            logger.exception("Failed sending set_servo via transport.mav.command_long_send: %s", exc)

        # 2) Try direct command_long_send on the transport (some wrappers expose it)
        try:
            if hasattr(self.transport, "command_long_send"):
                # signature expected: command_long_send(target_system, target_component, command, confirmation, p1..p7)
                target_system = getattr(self.transport, "target_system", 1)
                target_component = getattr(self.transport, "target_component", 1)
                self.transport.command_long_send(
                    int(target_system),
                    int(target_component),
                    MAV_CMD_DO_SET_SERVO,
                    0,
                    int(self.servo_channel),
                    pwm_val,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                logger.debug("Sent MAV_CMD_DO_SET_SERVO via transport.command_long_send: channel=%s pwm=%s",
                             self.servo_channel, pwm_val)
                return True
        except Exception as exc:  # pragma: no cover - transport dependent
            logger.exception("Failed sending set_servo via transport.command_long_send: %s", exc)

        # 3) Try convenience methods often provided by wrappers
        try:
            if hasattr(self.transport, "set_servo"):
                # set_servo(channel, pwm)
                self.transport.set_servo(int(self.servo_channel), pwm_val)
                logger.debug("Sent set_servo via transport.set_servo: channel=%s pwm=%s",
                             self.servo_channel, pwm_val)
                return True
            if hasattr(self.transport, "set_servo_pwm"):
                # set_servo_pwm(channel, pwm)
                self.transport.set_servo_pwm(int(self.servo_channel), pwm_val)
                logger.debug("Sent set_servo via transport.set_servo_pwm: channel=%s pwm=%s",
                             self.servo_channel, pwm_val)
                return True
        except Exception as exc:  # pragma: no cover - transport dependent
            logger.exception("Failed sending set_servo via convenience method: %s", exc)

        # 4) If no supported interface found, log and return False
        logger.error(
            "No supported MAVLink send interface found on transport to set servo (channel=%s pwm=%s)",
            self.servo_channel,
            pwm_val,
        )
        return False

    def release_payload_1(self) -> bool:
        """Release payload 1 by commanding the servo to pwm_payload_1.

        Returns True on successful command send and state update, False otherwise.
        This method is idempotent: if payload1_released is already True it will
        not resend the command.
        """
        if self._status.payload1_released:
            logger.info("Attempted to release payload 1 but it was already released.")
            return False

        try:
            ok = self._send_set_servo(self.pwm_payload_1)
            if not ok:
                logger.error("Failed to send release command for payload 1 (transport error)")
                return False

            # Update status
            self._status.payload1_released = True
            self._status.last_release_timestamp = time.time()
            self._status.total_released_count += 1
            logger.info("Payload 1 released: channel=%s pwm=%s", self.servo_channel, self.pwm_payload_1)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Exception while releasing payload 1: %s", exc)
            return False

    def release_payload_2(self) -> bool:
        """Release payload 2 by commanding the servo to pwm_payload_2.

        Returns True on successful command send and state update, False otherwise.
        Idempotent: will not resend if payload2_released already True.
        """
        if self._status.payload2_released:
            logger.info("Attempted to release payload 2 but it was already released.")
            return False

        try:
            ok = self._send_set_servo(self.pwm_payload_2)
            if not ok:
                logger.error("Failed to send release command for payload 2 (transport error)")
                return False

            # Update status
            self._status.payload2_released = True
            self._status.last_release_timestamp = time.time()
            self._status.total_released_count += 1
            logger.info("Payload 2 released: channel=%s pwm=%s", self.servo_channel, self.pwm_payload_2)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Exception while releasing payload 2: %s", exc)
            return False

    def reset_mechanism(self) -> bool:
        """Reset the servo/mechanism to a safe locked PWM (1000).

        Returns True if a reset command was sent, False otherwise.
        Note: this does not modify payload1/2 released flags; it only commands the
        servo to a lock position. Use with caution if hardware state requires
        resetting flags as well.
        """
        try:
            ok = self._send_set_servo(1000)
            if not ok:
                logger.error("Failed to send reset servo command (transport error)")
                return False
            logger.info("Sent reset servo command to PWM=1000 on channel %s", self.servo_channel)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Exception while resetting mechanism: %s", exc)
            return False
