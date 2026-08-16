"""scandium.mavlink.payload_controller

Payload drop servo controller using MAVLink commands.

This module provides a PayloadController class that issues MAV_CMD_DO_SET_SERVO
commands to set a servo PWM for dropping payloads. The controller is defensive,
waits for COMMAND_ACK from the autopilot, and prevents duplicate releases.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional, Tuple

from pymavlink import mavutil

# MAVLink command id for setting a servo output
MAV_CMD_DO_SET_SERVO = mavutil.mavlink.MAV_CMD_DO_SET_SERVO

logger = logging.getLogger(__name__)

# Validation ranges
SERVO_CHANNEL_MIN = 1
SERVO_CHANNEL_MAX = 16
PWM_MIN = 800
PWM_MAX = 2200


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
    require_arming: bool
        If True, require vehicle to be armed (by HEARTBEAT base_mode) before sending release commands.
    ack_retries: int
        Number of times to retry sending the command and waiting for an ACK.
    ack_timeout_s: float
        Timeout per ACK wait attempt in seconds.
    target_system: int
        MAVLink target system id to send commands to.
    target_component: int
        MAVLink target component id to send commands to.
    """

    def __init__(
        self,
        mav_connection: mavutil.mavlink_connection,
        servo_channel: int = 9,
        pwm_payload_1: int = 1500,
        pwm_payload_2: int = 2000,
        require_arming: bool = True,
        ack_retries: int = 2,
        ack_timeout_s: float = 1.0,
        target_system: int = 1,
        target_component: int = 1,
    ) -> None:
        # Validate inputs
        servo_channel = int(servo_channel)
        if not (SERVO_CHANNEL_MIN <= servo_channel <= SERVO_CHANNEL_MAX):
            raise ValueError(
                f"servo_channel must be between {SERVO_CHANNEL_MIN} and {SERVO_CHANNEL_MAX}, got {servo_channel}"
            )

        pwm_payload_1 = int(pwm_payload_1)
        pwm_payload_2 = int(pwm_payload_2)
        if not (PWM_MIN <= pwm_payload_1 <= PWM_MAX):
            raise ValueError(f"pwm_payload_1 must be between {PWM_MIN} and {PWM_MAX}, got {pwm_payload_1}")
        if not (PWM_MIN <= pwm_payload_2 <= PWM_MAX):
            raise ValueError(f"pwm_payload_2 must be between {PWM_MIN} and {PWM_MAX}, got {pwm_payload_2}")

        self.mav_connection = mav_connection
        self.servo_channel = servo_channel
        self.pwm_payload_1 = pwm_payload_1
        self.pwm_payload_2 = pwm_payload_2

        # Durum bayrakları (Mükerrer atışı engeller)
        self.payload1_released: bool = False
        self.payload2_released: bool = False

        # Güvenlik ve haberleşme ayarları
        self.require_arming: bool = bool(require_arming)
        self.ack_retries: int = max(0, int(ack_retries))
        self.ack_timeout_s: float = float(ack_timeout_s)
        self.target_system: int = int(target_system)
        self.target_component: int = int(target_component)

        # Thread-safety lock to protect state and MAVLink send/wait sequences
        self._lock = threading.Lock()

        # Track last sent target system/component for ACK source verification
        self._last_tgt_sys: Optional[int] = None
        self._last_tgt_comp: Optional[int] = None

    def _check_armed(self) -> bool:
        """HEARTBEAT base_mode üzerinden aracın ARMED durumunu kontrol eder."""
        MAV_MODE_FLAG_SAFETY_ARMED = getattr(mavutil.mavlink, "MAV_MODE_FLAG_SAFETY_ARMED", 0x80)

        end_time = time.time() + 0.5
        while time.time() < end_time:
            try:
                msg = self.mav_connection.recv_match(type="HEARTBEAT", blocking=False)
            except Exception as exc:
                logger.error("Error receiving HEARTBEAT: %s", exc)
                return False

            if msg is None:
                time.sleep(0.02)
                continue

            try:
                base_mode = int(getattr(msg, "base_mode", 0))
            except Exception:
                logger.warning("Malformed HEARTBEAT message received: %s", msg)
                return False

            armed = (base_mode & int(MAV_MODE_FLAG_SAFETY_ARMED)) != 0
            logger.debug("HEARTBEAT base_mode=%s armed=%s", base_mode, armed)
            return armed

        logger.debug("No HEARTBEAT received to determine armed state; assuming not armed")
        return False

    def _validate_pwm(self, pwm: int) -> None:
        pwm = int(pwm)
        if not (PWM_MIN <= pwm <= PWM_MAX):
            raise ValueError(f"pwm must be between {PWM_MIN} and {PWM_MAX}, got {pwm}")

    def _send_set_servo(self, pwm: int) -> bool:
        """MAVLink üzerinden MAV_CMD_DO_SET_SERVO komutunu basar.

        Ayrıca son gönderilen hedef (system/component) bilgilerini self._last_tgt_*
        olarak saklar; bu bilgi ACK kaynağı doğrulamasında kullanılır.
        """
        self._validate_pwm(pwm)
        try:
            conn_tgt_sys = getattr(self.mav_connection, "target_system", None)
            conn_tgt_comp = getattr(self.mav_connection, "target_component", None)

            tgt_sys = int(self.target_system) if self.target_system is not None else int(conn_tgt_sys or 0)
            tgt_comp = int(self.target_component) if self.target_component is not None else int(conn_tgt_comp or 0)

            # param1 = servo kanalı, param2 = pwm değeri, diğerleri 0.0
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

            # Save last target for subsequent ACK verification
            self._last_tgt_sys = int(tgt_sys)
            self._last_tgt_comp = int(tgt_comp)

            logger.info(
                "Sent MAV_CMD_DO_SET_SERVO: channel=%s pwm=%s (tgt_sys=%s tgt_comp=%s)",
                self.servo_channel,
                pwm,
                tgt_sys,
                tgt_comp,
            )
            return True
        except Exception as exc:
            logger.error("Failed to send MAV_CMD_DO_SET_SERVO: %s", exc)
            return False

    def _extract_msg_source(self, msg) -> Tuple[Optional[int], Optional[int]]:
        """Try multiple common attributes to find source system/component of a message."""
        # Try method-based getters first (pymavlink sometimes exposes these)
        try:
            get_sys = getattr(msg, "get_srcSystem", None)
            get_comp = getattr(msg, "get_srcComponent", None)
            if callable(get_sys):
                src_sys = get_sys()
                src_comp = get_comp() if callable(get_comp) else None
                return (int(src_sys) if src_sys is not None else None, int(src_comp) if src_comp is not None else None)
        except Exception:
            pass

        # Fallback to common attribute names
        src_sys = None
        src_comp = None
        for name in ("srcSystem", "src_system", "sysid", "src_sys", "from_system"):
            v = getattr(msg, name, None)
            if v is not None:
                src_sys = v
                break

        for name in ("srcComponent", "src_component", "compid", "comp_id", "from_component"):
            v = getattr(msg, name, None)
            if v is not None:
                src_comp = v
                break

        try:
            return (int(src_sys) if src_sys is not None else None, int(src_comp) if src_comp is not None else None)
        except Exception:
            return (None, None)

    def _wait_for_ack(self, command_id: int, timeout_s: Optional[float] = None) -> bool:
        """Belirtilen komut için tek denemelik COMMAND_ACK bekler.

        Ek olarak ACK'in kaynağını (src_sys, src_comp) kontrol eder; eğer ACK,
        kendimizin hedeflediği system/component'tan gelmiyorsa paketi atlar ve beklemeye devam eder.
        """
        timeout = float(self.ack_timeout_s if timeout_s is None else timeout_s)
        end_time = time.time() + timeout
        MAV_RESULT_ACCEPTED = mavutil.mavlink.MAV_RESULT_ACCEPTED

        # Capture expected source under lock to avoid races
        with self._lock:
            expected_sys = self._last_tgt_sys
            expected_comp = self._last_tgt_comp

        while time.time() < end_time:
            try:
                msg = self.mav_connection.recv_match(type="COMMAND_ACK", blocking=False)
            except Exception as exc:
                logger.error("Error receiving COMMAND_ACK: %s", exc)
                return False

            if msg is None:
                time.sleep(0.02)
                continue

            try:
                msg_command = int(getattr(msg, "command", -1))
                msg_result = int(getattr(msg, "result", -1))
            except Exception:
                logger.warning("Malformed COMMAND_ACK message received: %s", msg)
                continue

            # If this ACK is for a different command id, skip
            if msg_command != int(command_id):
                continue

            # Extract source system/component and, if expected values are known, verify them
            src_sys, src_comp = self._extract_msg_source(msg)
            if expected_sys is not None and src_sys is not None and int(src_sys) != int(expected_sys):
                logger.debug(
                    "Ignoring COMMAND_ACK for command %s from src_sys=%s (expected %s)", msg_command, src_sys, expected_sys
                )
                # Not from our target; skip/continue waiting
                continue

            if expected_comp is not None and src_comp is not None and int(src_comp) != int(expected_comp):
                logger.debug(
                    "Ignoring COMMAND_ACK for command %s from src_comp=%s (expected %s)",
                    msg_command,
                    src_comp,
                    expected_comp,
                )
                continue

            if msg_result == MAV_RESULT_ACCEPTED:
                logger.info("Received COMMAND_ACK accepted for command %s (src=%s/%s)", command_id, src_sys, src_comp)
                return True

            logger.warning(
                "Received COMMAND_ACK for command %s but result=%s (not accepted) (src=%s/%s)",
                command_id,
                msg_result,
                src_sys,
                src_comp,
            )
            return False

        logger.warning("Timeout waiting for COMMAND_ACK for command %s", command_id)
        return False

    def release_payload_1(self, force: bool = False) -> bool:
        """1. Yükü bırakır (Mavi Hedef / PWM 1500)."""
        with self._lock:
            if self.payload1_released:
                logger.info("release_payload_1 called but payload1 already released; skipping")
                return False

            if not force and self.require_arming and not self._check_armed():
                logger.warning("Vehicle not armed and require_arming=True; release aborted")
                return False

            attempts = max(1, self.ack_retries)
            for attempt in range(1, attempts + 1):
                try:
                    sent = self._send_set_servo(self.pwm_payload_1)
                except ValueError as ve:
                    logger.error("Invalid PWM for payload 1: %s", ve)
                    return False

                if sent and self._wait_for_ack(MAV_CMD_DO_SET_SERVO):
                    self.payload1_released = True
                    logger.info("Payload 1 released and confirmed on attempt %d/%d", attempt, attempts)
                    return True

                if attempt < attempts:
                    logger.warning("Payload 1 release attempt %d failed; retrying in 0.1s...", attempt)
                    # Release lock while sleeping to avoid blocking unrelated callers
                    self._lock.release()
                    try:
                        time.sleep(0.1)
                    finally:
                        # Re-acquire lock to proceed with next attempt
                        self._lock.acquire()

            logger.error("Payload 1 release failed after %d attempts", attempts)
            return False

    def release_payload_2(self, force: bool = False) -> bool:
        """2. Yükü bırakır (Kırmızı Hedef / PWM 2000)."""
        with self._lock:
            if self.payload2_released:
                logger.info("release_payload_2 called but payload2 already released; skipping")
                return False

            if not force and self.require_arming and not self._check_armed():
                logger.warning("Vehicle not armed and require_arming=True; release aborted")
                return False

            attempts = max(1, self.ack_retries)
            for attempt in range(1, attempts + 1):
                try:
                    sent = self._send_set_servo(self.pwm_payload_2)
                except ValueError as ve:
                    logger.error("Invalid PWM for payload 2: %s", ve)
                    return False

                if sent and self._wait_for_ack(MAV_CMD_DO_SET_SERVO):
                    self.payload2_released = True
                    logger.info("Payload 2 released and confirmed on attempt %d/%d", attempt, attempts)
                    return True

                if attempt < attempts:
                    logger.warning("Payload 2 release attempt %d failed; retrying in 0.1s...", attempt)
                    # Release lock while sleeping to avoid blocking unrelated callers
                    self._lock.release()
                    try:
                        time.sleep(0.1)
                    finally:
                        # Re-acquire lock to proceed with next attempt
                        self._lock.acquire()

            logger.error("Payload 2 release failed after %d attempts", attempts)
            return False

    def reset_mechanism(self) -> bool:
        """Servoyu kilitli başlangıç konumuna (PWM 1000) çeker. Artık ACK bekler."""
        pwm = 1000
        try:
            self._validate_pwm(pwm)
        except ValueError as ve:
            logger.error("Invalid PWM for reset_mechanism: %s", ve)
            return False

        with self._lock:
            sent = self._send_set_servo(pwm)
            if not sent:
                logger.error("Failed to send reset command to servo")
                return False

            if self._wait_for_ack(MAV_CMD_DO_SET_SERVO):
                logger.info("Reset mechanism command acknowledged")
                return True

            logger.error("Reset mechanism command not acknowledged")
            return False
