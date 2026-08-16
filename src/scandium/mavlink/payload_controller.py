"""scandium.mavlink.payload_controller

Non-blocking, multi-payload servo release controller for MAVLink autopilots.

This module manages payload release mechanisms via MAV_CMD_DO_SET_SERVO.
It enforces strict parameter boundary validations, non-blocking state progression,
slot-isolated status tracking, and single-flight ACK disambiguation.
"""
from __future__ import annotations

import dataclasses
import enum
import logging
import time
from typing import Dict, Optional

from pymavlink import mavutil

# MAVLink command ID for direct servo PWM control
MAV_CMD_DO_SET_SERVO = mavutil.mavlink.MAV_CMD_DO_SET_SERVO

logger = logging.getLogger(__name__)

# Donanımsal Emniyet Aralıkları (Saha ve Pixhawk Standartları)
SERVO_CHANNEL_MIN = 1
SERVO_CHANNEL_MAX = 16
PWM_MIN = 800
PWM_MAX = 2200
DEFAULT_RESET_PWM = 1000


class ReleaseState(enum.Enum):
    """Her yük yuvasının (slot) yaşam döngüsü durumları."""
    IDLE = 0
    AWAITING_ACK = 1
    CONFIRMED = 2
    FAILED = 3


@dataclasses.dataclass
class PayloadSlot:
    """Tekil bir yük bırakma yuvasının durum ve konfigürasyon veri yapısı."""
    payload_id: int
    pwm: int
    state: ReleaseState = ReleaseState.IDLE
    attempt: int = 0
    deadline: float = 0.0
    released: bool = False


class PayloadController:
    """MAVLink üzerinden servo kontrollü çoklu yük bırakma denetleyicisi.

    Parameters
    ----------
    mav_connection : mavutil.mavlink_connection
        Aktif pymavlink bağlantı nesnesi.
    servo_channel : int
        Komut gönderilecek servo çıkış kanalı (1 - 16 arası).
    pwm_payload_1 : int
        1. Yük (Mavi Hedef) için bırakma PWM değeri (800 - 2200 us).
    pwm_payload_2 : int
        2. Yük (Kırmızı Hedef) için bırakma PWM değeri (800 - 2200 us).
    ack_retries : int
        COMMAND_ACK gelmediğinde yapılacak maksimum yeniden deneme sayısı.
    ack_timeout_s : float
        Her deneme için ACK bekleme zaman aşımı süresi (saniye).
    target_system : int
        Hedef MAVLink sistem kimliği (SysID, varsayılan: 1).
    target_component : int
        Hedef MAVLink bileşen kimliği (CompID, varsayılan: 1).
    """

    def __init__(
        self,
        mav_connection: mavutil.mavlink_connection,
        servo_channel: int = 9,
        pwm_payload_1: int = 1500,
        pwm_payload_2: int = 2000,
        ack_retries: int = 2,
        ack_timeout_s: float = 0.8,
        target_system: int = 1,
        target_component: int = 1,
    ) -> None:
        # 1. Servo Kanalı Sınır Doğrulaması
        self.servo_channel = int(servo_channel)
        if not (SERVO_CHANNEL_MIN <= self.servo_channel <= SERVO_CHANNEL_MAX):
            raise ValueError(
                f"Geçersiz servo_channel: {self.servo_channel}. "
                f"Değer {SERVO_CHANNEL_MIN} ile {SERVO_CHANNEL_MAX} arasında olmalıdır."
            )

        # 2. PWM Sınır Doğrulamaları
        pwm_p1 = self._validate_pwm(pwm_payload_1, "pwm_payload_1")
        pwm_p2 = self._validate_pwm(pwm_payload_2, "pwm_payload_2")

        self.mav_connection = mav_connection
        self.ack_retries = max(0, int(ack_retries))
        self.ack_timeout_s = float(ack_timeout_s)
        self.target_system = int(target_system)
        self.target_component = int(target_component)

        # Bağımsız yük yuvaları (Birbirini asla kilitlemez)
        self.slots: Dict[int, PayloadSlot] = {
            1: PayloadSlot(payload_id=1, pwm=pwm_p1),
            2: PayloadSlot(payload_id=2, pwm=pwm_p2),
        }

    def _validate_pwm(self, pwm: int, param_name: str = "PWM") -> int:
        """PWM değerinin güvenli sınırlar içinde olduğunu denetler."""
        val = int(pwm)
        if not (PWM_MIN <= val <= PWM_MAX):
            raise ValueError(
                f"Geçersiz {param_name}: {val} us. "
                f"Değer {PWM_MIN} ile {PWM_MAX} us arasında olmalıdır."
            )
        return val

    def _send_set_servo(self, pwm: int) -> bool:
        """MAVLink MAV_CMD_DO_SET_SERVO komutunu otopilota iletir."""
        try:
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                int(MAV_CMD_DO_SET_SERVO),
                0,
                float(self.servo_channel),
                float(pwm),
                0.0, 0.0, 0.0, 0.0, 0.0,
            )
            logger.info("Sent DO_SET_SERVO: Kanal=%s PWM=%s", self.servo_channel, pwm)
            return True
        except Exception as exc:
            logger.error("DO_SET_SERVO gönderim hatası: %s", exc)
            return False

    def trigger_release(self, payload_id: int, is_authorized: bool) -> bool:
        """Yük bırakma sürecini non-blocking başlatır.

        Parameters
        ----------
        payload_id : int
            Bırakılacak yük numarası (1 veya 2).
        is_authorized : bool
            Uçuş modu (AUTO/GUIDED) ve ARMED güvenlik yetki durumu.
        """
        # ACK Çakışma Önleyici (Single-Flight Gate): Halihazırda onay bekleyen varsa sıraya al
        if any(s.state == ReleaseState.AWAITING_ACK for s in self.slots.values()):
            return False

        slot = self.slots.get(payload_id)
        if not slot or slot.released or slot.state == ReleaseState.AWAITING_ACK:
            return False

        if not is_authorized:
            logger.warning("Yük %d tetikleme reddedildi: Uçuş modu / ARMED yetkisi yok.", payload_id)
            slot.state = ReleaseState.FAILED
            return False

        slot.attempt = 1
        slot.deadline = time.monotonic() + self.ack_timeout_s
        slot.state = ReleaseState.AWAITING_ACK
        self._send_set_servo(slot.pwm)
        return True

    def handle_command_ack(self, msg) -> None:
        """TelemetryDispatcher tarafından yakalanan COMMAND_ACK mesajını işler."""
        try:
            cmd = int(getattr(msg, "command", -1))
            res = int(getattr(msg, "result", -1))
            src_sys = getattr(msg, "get_srcSystem", lambda: getattr(msg, "sysid", None))()
            src_comp = getattr(msg, "get_srcComponent", lambda: getattr(msg, "compid", None))()
        except Exception:
            return

        if cmd != int(MAV_CMD_DO_SET_SERVO):
            return

        # Hedef otopilot kaynak doğrulaması
        if src_sys is not None and int(src_sys) != self.target_system:
            return
        if src_comp is not None and int(src_comp) != self.target_component:
            return

        for slot in self.slots.values():
            if slot.state == ReleaseState.AWAITING_ACK:
                if res == 0:  # MAV_RESULT_ACCEPTED
                    slot.released = True
                    slot.state = ReleaseState.CONFIRMED
                    logger.info("🎯 Yük %d başarıyla bırakıldı (Otopilot COMMAND_ACK onayladı).", slot.payload_id)
                else:
                    logger.warning("Yük %d için gelen ACK reddedildi (Result=%s).", slot.payload_id, res)
                    slot.state = ReleaseState.FAILED

    def tick(self) -> None:
        """Ana döngüde her karede çağrılan zaman aşımı ve yeniden deneme yöneticisi."""
        now = time.monotonic()
        for slot in self.slots.values():
            if slot.state == ReleaseState.AWAITING_ACK and now >= slot.deadline:
                if slot.attempt < (self.ack_retries + 1):
                    slot.attempt += 1
                    logger.warning("Yük %d ACK zaman aşımı. %d. deneme basılıyor...", slot.payload_id, slot.attempt)
                    self._send_set_servo(slot.pwm)
                    slot.deadline = now + self.ack_timeout_s
                else:
                    logger.error("Yük %d bırakma başarısız: Maksimum deneme tükendi.", slot.payload_id)
                    slot.state = ReleaseState.FAILED

    def is_released(self, payload_id: int) -> bool:
        """Belirtilen yükün başarıyla bırakılıp bırakılmadığını döner."""
        slot = self.slots.get(payload_id)
        return slot.released if slot else False

    def reset_mechanism(self, reset_pwm: int = DEFAULT_RESET_PWM) -> bool:
        """Servoyu kilitli başlangıç konumuna (varsayılan: 1000 us) çeker."""
        valid_pwm = self._validate_pwm(reset_pwm, "reset_pwm")
        return self._send_set_servo(valid_pwm)
