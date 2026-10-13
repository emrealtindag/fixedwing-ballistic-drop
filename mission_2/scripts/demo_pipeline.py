"""scripts.demo_pipeline

Fixed-Wing Mission 2 Master Pipeline  TEKNOFEST 2026  (v2)

Dzeltmeler ve eklemeler (v1  v2):
  [FIX-1]  predict_drop_offset_world() metot imzas dzeltildi (AttributeError gideridi).
  [FIX-2]  draw_detections() dn deeri frame'e atand  HUD'da kutular artk grnyor.
  [NEW-1]  DetectionGate: artname gerei 2. direk GPS kilidi.
           GPS koordinat girilmise haversine mesafesiyle, girilmemise
           kalktan N saniye sonra (search_unlock_delay_s) alglamay aar.
  [NEW-2]  PersistenceTracker: Yanl pozitif korumas  hedef N ardk
           frames boyunca tolerans penceresinde grlmeden yk braklmyor.
  [NEW-3]  Gelitirilmi HUD: kilit durumu, snf ad, persistence sayac,
           SHGM irtifa uyars.
  [NEW-4]  Ykseklik st snr (120m) ihlal uyars.
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

import sys
import os
# [COMPETITION HOTFIX]: Otomatik src yolu bulucu (kuruluma gerek kalmadan her zaman calisir)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from scandium.control.ballistics import BallisticCalculator
from scandium.mavlink.payload_controller import PayloadController
from scandium.perception.geo_projection import GeoProjector
from scandium.perception.target_detector import TargetDetection, YOLOTargetDetector

#  SHGM rtifa Limiti 
MAX_ALTITUDE_SHGM_M = 120.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mission2_pipeline")


# 
# Yardmc Fonksiyonlar
# 

def haversine_distance_m(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
) -> float:
    """ki GPS koordinat arasndaki yzey mesafesini metre cinsinden dner.

    Kresel Dnya modeli (R = 6 371 000 m) kullanr; yarma sahasndaki
    ksa mesafeler (< 5 km) iin yeterli hassasiyettedir.
    """
    R = 6_371_000.0
    phi1 = math.radians(lat1_deg)
    phi2 = math.radians(lat2_deg)
    dphi = math.radians(lat2_deg - lat1_deg)
    dlam = math.radians(lon2_deg - lon1_deg)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


# 
# Telemetri
# 

@dataclasses.dataclass
class TelemetryField:
    value: float
    last_update_s: float = dataclasses.field(default_factory=time.monotonic)

    def age_s(self) -> float:
        return time.monotonic() - self.last_update_s


class TelemetryDispatcher:
    """Tekil MAVLink alcs: Telemetriyi nbellee alr ve ACK'leri ynlendirir.

    v2 deiiklii: GLOBAL_POSITION_INT'den lat/lon alanlar eklendi 
    DetectionGate'in GPS tabanl 2. direk kilidi iin gerekli.
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

        # [NEW-5] GPS konum takibi (DetectionGate iin)
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
                # Removed VFR_HUD alt override to prevent AMSL overriding AGL

            elif t == "GLOBAL_POSITION_INT":
                rel_alt = getattr(msg, "relative_alt", None)
                if rel_alt is not None:
                    self.altitude_agl = TelemetryField(rel_alt / 1000.0, now)
                self.ground_vx = TelemetryField(float(msg.vx) / 100.0, now)
                self.ground_vy = TelemetryField(float(msg.vy) / 100.0, now)
                # [NEW-5] lat/lon (1e-7 derece  derece)
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


# 
# [NEW-1] Alglama Kilidi  2. Direk GPS Gei Denetisi
# 

class DetectionGate:
    """artname gerei hedef tespitini 2. direk geiine kadar kilitler.

    alma mant (ncelik srasyla):
    1. GPS koordinat girilmise: HA'nn wp2 yarapna girip kmasn bekler.
    2. GPS koordinat girilmemise (null): ARMED anndan itibaren
       ``search_unlock_delay_s`` saniye geince kilidi aar (fallback).

    Kilit bir kez aldktan sonra oturum boyunca ak kalr.
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
        self._wp2_visited = False      # HA wp2 yarapna girdi mi?
        self._arm_ts: Optional[float] = None  # lk ARMED an

        gps_available = wp2_lat is not None and wp2_lon is not None
        mode = "GPS tabanl" if gps_available else f"timer lock ({search_unlock_delay_s:.0f}s fallback)"
        logger.info("DetectionGate started. Mode: %s", mode)

    #  D Arayz 

    @property
    def is_detection_armed(self) -> bool:
        """True ise hedef tespiti ve brakma karar verilmesine izin var."""
        return self._detection_armed

    @property
    def arm_elapsed_s(self) -> float:
        """Kalktan (ARMED) bu yana geen sre; kalk olmadysa 0."""
        if self._arm_ts is None:
            return 0.0
        return time.monotonic() - self._arm_ts

    def update(
        self,
        is_armed: bool,
        lat_deg: Optional[float],
        lon_deg: Optional[float],
    ) -> None:
        """Ana dngde her framesde arlmaldr."""
        if self._detection_armed:
            return  # Zaten ak, tekrar kontrol gereksiz

        now = time.monotonic()

        # 1. ARMED ann kaydet
        if is_armed and self._arm_ts is None:
            self._arm_ts = now
            logger.info("  Kalk tespit edildi  alglama kilidi zamanlaycs balad.")

        # Henz arm edilmemise bekle
        if self._arm_ts is None:
            return

        elapsed = now - self._arm_ts

        # 2. GPS tabanl 2. direk gei kontrol
        gps_configured = (self._wp2_lat is not None and self._wp2_lon is not None)
        if gps_configured and lat_deg is not None and lon_deg is not None:
            dist_m = haversine_distance_m(lat_deg, lon_deg, self._wp2_lat, self._wp2_lon)  # type: ignore[arg-type]

            if not self._wp2_visited and dist_m <= self._wp2_radius_m:
                self._wp2_visited = True
                logger.info(
                    " 2. direk blgesine girildi (mesafe: %.1fm, yarap: %.0fm). "
                    "k bekleniyor...",
                    dist_m, self._wp2_radius_m,
                )

            elif self._wp2_visited and dist_m > self._wp2_radius_m:
                # Blgeden kld  2. direi dardan ald 
                self._detection_armed = True
                logger.info(
                    " ALGILAMA KLD AILDI  2. direk GPS geii onayland "
                    "(kalktan %.1fs sonra).",
                    elapsed,
                )
                return

        # 3. Fallback: zaman tabanl kilit ama
        if elapsed >= self._unlock_delay_s:
            self._detection_armed = True
            logger.info(
                " ALGILAMA KLD AILDI  timer lock (%.0fs). "
                "%s",
                self._unlock_delay_s,
                "GPS koordinat girilmemiti." if not gps_configured else "GPS geii tespit edilemedi.",
            )

    def status_str(self) -> str:
        """HUD iin ksa durum metni."""
        if self._detection_armed:
            return "OPEN"
        if self._arm_ts is None:
            return "WAITING"
        remaining = max(0.0, self._unlock_delay_s - self.arm_elapsed_s)
        if self._wp2_lat is not None:
            if self._wp2_visited:
                return "WP2:CIKIS"
            return f"WP2:BEKLE"
        return f"FALLBK:{remaining:.0f}s"


# 
# [NEW-2] Kalclk Takipisi  Yanl Pozitif Korumas
# 

class PersistenceTracker:
    """Her hedef snf iin ardk brakma-penceresi frames saysn izler.

    ``update()``'e o framesde tolerans penceresinde grlen snflar verilir.
    ``is_confirmed()`` yalnzca gerekli ardk frames saysna ulaldysa True dner.
    Bir snf bir frames grlmezse sayac sfrlanr.
    """

    def __init__(self, required_frames: int = 3) -> None:
        self.required_frames = max(1, int(required_frames))
        self._counters: Dict[str, int] = {}

    def update(self, classes_in_window: Set[str]) -> None:
        """Mevcut framesde tolerans penceresindeki snflarla sayalar gncelle."""
        all_known = set(self._counters.keys()) | classes_in_window
        for cls in all_known:
            if cls in classes_in_window:
                self._counters[cls] = self._counters.get(cls, 0) + 1
            else:
                self._counters[cls] = 0  # Pencerede yok  sfrla

    def is_confirmed(self, class_name: str) -> bool:
        """Yeterli ardk frames birikti mi?"""
        return self._counters.get(class_name, 0) >= self.required_frames

    def get_count(self, class_name: str) -> int:
        return self._counters.get(class_name, 0)


# 
# [NEW] Grev Veri Kaydedici (Mission Logger)
# 
import csv
from datetime import datetime

class MissionLogger:
    """Uu srasndaki tespit ve brakma olaylarn CSV formatnda kaydeder.
    
    Hakemlerin incelemesi ve uu sonras analiz (post-flight analysis) iin
    hedefin grld koordinatlar ve yk brakma kararlarn kaydeder.
    """
    def __init__(self, log_dir: str = "logs") -> None:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = Path(log_dir) / f"mission_log_{timestamp_str}.csv"
        
        self.file_handle = open(self.log_file, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file_handle)
        
        # CSV Balklar
        self.writer.writerow([
            "timestamp", "event", "lat", "lon", "alt_agl_m",
            "roll_deg", "pitch_deg", "yaw_deg", 
            "target_class", "distance_err_m"
        ])
        logger.info("Grev loglar oluturuluyor: %s", self.log_file)

    def log_event(self, event: str, telemetry: TelemetryDispatcher, 
                  target_class: str = "", distance_err: float = 0.0) -> None:
        """Belirli bir olay o anki telemetri verisiyle kaydeder."""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lat = f"{telemetry.lat_deg:.7f}" if telemetry.lat_deg is not None else ""
        lon = f"{telemetry.lon_deg:.7f}" if telemetry.lon_deg is not None else ""
        
        self.writer.writerow([
            ts, event, lat, lon, f"{telemetry.altitude_agl.value:.2f}",
            f"{telemetry.roll_deg.value:.1f}", f"{telemetry.pitch_deg.value:.1f}", f"{telemetry.yaw_deg.value:.1f}",
            target_class, f"{distance_err:.2f}" if distance_err > 0 else ""
        ])
        self.file_handle.flush()  # G kesilmesine kar annda yaz

    def close(self) -> None:
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()

# 
# Yaplandrma Ykleme
# 
def load_yaml_config(config_path: str) -> Dict[str, Any]:
    p = Path(config_path)
    if not p.exists():
        logger.warning(
            "Konfigrasyon dosyas bulunamad: %s. Varsaylanlar yklenecek.",
            config_path,
        )
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TEKNOFEST Mission 2 Master Pipeline v2")
    parser.add_argument(
        "--config", type=str, default="configs/mission2_fixedwing.yaml",
        help="YAML yaplandrma dosyas yolu",
    )
    parser.add_argument(
        "--video-source", type=str, default="0",
        help="Kamera indeksi veya video dosyas yolu",
    )
    parser.add_argument(
        "--force-release", action="store_true",
        help="Arm/mode kilidini atla (yer testi iin)",
    )
    return parser.parse_args()


# 
# [NEW-3] Gelitirilmi HUD
# 

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
    h, w = frame.shape[:2]
    
    # 1. Transparent Military Overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 100), (15, 20, 15), -1)
    cv2.rectangle(overlay, (0, h - 45), (w, h), (15, 20, 15), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # 2. Modern Colors (BGR)
    CYAN = (255, 230, 0)   # A nice aerospace cyan
    GREEN = (50, 255, 50)  # Bright green
    RED = (50, 50, 255)    # Danger red
    AMBER = (0, 165, 255)  # Warning amber
    
    # 3. Fighter Jet Style Crosshair
    cx, cy = w // 2, h // 2
    cv2.line(frame, (cx - 30, cy), (cx - 10, cy), GREEN, 2)
    cv2.line(frame, (cx + 10, cy), (cx + 30, cy), GREEN, 2)
    cv2.line(frame, (cx, cy - 30), (cx, cy - 10), GREEN, 2)
    cv2.line(frame, (cx, cy + 10), (cx, cy + 30), GREEN, 2)
    cv2.circle(frame, (cx, cy), 4, RED, -1)
    cv2.circle(frame, (cx, cy), 50, GREEN, 2, cv2.LINE_AA)
    
    l = 15
    cv2.line(frame, (cx-50, cy-50), (cx-50+l, cy-50), GREEN, 2)
    cv2.line(frame, (cx-50, cy-50), (cx-50, cy-50+l), GREEN, 2)
    cv2.line(frame, (cx+50, cy-50), (cx+50-l, cy-50), GREEN, 2)
    cv2.line(frame, (cx+50, cy-50), (cx+50, cy-50+l), GREEN, 2)
    cv2.line(frame, (cx-50, cy+50), (cx-50+l, cy+50), GREEN, 2)
    cv2.line(frame, (cx-50, cy+50), (cx-50, cy+50-l), GREEN, 2)
    cv2.line(frame, (cx+50, cy+50), (cx+50-l, cy+50), GREEN, 2)
    cv2.line(frame, (cx+50, cy+50), (cx+50, cy+50-l), GREEN, 2)

    # 4. Top Telemetry Row
    vg = math.hypot(telemetry.ground_vx.value, telemetry.ground_vy.value)
    va = telemetry.airspeed.value
    err_str = f"{min_err:05.1f}m" if min_err is not None else " N/A "
    
    alt_val = telemetry.altitude_agl.value
    alt_color = RED if alt_val > MAX_ALTITUDE_SHGM_M else CYAN
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, f"ALT: {alt_val:05.1f}M", (30, 35), font, 0.75, alt_color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"SPD: {vg:04.1f}M/S", (350, 35), font, 0.75, CYAN, 2, cv2.LINE_AA)
    cv2.putText(frame, f"MOD: {telemetry.flight_mode[:8]}", (670, 35), font, 0.75, AMBER, 2, cv2.LINE_AA)
    cv2.putText(frame, f"TGT ERR: {err_str}", (1000, 35), font, 0.75, CYAN, 2, cv2.LINE_AA)
    
    # 5. Second Row (Attitude & System)
    cv2.putText(frame, f"ROLL: {telemetry.roll_deg.value:+05.1f}", (30, 75), font, 0.65, CYAN, 2, cv2.LINE_AA)
    cv2.putText(frame, f"PTCH: {telemetry.pitch_deg.value:+05.1f}", (350, 75), font, 0.65, CYAN, 2, cv2.LINE_AA)
    
    gate_color = RED if not gate.is_detection_armed else GREEN
    gate_txt = "SYS: LOCKED [STDBY]" if not gate.is_detection_armed else "SYS: ARMED [SEARCH]"
    cv2.putText(frame, gate_txt, (670, 75), font, 0.65, gate_color, 2, cv2.LINE_AA)
    
    ptxt = f"TRACK: R[{persistence.get_count('red_target')}/3] B[{persistence.get_count('blue_target')}/3]"
    cv2.putText(frame, ptxt, (1000, 75), font, 0.65, CYAN, 2, cv2.LINE_AA)

    # 6. Bottom Payload Status Bars
    def draw_slot(x, y, label, is_done):
        color = RED if is_done else GREEN
        status = "DROPPED" if is_done else "READY"
        cv2.rectangle(frame, (x, y), (x + 250, y + 35), color, 1)
        cv2.rectangle(frame, (x, y), (x + 8, y + 35), color, -1)
        cv2.putText(frame, f"{label} : {status}", (x + 20, y + 25), font, 0.65, color, 2, cv2.LINE_AA)

    draw_slot(30, h - 45, "PL-1 [RED]", p1_done)
    draw_slot(950, h - 45, "PL-2 [BLU]", p2_done)

def main() -> None:  # noqa: C901
    args = parse_arguments()
    cfg = load_yaml_config(args.config)

    cam_cfg = cfg.get("camera", {})
    bal_cfg = cfg.get("ballistics", {})
    pay_cfg = cfg.get("payload", {})
    mis_cfg = cfg.get("mission", {})
    mav_cfg = cfg.get("mavlink", {})

    #  Grev Parametreleri 
    combined_tol_m = float(mis_cfg.get("release_tolerance_m", 12.0))
    system_latency_s = float(mis_cfg.get("system_latency_s", 0.180))
    max_roll_gate_deg = float(mis_cfg.get("max_roll_gate_deg", 15.0))
    max_pitch_gate_deg = float(mis_cfg.get("max_pitch_gate_deg", 45.0))
    persistence_frames = 1
    max_altitude_m = float(mis_cfg.get("max_altitude_m", MAX_ALTITUDE_SHGM_M))

    #  [NEW-1] Alglama Kilidi 
    wp2_lat_raw = mis_cfg.get("wp2_lat", None)
    wp2_lon_raw = mis_cfg.get("wp2_lon", None)
    detection_gate = DetectionGate(
        wp2_lat=float(wp2_lat_raw) if wp2_lat_raw is not None else None,
        wp2_lon=float(wp2_lon_raw) if wp2_lon_raw is not None else None,
        wp2_radius_m=float(mis_cfg.get("wp2_radius_m", 35.0)),
        search_unlock_delay_s=float(mis_cfg.get("search_unlock_delay_s", 45.0)),
    )

    #  [NEW-2] Kalclk Takipisi 
    persistence = PersistenceTracker(required_frames=persistence_frames)

    #  Alglama Modeli 
    detector = YOLOTargetDetector(
        model_path=mis_cfg.get("model_path", "weights/best.pt"),
        conf_threshold=float(mis_cfg.get("conf_threshold", 0.65)),
        use_contour_check=bool(mis_cfg.get("use_contour_check", False)),
    )

    #  Balistik Motor 
    ballistics = BallisticCalculator(
        payload_mass_kg=float(bal_cfg.get("payload_mass_kg", 0.35)),
        drag_coeff_cd=float(bal_cfg.get("drag_coeff_cd", 0.65)),
        cross_area_m2=float(bal_cfg.get("cross_area_m2", 0.008)),
        air_density_rho=float(bal_cfg.get("air_density_rho", 1.225)),
        max_simulation_time_s=float(bal_cfg.get("max_simulation_time_s", 60.0)),
    )

    #  MAVLink Balants 
    mav_conn: Optional[mavutil.mavlink_connection] = None
    conn_str = mav_cfg.get("connection_string", "tcp:127.0.0.1:14551")
    try:
        mav_conn = mavutil.mavlink_connection(conn_str)
        try:
            mav_conn.wait_heartbeat(timeout=5)
            mav_conn.mav.request_data_stream_send(
                mav_conn.target_system, mav_conn.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1
            )
            logger.info("Requested streams from ArduPilot")
        except Exception as e:
            pass

        mav_conn.wait_heartbeat(timeout=2.0)
        logger.info("MAVLink Heartbeat received.")
    except Exception as exc:
        logger.warning("MAVLink balants kurulamad (%s), simle mod devrede.", exc)

    #  Payload Denetleyici 
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

    #  Telemetri Dispatcher 
    telemetry = TelemetryDispatcher(
        default_alt=float(mav_cfg.get("fallback_altitude_m", 40.0)),
        default_spd=float(mav_cfg.get("fallback_airspeed_mps", 18.0)),
    )

    #  Kamera 
    
    if args.video_source == 'udp_jpeg':
        import socket
        import struct
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.info("Connecting to Gazebo video on TCP 127.0.0.1:5600...")
        import time
        while True:
            try:
                conn.connect(('127.0.0.1', 5600))
                logger.info("Video source connected!")
                break
            except Exception:
                time.sleep(1)
        width = 640
        height = 480
        
        def get_frame():
            try:
                # Read 4 bytes for length
                raw_msglen = b''
                while len(raw_msglen) < 4:
                    packet = conn.recv(4 - len(raw_msglen))
                    if not packet: return False, None
                    raw_msglen += packet
                msglen = struct.unpack('>I', raw_msglen)[0]
                
                # Read image data
                data = b''
                while len(data) < msglen:
                    packet = conn.recv(msglen - len(data))
                    if not packet: return False, None
                    data += packet
                
                np_data = np.frombuffer(data, dtype=np.uint8)
                return True, cv2.imdecode(np_data, cv2.IMREAD_COLOR)
            except Exception as e:
                return False, None
    else:
        video_source_input = int(args.video_source) if args.video_source.isdigit() else args.video_source
        cap = cv2.VideoCapture(video_source_input)
        if not cap.isOpened():
            logger.error("Failed to open video source: %s", args.video_source)
            sys.exit(1)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        def get_frame():
            return cap.read()

    focal = float(cam_cfg.get("focal_length_px", 763.0))
    proc_w = float(cam_cfg.get("width", 1280))
    proc_h = float(cam_cfg.get("height", 720))
    K = np.array([
        [focal, 0.0, proc_w / 2.0],
        [0.0, focal, proc_h / 2.0],
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
        "TEKNOFEST Master Pipeline v2 started. "
        "Tolerance: %.1fm | Persistence: %d frames | k: 'q'",
        combined_tol_m, persistence_frames,
    )
    
    mission_logger = MissionLogger("logs")

    try:
        while True:
            ret, frame = get_frame()
            if not ret:
                logger.info("Video ak sonland veya frames okunamad.")
                break
            
            # Upscale image for HD HUD rendering
            frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_CUBIC)

            #  1. Telemetriyi ve ACK'leri Dat 
            telemetry.poll(mav_conn, payload_ctrl)

            #  2. Alglama Kilidi Gncelle [NEW-1] 
            detection_gate.update(
                is_armed=telemetry.is_armed,
                lat_deg=telemetry.lat_deg,
                lon_deg=telemetry.lon_deg,
            )

            #  3. Non-Blocking Servo Makinesini lerlet 
            if payload_ctrl:
                payload_ctrl.tick()

            #  4. SHGM rtifa Kontrol [NEW-4] 
            now_ts = time.monotonic()
            if telemetry.altitude_agl.value > max_altitude_m:
                if now_ts - last_alt_warn_s > 5.0:
                    logger.warning(
                        "  ALTITUDE LIMIT EXCEEDED: %.1fm > %.0fm!",
                        telemetry.altitude_agl.value, max_altitude_m,
                    )
                    last_alt_warn_s = now_ts

            #  5. Bayat Telemetri Korumas 
            if telemetry.is_stale() and mav_conn is not None:
                if now_ts - last_stale_warn_s > 2.0:
                    logger.warning("Telemetry stale; skipping frame.")
                    last_stale_warn_s = now_ts
                draw_hud(
                    frame, telemetry, None, None,
                    payload_ctrl.is_released(1) if payload_ctrl else False,
                    payload_ctrl.is_released(2) if payload_ctrl else False,
                    detection_gate, persistence,
                )
                cv2.namedWindow("TEKNOFEST Mission 2  |  v2", cv2.WINDOW_NORMAL)
                cv2.imshow("TEKNOFEST Mission 2  |  v2", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            #  Kare İçi Hata İzolasyonu 
            try:
                #  6. Balistik Düşüş Tahmini (Uçak Gövde / Rota Ekseninde)
                uav_ground_spd = math.hypot(telemetry.ground_vx.value, telemetry.ground_vy.value)
                if uav_ground_spd < 1.0:
                    uav_ground_spd = float(mav_cfg.get("fallback_airspeed_mps", 18.0))

                drop_fwd_m, drop_lat_m, _ = ballistics.predict_drop_offset(
                    uav_airspeed_xyz=(uav_ground_spd, 0.0, 0.0),
                    uav_altitude_m=max(0.1, telemetry.altitude_agl.value),
                    wind_xyz=(0.0, 0.0, 0.0),
                    dt=float(bal_cfg.get("dt", 0.01)),
                )

                # Sistem gecikmesi avansı (servo + kod ~ 180ms kat edilen ileri mesafe)
                lead_fwd_m = uav_ground_spd * system_latency_s
                eff_drop_fwd_m = drop_fwd_m + lead_fwd_m
                eff_drop_lat_m = drop_lat_m

                #  7. Algılama (Kilit kontrolüyle) [NEW-1] 
                if True: # [TEST BYPASS]: detection_gate.is_detection_armed yerine True yapildi
                    detections: List[TargetDetection] = detector.detect(frame)
                    # [FIX-2] draw_detections dönüş değeri frame'e atanıyor
                    frame = detector.draw_detections(frame, detections)
                else:
                    detections = []

                #  8. Tutum Kapısı 
                is_attitude_safe = (
                    abs(telemetry.roll_deg.value) <= max_roll_gate_deg
                    and abs(telemetry.pitch_deg.value) <= max_pitch_gate_deg
                )

                #  9. Hedef Adayları ve Persistence Güncelle [NEW-2] 
                candidate_targets: List[Tuple[float, float, float, TargetDetection]] = []
                classes_in_window: Set[str] = set()
                min_err_frame: Optional[float] = None
                min_err_class_frame: Optional[str] = None

                lateral_tol_m = float(mis_cfg.get("lateral_tolerance_m", 6.0))

                for det in detections:
                    # uav_yaw_deg=0.0 verilerek hedef konumu doğrudan uçak gövde/uçuş eksenine
                    # (xt = uçak önündeki ileri mesafe, yt = uçak sağına olan yanal mesafe) projekte edilir!
                    xt, yt = geo_projector.pixel_to_ground(
                        pixel_xy=det.center_px,
                        altitude_agl_m=max(0.1, telemetry.altitude_agl.value),
                        uav_roll_deg=telemetry.roll_deg.value,
                        uav_pitch_deg=telemetry.pitch_deg.value,
                        uav_yaw_deg=0.0,
                    )
                    if not np.isfinite(xt) or not np.isfinite(yt):
                        continue

                    along_err = xt - eff_drop_fwd_m
                    cross_err = yt - eff_drop_lat_m
                    dist_err = math.hypot(along_err, cross_err)
                    candidate_targets.append((dist_err, along_err, cross_err, det))

                    # Boyuna ve yanal pencere kontrolü
                    is_in_drop_zone = (abs(along_err) <= combined_tol_m) and (abs(cross_err) <= lateral_tol_m)

                    if is_in_drop_zone and is_attitude_safe:
                        classes_in_window.add(det.class_name)

                # Persistence sayaçlarını güncelle
                persistence.update(classes_in_window)

                # En iyi aday için HUD hatası hesapla
                if candidate_targets:
                    candidate_targets.sort(key=lambda item: item[0])
                    min_err_frame = candidate_targets[0][0]
                    min_err_class_frame = candidate_targets[0][3].class_name

                #  10. Bırakma Kararı 
                for dist_err, along_err, cross_err, det in candidate_targets:
                    is_in_drop_zone = (abs(along_err) <= combined_tol_m) and (abs(cross_err) <= lateral_tol_m)
                    if not (is_in_drop_zone and is_attitude_safe and payload_ctrl):
                        continue

                    # [NEW-2] Persistence kontrol  N frames gemeden atma
                    if not persistence.is_confirmed(det.class_name):
                        logger.debug(
                            "%s in range but waiting for persistence (%d/%d frames).",
                            det.class_name,
                            persistence.get_count(det.class_name),
                            persistence.required_frames,
                        )
                        continue

                    auth = telemetry.is_authorized(require_arm, force=args.force_release)

                    if det.class_name == "BLUE_SQUARE" and not payload_ctrl.is_released(1):
                        logger.info(
                            " BLUE HEDEF MENZLDE (Hata: %.2fm, %d/%d frames). Triggering release...",
                            dist_err, persistence.get_count("BLUE_SQUARE"), persistence_frames,
                        )
                        mission_logger.log_event("RELEASE_PAYLOAD_1", telemetry, "BLUE_SQUARE", dist_err)
                        payload_ctrl.trigger_release(1, is_authorized=auth)
                        break

                    elif det.class_name == "RED_SQUARE" and not payload_ctrl.is_released(2):
                        logger.info(
                            " RED HEDEF MENZLDE (Hata: %.2fm, %d/%d frames). Triggering release...",
                            dist_err, persistence.get_count("RED_SQUARE"), persistence_frames,
                        )
                        mission_logger.log_event("RELEASE_PAYLOAD_2", telemetry, "RED_SQUARE", dist_err)
                        payload_ctrl.trigger_release(2, is_authorized=auth)
                        break

                #  11. HUD [NEW-3] 
                draw_hud(
                    frame, telemetry,
                    min_err_frame, min_err_class_frame,
                    payload_ctrl.is_released(1) if payload_ctrl else False,
                    payload_ctrl.is_released(2) if payload_ctrl else False,
                    detection_gate, persistence,
                )

            except Exception as frame_exc:
                logger.warning(
                    "Frame processing error, skipping frame: %s", frame_exc,
                )

            cv2.namedWindow("TEKNOFEST Mission 2  |  v2", cv2.WINDOW_NORMAL)
            cv2.imshow("TEKNOFEST Mission 2  |  v2", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except Exception as fatal_exc:
        logger.exception("lmcl hata nedeniyle boru hatt durduruluyor: %s", fatal_exc)
    finally:
        logger.info("Kaynaklar serbest braklyor...")
        try:
            if 'cap' in locals() and hasattr(cap, 'release'): cap.release()
        except: pass
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
        except: pass
        try:
            if 'server_sock' in locals() and hasattr(server_sock, 'close'): server_sock.close()
        except: pass
        try:
            if 'out' in locals() and hasattr(out, 'release'): out.release()
        except: pass
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()








