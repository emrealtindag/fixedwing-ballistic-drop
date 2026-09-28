"""scripts.demo_pipeline

Fixed-Wing Mission 2 Master Pipeline â€” TEKNOFEST 2026  (v2)

DÃ¼zeltmeler ve eklemeler (v1 â†’ v2):
  [FIX-1]  predict_drop_offset_world() metot imzasÄ± dÃ¼zeltildi (AttributeError gideridi).
  [FIX-2]  draw_detections() dÃ¶nÃ¼ÅŸ deÄŸeri frame'e atandÄ± â€” HUD'da kutular artÄ±k gÃ¶rÃ¼nÃ¼yor.
  [NEW-1]  DetectionGate: Åartname gereÄŸi 2. direk GPS kilidi.
           GPS koordinatÄ± girilmiÅŸse haversine mesafesiyle, girilmemiÅŸse
           kalkÄ±ÅŸtan N saniye sonra (search_unlock_delay_s) algÄ±lamayÄ± aÃ§ar.
  [NEW-2]  PersistenceTracker: YanlÄ±ÅŸ pozitif korumasÄ± â€” hedef N ardÄ±ÅŸÄ±k
           kare boyunca tolerans penceresinde gÃ¶rÃ¼lmeden yÃ¼k bÄ±rakÄ±lmÄ±yor.
  [NEW-3]  GeliÅŸtirilmiÅŸ HUD: kilit durumu, sÄ±nÄ±f adÄ±, persistence sayacÄ±,
           SHGM irtifa uyarÄ±sÄ±.
  [NEW-4]  YÃ¼kseklik Ã¼st sÄ±nÄ±rÄ± (120m) ihlal uyarÄ±sÄ±.
  [NEW-5]  TelemetryDispatcher: GLOBAL_POSITION_INT'den lat/lon takibi eklendi.
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
import yaml
from pymavlink import mavutil

from scandium.control.ballistics import BallisticCalculator
from scandium.mavlink.payload_controller import PayloadController
from scandium.perception.geo_projection import GeoProjector
from scandium.perception.target_detector import TargetDetection, YOLOTargetDetector

# â”€â”€ SHGM Ä°rtifa Limiti â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MAX_ALTITUDE_SHGM_M = 120.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mission2_pipeline")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# YardÄ±mcÄ± Fonksiyonlar
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def haversine_distance_m(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
) -> float:
    """Ä°ki GPS koordinatÄ± arasÄ±ndaki yÃ¼zey mesafesini metre cinsinden dÃ¶ner.

    KÃ¼resel DÃ¼nya modeli (R = 6 371 000 m) kullanÄ±r; yarÄ±ÅŸma sahasÄ±ndaki
    kÄ±sa mesafeler (< 5 km) iÃ§in yeterli hassasiyettedir.
    """
    R = 6_371_000.0
    phi1 = math.radians(lat1_deg)
    phi2 = math.radians(lat2_deg)
    dphi = math.radians(lat2_deg - lat1_deg)
    dlam = math.radians(lon2_deg - lon1_deg)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Telemetri
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclasses.dataclass
class TelemetryField:
    value: float
    last_update_s: float = dataclasses.field(default_factory=time.monotonic)

    def age_s(self) -> float:
        return time.monotonic() - self.last_update_s


class TelemetryDispatcher:
    """Tekil MAVLink alÄ±cÄ±sÄ±: Telemetriyi Ã¶nbelleÄŸe alÄ±r ve ACK'leri yÃ¶nlendirir.

    v2 deÄŸiÅŸikliÄŸi: GLOBAL_POSITION_INT'den lat/lon alanlarÄ± eklendi â€”
    DetectionGate'in GPS tabanlÄ± 2. direk kilidi iÃ§in gerekli.
    """

    def __init__(
        self,
        default_alt: float = 40.0,
        default_spd: float = 18.0,
        max_age_s: float = 1.0,
    ) -> None:
        now = time.monotonic()
        self.altitude_agl = TelemetryField(default_alt, now)
        self.airspeed = TelemetryField(default_spd, now)
        self.ground_vx = TelemetryField(default_spd, now)
        self.ground_vy = TelemetryField(0.0, now)
        self.roll_deg = TelemetryField(0.0, now)
        self.pitch_deg = TelemetryField(0.0, now)
        self.yaw_deg = TelemetryField(0.0, now)
        self.wind_xyz: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.wind_ts = now

        # [NEW-5] GPS konum takibi (DetectionGate iÃ§in)
        self.lat_deg: Optional[float] = None
        self.lon_deg: Optional[float] = None

        self.is_armed = False
        self.flight_mode = "UNKNOWN"
        self.heartbeat_ts = 0.0
        self.max_age_s = float(max_age_s)

    def poll(
        self,
        mav_conn: Optional[mavutil.mavlink_connection],
        payload_ctrl: Optional[PayloadController],
    ) -> None:
        if mav_conn is None:
            return
        now = time.monotonic()
        while True:
            msg = mav_conn.recv_match(blocking=False)
            if msg is None:
                break
            t = msg.get_type()

            if t == "HEARTBEAT":
                self.heartbeat_ts = now
                base_mode = int(getattr(msg, "base_mode", 0))
                self.is_armed = (base_mode & 0x80) != 0
                mode_str = mavutil.mode_string_v10(msg)
                if mode_str:
                    self.flight_mode = mode_str

            elif t == "COMMAND_ACK" and payload_ctrl is not None:
                payload_ctrl.handle_command_ack(msg)

            elif t == "VFR_HUD":
                self.airspeed = TelemetryField(float(getattr(msg, "airspeed", self.airspeed.value)), now)
                self.altitude_agl = TelemetryField(float(getattr(msg, "alt", self.altitude_agl.value)), now)

            elif t == "GLOBAL_POSITION_INT":
                rel_alt = getattr(msg, "relative_alt", None)
                if rel_alt is not None:
                    self.altitude_agl = TelemetryField(rel_alt / 1000.0, now)
                self.ground_vx = TelemetryField(float(msg.vx) / 100.0, now)
                self.ground_vy = TelemetryField(float(msg.vy) / 100.0, now)
                # [NEW-5] lat/lon (1e-7 derece â†’ derece)
                raw_lat = getattr(msg, "lat", None)
                raw_lon = getattr(msg, "lon", None)
                if raw_lat is not None:
                    self.lat_deg = float(raw_lat) / 1e7
                if raw_lon is not None:
                    self.lon_deg = float(raw_lon) / 1e7

            elif t == "ATTITUDE":
                self.roll_deg = TelemetryField(math.degrees(float(msg.roll)), now)
                self.pitch_deg = TelemetryField(math.degrees(float(msg.pitch)), now)
                self.yaw_deg = TelemetryField(math.degrees(float(msg.yaw)), now)

            elif t == "WIND":
                w_spd = float(getattr(msg, "speed", 0.0))
                w_dir = math.radians(float(getattr(msg, "direction", 0.0)))
                self.wind_xyz = (w_spd * math.cos(w_dir), w_spd * math.sin(w_dir), 0.0)
                self.wind_ts = now

    def is_stale(self) -> bool:
        return max(
            self.roll_deg.age_s(),
            self.pitch_deg.age_s(),
            self.yaw_deg.age_s(),
            self.altitude_agl.age_s(),
            self.ground_vx.age_s(),
            self.ground_vy.age_s(),
        ) > self.max_age_s

    def is_authorized(self, require_arming: bool, force: bool = False) -> bool:
        if force:
            return True
        if (time.monotonic() - self.heartbeat_ts) > 2.5:
            return False
        if require_arming and not self.is_armed:
            return False
        if self.flight_mode not in {"AUTO", "GUIDED"}:
            return False
        return True


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# [NEW-1] AlgÄ±lama Kilidi â€” 2. Direk GPS GeÃ§iÅŸ DenetÃ§isi
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class DetectionGate:
    """Åartname gereÄŸi hedef tespitini 2. direk geÃ§iÅŸine kadar kilitler.

    Ã‡alÄ±ÅŸma mantÄ±ÄŸÄ± (Ã¶ncelik sÄ±rasÄ±yla):
    1. GPS koordinatÄ± girilmiÅŸse: Ä°HA'nÄ±n wp2 yarÄ±Ã§apÄ±na girip Ã§Ä±kmasÄ±nÄ± bekler.
    2. GPS koordinatÄ± girilmemiÅŸse (null): ARMED anÄ±ndan itibaren
       ``search_unlock_delay_s`` saniye geÃ§ince kilidi aÃ§ar (fallback).

    Kilit bir kez aÃ§Ä±ldÄ±ktan sonra oturum boyunca aÃ§Ä±k kalÄ±r.
    """

    def __init__(
        self,
        wp2_lat: Optional[float],
        wp2_lon: Optional[float],
        wp2_radius_m: float = 35.0,
        search_unlock_delay_s: float = 45.0,
    ) -> None:
        self._wp2_lat = wp2_lat
        self._wp2_lon = wp2_lon
        self._wp2_radius_m = float(wp2_radius_m)
        self._unlock_delay_s = float(search_unlock_delay_s)

        self._detection_armed = False
        self._wp2_visited = False      # Ä°HA wp2 yarÄ±Ã§apÄ±na girdi mi?
        self._arm_ts: Optional[float] = None  # Ä°lk ARMED anÄ±

        gps_available = wp2_lat is not None and wp2_lon is not None
        mode = "GPS tabanlÄ±" if gps_available else f"zaman kilidi ({search_unlock_delay_s:.0f}s fallback)"
        logger.info("DetectionGate baÅŸlatÄ±ldÄ±. Mod: %s", mode)

    # â”€â”€ DÄ±ÅŸ ArayÃ¼z â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @property
    def is_detection_armed(self) -> bool:
        """True ise hedef tespiti ve bÄ±rakma kararÄ± verilmesine izin var."""
        return self._detection_armed

    @property
    def arm_elapsed_s(self) -> float:
        """KalkÄ±ÅŸtan (ARMED) bu yana geÃ§en sÃ¼re; kalkÄ±ÅŸ olmadÄ±ysa 0."""
        if self._arm_ts is None:
            return 0.0
        return time.monotonic() - self._arm_ts

    def update(
        self,
        is_armed: bool,
        lat_deg: Optional[float],
        lon_deg: Optional[float],
    ) -> None:
        """Ana dÃ¶ngÃ¼de her karede Ã§aÄŸrÄ±lmalÄ±dÄ±r."""
        if self._detection_armed:
            return  # Zaten aÃ§Ä±k, tekrar kontrol gereksiz

        now = time.monotonic()

        # 1. ARMED anÄ±nÄ± kaydet
        if is_armed and self._arm_ts is None:
            self._arm_ts = now
            logger.info("â±ï¸  KalkÄ±ÅŸ tespit edildi â€” algÄ±lama kilidi zamanlayÄ±cÄ±sÄ± baÅŸladÄ±.")

        # HenÃ¼z arm edilmemiÅŸse bekle
        if self._arm_ts is None:
            return

        elapsed = now - self._arm_ts

        # 2. GPS tabanlÄ± 2. direk geÃ§iÅŸ kontrolÃ¼
        gps_configured = (self._wp2_lat is not None and self._wp2_lon is not None)
        if gps_configured and lat_deg is not None and lon_deg is not None:
            dist_m = haversine_distance_m(lat_deg, lon_deg, self._wp2_lat, self._wp2_lon)  # type: ignore[arg-type]

            if not self._wp2_visited and dist_m <= self._wp2_radius_m:
                self._wp2_visited = True
                logger.info(
                    "ğŸ“ 2. direk bÃ¶lgesine girildi (mesafe: %.1fm, yarÄ±Ã§ap: %.0fm). "
                    "Ã‡Ä±kÄ±ÅŸ bekleniyor...",
                    dist_m, self._wp2_radius_m,
                )

            elif self._wp2_visited and dist_m > self._wp2_radius_m:
                # BÃ¶lgeden Ã§Ä±kÄ±ldÄ± â†’ 2. direÄŸi dÄ±ÅŸarÄ±dan aldÄ± âœ…
                self._detection_armed = True
                logger.info(
                    "ğŸ”“ ALGILAMA KÄ°LÄ°DÄ° AÃ‡ILDI â€” 2. direk GPS geÃ§iÅŸi onaylandÄ± "
                    "(kalkÄ±ÅŸtan %.1fs sonra).",
                    elapsed,
                )
                return

        # 3. Fallback: zaman tabanlÄ± kilit aÃ§ma
        if elapsed >= self._unlock_delay_s:
            self._detection_armed = True
            logger.info(
                "ğŸ”“ ALGILAMA KÄ°LÄ°DÄ° AÃ‡ILDI â€” zaman kilidi (%.0fs). "
                "%s",
                self._unlock_delay_s,
                "GPS koordinatÄ± girilmemiÅŸti." if not gps_configured else "GPS geÃ§iÅŸi tespit edilemedi.",
            )

    def status_str(self) -> str:
        """HUD iÃ§in kÄ±sa durum metni."""
        if self._detection_armed:
            return "ACIK"
        if self._arm_ts is None:
            return "BEKLIYOR"
        remaining = max(0.0, self._unlock_delay_s - self.arm_elapsed_s)
        if self._wp2_lat is not None:
            if self._wp2_visited:
                return "WP2:CIKIS"
            return f"WP2:BEKLE"
        return f"FALLBK:{remaining:.0f}s"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# [NEW-2] KalÄ±cÄ±lÄ±k TakipÃ§isi â€” YanlÄ±ÅŸ Pozitif KorumasÄ±
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class PersistenceTracker:
    """Her hedef sÄ±nÄ±fÄ± iÃ§in ardÄ±ÅŸÄ±k bÄ±rakma-penceresi kare sayÄ±sÄ±nÄ± izler.

    ``update()``'e o karede tolerans penceresinde gÃ¶rÃ¼len sÄ±nÄ±flar verilir.
    ``is_confirmed()`` yalnÄ±zca gerekli ardÄ±ÅŸÄ±k kare sayÄ±sÄ±na ulaÅŸÄ±ldÄ±ysa True dÃ¶ner.
    Bir sÄ±nÄ±f bir kare gÃ¶rÃ¼lmezse sayacÄ± sÄ±fÄ±rlanÄ±r.
    """

    def __init__(self, required_frames: int = 3) -> None:
        self.required_frames = max(1, int(required_frames))
        self._counters: Dict[str, int] = {}

    def update(self, classes_in_window: Set[str]) -> None:
        """Mevcut karede tolerans penceresindeki sÄ±nÄ±flarla sayaÃ§larÄ± gÃ¼ncelle."""
        all_known = set(self._counters.keys()) | classes_in_window
        for cls in all_known:
            if cls in classes_in_window:
                self._counters[cls] = self._counters.get(cls, 0) + 1
            else:
                self._counters[cls] = 0  # Pencerede yok â†’ sÄ±fÄ±rla

    def is_confirmed(self, class_name: str) -> bool:
        """Yeterli ardÄ±ÅŸÄ±k kare birikti mi?"""
        return self._counters.get(class_name, 0) >= self.required_frames

    def get_count(self, class_name: str) -> int:
        return self._counters.get(class_name, 0)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# [NEW] GÃ¶rev Veri Kaydedici (Mission Logger)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
import csv
from datetime import datetime

class MissionLogger:
    """UÃ§uÅŸ sÄ±rasÄ±ndaki tespit ve bÄ±rakma olaylarÄ±nÄ± CSV formatÄ±nda kaydeder.
    
    Hakemlerin incelemesi ve uÃ§uÅŸ sonrasÄ± analiz (post-flight analysis) iÃ§in
    hedefin gÃ¶rÃ¼ldÃ¼ÄŸÃ¼ koordinatlarÄ± ve yÃ¼k bÄ±rakma kararlarÄ±nÄ± kaydeder.
    """
    def __init__(self, log_dir: str = "logs") -> None:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = Path(log_dir) / f"mission_log_{timestamp_str}.csv"
        
        self.file_handle = open(self.log_file, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file_handle)
        
        # CSV BaÅŸlÄ±klarÄ±
        self.writer.writerow([
            "timestamp", "event", "lat", "lon", "alt_agl_m",
            "roll_deg", "pitch_deg", "yaw_deg", 
            "target_class", "distance_err_m"
        ])
        logger.info("GÃ¶rev loglarÄ± oluÅŸturuluyor: %s", self.log_file)

    def log_event(self, event: str, telemetry: TelemetryDispatcher, 
                  target_class: str = "", distance_err: float = 0.0) -> None:
        """Belirli bir olayÄ± o anki telemetri verisiyle kaydeder."""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lat = f"{telemetry.lat_deg:.7f}" if telemetry.lat_deg is not None else ""
        lon = f"{telemetry.lon_deg:.7f}" if telemetry.lon_deg is not None else ""
        
        self.writer.writerow([
            ts, event, lat, lon, f"{telemetry.altitude_agl.value:.2f}",
            f"{telemetry.roll_deg.value:.1f}", f"{telemetry.pitch_deg.value:.1f}", f"{telemetry.yaw_deg.value:.1f}",
            target_class, f"{distance_err:.2f}" if distance_err > 0 else ""
        ])
        self.file_handle.flush()  # GÃ¼Ã§ kesilmesine karÅŸÄ± anÄ±nda yaz

    def close(self) -> None:
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# YapÄ±landÄ±rma YÃ¼kleme
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def load_yaml_config(config_path: str) -> Dict[str, Any]:
    p = Path(config_path)
    if not p.exists():
        logger.warning(
            "KonfigÃ¼rasyon dosyasÄ± bulunamadÄ±: %s. VarsayÄ±lanlar yÃ¼klenecek.",
            config_path,
        )
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TEKNOFEST Mission 2 Master Pipeline v2")
    parser.add_argument(
        "--config", type=str, default="configs/mission2_fixedwing.yaml",
        help="YAML yapÄ±landÄ±rma dosyasÄ± yolu",
    )
    parser.add_argument(
        "--video-source", type=str, default="0",
        help="Kamera indeksi veya video dosyasÄ± yolu",
    )
    parser.add_argument(
        "--force-release", action="store_true",
        help="Arm/mode kilidini atla (yer testi iÃ§in)",
    )
    return parser.parse_args()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# [NEW-3] GeliÅŸtirilmiÅŸ HUD
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def draw_hud(
    frame: np.ndarray,
    telemetry: TelemetryDispatcher,
    min_err: Optional[float],
    min_err_class: Optional[str],
    p1_done: bool,
    p2_done: bool,
    gate: DetectionGate,
    persistence: PersistenceTracker,
) -> None:
    """Kare Ã¼zerine telemetri + gÃ¶rev HUD'u Ã§izer (in-place)."""
    h, w = frame.shape[:2]

    # â”€â”€ SatÄ±r 1: UÃ§uÅŸ Telemetrisi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cv2.rectangle(frame, (0, 0), (w, 44), (20, 20, 20), -1)
    vg = math.hypot(telemetry.ground_vx.value, telemetry.ground_vy.value)
    va = telemetry.airspeed.value
    err_str = f"{min_err:5.1f}m" if min_err is not None else "  N/A "
    cls_str = f"[{min_err_class}]" if min_err_class else ""

    # SHGM irtifa uyarÄ±sÄ±
    alt_color = (0, 60, 220) if telemetry.altitude_agl.value > MAX_ALTITUDE_SHGM_M else (0, 255, 255)
    alt_warn = " âš SHGM!" if telemetry.altitude_agl.value > MAX_ALTITUDE_SHGM_M else ""

    hud_line1 = (
        f"ALT:{telemetry.altitude_agl.value:5.1f}m{alt_warn} | "
        f"VG:{vg:4.1f} VA:{va:4.1f} m/s | "
        f"MODE:{telemetry.flight_mode} | "
        f"ERR:{err_str} {cls_str}"
    )
    cv2.putText(frame, hud_line1, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.48, alt_color, 1, cv2.LINE_AA)

    # â”€â”€ SatÄ±r 2: Kilit Durumu + Persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cv2.rectangle(frame, (0, 44), (w, 82), (10, 10, 35), -1)

    gate_color = (0, 220, 0) if gate.is_detection_armed else (0, 80, 220)
    gate_label = f"GATE:{gate.status_str()}"
    cv2.putText(frame, gate_label, (10, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.50, gate_color, 1, cv2.LINE_AA)

    p_req = persistence.required_frames
    p1_cnt = persistence.get_count("BLUE_SQUARE")
    p2_cnt = persistence.get_count("RED_SQUARE")
    persist_label = (
        f"PERSIST  MAVÄ°:{p1_cnt}/{p_req}  KIRMIZI:{p2_cnt}/{p_req} | "
        f"ROLL:{telemetry.roll_deg.value:+5.1f}Â°  PITCH:{telemetry.pitch_deg.value:+5.1f}Â°"
    )
    cv2.putText(frame, persist_label, (200, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (180, 180, 255), 1, cv2.LINE_AA)

    # â”€â”€ YÃ¼k Durum KutularÄ± (saÄŸ Ã¼st) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    for slot_idx, (label, done, cnt, max_cnt) in enumerate([
        ("P1 MAVÄ°â†’KIRMIZI YÃœK", p1_done, p1_cnt, p_req),
        ("P2 KIRMIZIâ†’MAVÄ° YÃœK", p2_done, p2_cnt, p_req),
    ]):
        y0 = 50 + slot_idx * 32
        y1 = y0 + 26
        box_color = (0, 180, 0) if done else (0, 0, 200)
        cv2.rectangle(frame, (w - 215, y0), (w - 5, y1), box_color, -1)
        status = "ATILDI âœ“" if done else f"HAZIR [{cnt}/{max_cnt}]"
        cv2.putText(
            frame, f"{label}: {status}",
            (w - 210, y0 + 17),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA,
        )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Ana DÃ¶ngÃ¼
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def main() -> None:  # noqa: C901
    args = parse_arguments()
    cfg = load_yaml_config(args.config)

    cam_cfg = cfg.get("camera", {})
    bal_cfg = cfg.get("ballistics", {})
    pay_cfg = cfg.get("payload", {})
    mis_cfg = cfg.get("mission", {})
    mav_cfg = cfg.get("mavlink", {})

    # â”€â”€ GÃ¶rev Parametreleri â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    combined_tol_m = float(mis_cfg.get("release_tolerance_m", 12.0))
    system_latency_s = float(mis_cfg.get("system_latency_s", 0.180))
    max_roll_gate_deg = float(mis_cfg.get("max_roll_gate_deg", 15.0))
    max_pitch_gate_deg = float(mis_cfg.get("max_pitch_gate_deg", 10.0))
    persistence_frames = int(mis_cfg.get("persistence_frames", 3))
    max_altitude_m = float(mis_cfg.get("max_altitude_m", MAX_ALTITUDE_SHGM_M))

    # â”€â”€ [NEW-1] AlgÄ±lama Kilidi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    wp2_lat_raw = mis_cfg.get("wp2_lat", None)
    wp2_lon_raw = mis_cfg.get("wp2_lon", None)
    detection_gate = DetectionGate(
        wp2_lat=float(wp2_lat_raw) if wp2_lat_raw is not None else None,
        wp2_lon=float(wp2_lon_raw) if wp2_lon_raw is not None else None,
        wp2_radius_m=float(mis_cfg.get("wp2_radius_m", 35.0)),
        search_unlock_delay_s=float(mis_cfg.get("search_unlock_delay_s", 45.0)),
    )

    # â”€â”€ [NEW-2] KalÄ±cÄ±lÄ±k TakipÃ§isi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    persistence = PersistenceTracker(required_frames=persistence_frames)

    # â”€â”€ AlgÄ±lama Modeli â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    detector = YOLOTargetDetector(
        model_path=mis_cfg.get("model_path", "weights/best.pt"),
        conf_threshold=float(mis_cfg.get("conf_threshold", 0.65)),
        use_contour_check=bool(mis_cfg.get("use_contour_check", False)),
    )

    # â”€â”€ Balistik Motor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ballistics = BallisticCalculator(
        payload_mass_kg=float(bal_cfg.get("payload_mass_kg", 0.35)),
        drag_coeff_cd=float(bal_cfg.get("drag_coeff_cd", 0.45)),
        cross_area_m2=float(bal_cfg.get("cross_area_m2", 0.008)),
        air_density_rho=float(bal_cfg.get("air_density_rho", 1.225)),
        max_simulation_time_s=float(bal_cfg.get("max_simulation_time_s", 60.0)),
    )

    # â”€â”€ MAVLink BaÄŸlantÄ±sÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    mav_conn: Optional[mavutil.mavlink_connection] = None
    conn_str = mav_cfg.get("connection_string", "udp:127.0.0.1:14551")
    try:
        mav_conn = mavutil.mavlink_connection(conn_str)
        mav_conn.wait_heartbeat(timeout=2.0)
        logger.info("MAVLink Heartbeat alÄ±ndÄ±.")
    except Exception as exc:
        logger.warning("MAVLink baÄŸlantÄ±sÄ± kurulamadÄ± (%s), simÃ¼le mod devrede.", exc)

    # â”€â”€ Payload Denetleyici â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    payload_ctrl: Optional[PayloadController] = None
    if mav_conn:
        payload_ctrl = PayloadController(
            mav_connection=mav_conn,
            servo_channel=int(pay_cfg.get("servo_channel", 9)),
            pwm_payload_1=int(pay_cfg.get("pwm_payload_1", 1500)),
            pwm_payload_2=int(pay_cfg.get("pwm_payload_2", 2000)),
            ack_retries=int(pay_cfg.get("ack_retries", 2)),
            ack_timeout_s=float(pay_cfg.get("ack_timeout_s", 0.8)),
            target_system=int(pay_cfg.get("target_system", 1)),
            target_component=int(pay_cfg.get("target_component", 1)),
        )

    # â”€â”€ Telemetri Dispatcher â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    telemetry = TelemetryDispatcher(
        default_alt=float(mav_cfg.get("fallback_altitude_m", 40.0)),
        default_spd=float(mav_cfg.get("fallback_airspeed_mps", 18.0)),
    )

    # â”€â”€ Kamera â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    video_source_input = (
        int(args.video_source) if args.video_source.isdigit() else args.video_source
    )
    cap = cv2.VideoCapture(video_source_input)
    if not cap.isOpened():
        logger.error("Video kaynaÄŸÄ± aÃ§Ä±lamadÄ±: %s", args.video_source)
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    focal = float(cam_cfg.get("focal_length_px", 1000.0))
    K = np.array([
        [focal, 0.0, width / 2.0],
        [0.0, focal, height / 2.0],
        [0.0, 0.0, 1.0],
    ])
    geo_projector = GeoProjector(
        camera_matrix=K,
        dist_coeffs=np.array(cam_cfg.get("dist_coeffs", [0.0, 0.0, 0.0, 0.0, 0.0])),
        mount_pitch_deg=float(cam_cfg.get("mount_pitch_deg", 25.0)),
        mount_roll_deg=float(cam_cfg.get("mount_roll_deg", 0.0)),
    )

    require_arm = bool(pay_cfg.get("require_arming", True))
    last_stale_warn_s = 0.0
    last_alt_warn_s = 0.0

    logger.info(
        "TEKNOFEST Master Pipeline v2 baÅŸladÄ±. "
        "Tolerans: %.1fm | Persistence: %d kare | Ã‡Ä±kÄ±ÅŸ: 'q'",
        combined_tol_m, persistence_frames,
    )
    
    mission_logger = MissionLogger("logs")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("Video akÄ±ÅŸÄ± sonlandÄ± veya kare okunamadÄ±.")
                break

            # â”€â”€ 1. Telemetriyi ve ACK'leri DaÄŸÄ±t â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            telemetry.poll(mav_conn, payload_ctrl)

            # â”€â”€ 2. AlgÄ±lama Kilidi GÃ¼ncelle [NEW-1] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            detection_gate.update(
                is_armed=telemetry.is_armed,
                lat_deg=telemetry.lat_deg,
                lon_deg=telemetry.lon_deg,
            )

            # â”€â”€ 3. Non-Blocking Servo Makinesini Ä°lerlet â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if payload_ctrl:
                payload_ctrl.tick()

            # â”€â”€ 4. SHGM Ä°rtifa KontrolÃ¼ [NEW-4] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            now_ts = time.monotonic()
            if telemetry.altitude_agl.value > max_altitude_m:
                if now_ts - last_alt_warn_s > 5.0:
                    logger.warning(
                        "âš ï¸  SHGM Ä°RTÄ°FA LÄ°MÄ°TÄ° AÅILDI: %.1fm > %.0fm!",
                        telemetry.altitude_agl.value, max_altitude_m,
                    )
                    last_alt_warn_s = now_ts

            # â”€â”€ 5. Bayat Telemetri KorumasÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if telemetry.is_stale() and mav_conn is not None:
                if now_ts - last_stale_warn_s > 2.0:
                    logger.warning("Telemetri bayat; bu karede atÄ±ÅŸ kararÄ± atlanÄ±yor.")
                    last_stale_warn_s = now_ts
                draw_hud(
                    frame, telemetry, None, None,
                    payload_ctrl.is_released(1) if payload_ctrl else False,
                    payload_ctrl.is_released(2) if payload_ctrl else False,
                    detection_gate, persistence,
                )
                cv2.imshow("TEKNOFEST Mission 2  |  v2", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            # â”€â”€ Kare Ä°Ã§i Hata Ä°zolasyonu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            try:
                # â”€â”€ 6. Balistik DÃ¼ÅŸÃ¼ÅŸ Tahmini [FIX-1] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                # predict_drop_offset_world() artÄ±k ballistics.py'da mevcut.
                impact_x, impact_y, _ = ballistics.predict_drop_offset_world(
                    uav_ground_velocity_xy=(
                        telemetry.ground_vx.value,
                        telemetry.ground_vy.value,
                    ),
                    uav_altitude_m=telemetry.altitude_agl.value,
                    wind_xyz=telemetry.wind_xyz,
                    dt=float(bal_cfg.get("dt", 0.01)),
                )

                # Sistem gecikmesi avansÄ± (servo + kod ~ 180ms)
                lead_x = telemetry.ground_vx.value * system_latency_s
                lead_y = telemetry.ground_vy.value * system_latency_s
                eff_impact_x = impact_x + lead_x
                eff_impact_y = impact_y + lead_y

                # â”€â”€ 7. AlgÄ±lama (Kilit kontrolÃ¼yle) [NEW-1] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                if detection_gate.is_detection_armed:
                    detections: List[TargetDetection] = detector.detect(frame)
                    # [FIX-2] draw_detections dÃ¶nÃ¼ÅŸ deÄŸeri frame'e atanÄ±yor
                    frame = detector.draw_detections(frame, detections)
                else:
                    detections = []

                # â”€â”€ 8. Tutum KapÄ±sÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                is_attitude_safe = (
                    abs(telemetry.roll_deg.value) <= max_roll_gate_deg
                    and abs(telemetry.pitch_deg.value) <= max_pitch_gate_deg
                )

                # â”€â”€ 9. Hedef AdaylarÄ± ve Persistence GÃ¼ncelle [NEW-2] â”€â”€â”€â”€â”€â”€â”€â”€â”€
                candidate_targets: List[Tuple[float, TargetDetection]] = []
                classes_in_window: Set[str] = set()
                min_err_frame: Optional[float] = None
                min_err_class_frame: Optional[str] = None

                for det in detections:
                    xt, yt = geo_projector.pixel_to_ground(
                        pixel_xy=det.center_px,
                        altitude_agl_m=telemetry.altitude_agl.value,
                        uav_roll_deg=telemetry.roll_deg.value,
                        uav_pitch_deg=telemetry.pitch_deg.value,
                        uav_yaw_deg=telemetry.yaw_deg.value,
                    )
                    if not np.isfinite(xt) or not np.isfinite(yt):
                        continue

                    lon_err = xt - eff_impact_x
                    lat_err = yt - eff_impact_y
                    dist_err = math.hypot(lon_err, lat_err)
                    candidate_targets.append((dist_err, lon_err, lat_err, det))

                    # [CLAUDE REVIEW FIX]: Dairesel hata yerine Çapraz (Cross-track) ve Boyuna (Along-track) ayri kontrol
                    is_in_drop_zone = abs(lat_err) <= combined_tol_m and -1.5 <= lon_err <= 1.5

                    if is_in_drop_zone and is_attitude_safe:
                        classes_in_window.add(det.class_name)

                # Persistence sayaÃ§larÄ±nÄ± gÃ¼ncelle
                persistence.update(classes_in_window)

                # En iyi aday iÃ§in HUD hatasÄ± hesapla
                if candidate_targets:
                    candidate_targets.sort(key=lambda item: item[0])
                    min_err_frame = candidate_targets[0][0]
                    min_err_class_frame = candidate_targets[0][1].class_name

                # â”€â”€ 10. BÄ±rakma KararÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                for dist_err, lon_err, lat_err, det in candidate_targets:
                    is_in_drop_zone = abs(lat_err) <= combined_tol_m and -1.5 <= lon_err <= 1.5
                    if not (is_in_drop_zone and is_attitude_safe and payload_ctrl):
                        continue

                    # [NEW-2] Persistence kontrolÃ¼ â€” N kare geÃ§meden atma
                    if not persistence.is_confirmed(det.class_name):
                        logger.debug(
                            "%s menzilde ama persistence bekleniyor (%d/%d kare).",
                            det.class_name,
                            persistence.get_count(det.class_name),
                            persistence.required_frames,
                        )
                        continue

                    auth = telemetry.is_authorized(require_arm, force=args.force_release)

                    if det.class_name == "BLUE_SQUARE" and not payload_ctrl.is_released(1):
                        logger.info(
                            "ğŸ¯ MAVÄ° HEDEF MENZÄ°LDE (Hata: %.2fm, %d/%d kare). Tetikleniyor...",
                            dist_err, persistence.get_count("BLUE_SQUARE"), persistence_frames,
                        )
                        mission_logger.log_event("RELEASE_PAYLOAD_1", telemetry, "BLUE_SQUARE", dist_err)
                        payload_ctrl.trigger_release(1, is_authorized=auth)
                        break

                    elif det.class_name == "RED_SQUARE" and not payload_ctrl.is_released(2):
                        logger.info(
                            "ğŸ¯ KIRMIZI HEDEF MENZÄ°LDE (Hata: %.2fm, %d/%d kare). Tetikleniyor...",
                            dist_err, persistence.get_count("RED_SQUARE"), persistence_frames,
                        )
                        mission_logger.log_event("RELEASE_PAYLOAD_2", telemetry, "RED_SQUARE", dist_err)
                        payload_ctrl.trigger_release(2, is_authorized=auth)
                        break

                # â”€â”€ 11. HUD [NEW-3] â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                draw_hud(
                    frame, telemetry,
                    min_err_frame, min_err_class_frame,
                    payload_ctrl.is_released(1) if payload_ctrl else False,
                    payload_ctrl.is_released(2) if payload_ctrl else False,
                    detection_gate, persistence,
                )

            except Exception as frame_exc:
                logger.warning(
                    "Kare iÅŸlenirken geÃ§ici hata oluÅŸtu, kare atlanÄ±yor: %s", frame_exc,
                )

            cv2.imshow("TEKNOFEST Mission 2  |  v2", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except Exception as fatal_exc:
        logger.exception("Ã–lÃ¼mcÃ¼l hata nedeniyle boru hattÄ± durduruluyor: %s", fatal_exc)
    finally:
        logger.info("Kaynaklar serbest bÄ±rakÄ±lÄ±yor...")
        mission_logger.close()
        cap.release()
        cv2.destroyAllWindows()
        if mav_conn:
            try:
                mav_conn.close()
            except Exception:
                pass
        logger.info("Master Pipeline v2 gÃ¼venle kapatÄ±ldÄ±.")


if __name__ == "__main__":
    main()


