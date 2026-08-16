"""scripts.demo_pipeline

Fixed-Wing Mission 2 Master Pipeline.
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import yaml
from pymavlink import mavutil

from scandium.control.ballistics import BallisticCalculator
from scandium.mavlink.payload_controller import PayloadController
from scandium.perception.geo_projection import GeoProjector
from scandium.perception.target_detector import TargetDetection, YOLOTargetDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mission2_pipeline")


@dataclasses.dataclass
class TelemetryField:
    value: float
    last_update_s: float = dataclasses.field(default_factory=time.monotonic)

    def age_s(self) -> float:
        return time.monotonic() - self.last_update_s


class TelemetryDispatcher:
    """Tekil MAVLink alıcısı: Telemetriyi önbelleğe alır ve ACK'leri yönlendirir."""

    def __init__(self, default_alt: float = 40.0, default_spd: float = 18.0, max_age_s: float = 1.0) -> None:
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

        self.is_armed = False
        self.flight_mode = "UNKNOWN"
        self.heartbeat_ts = 0.0
        self.max_age_s = float(max_age_s)

    def poll(self, mav_conn: Optional[mavutil.mavlink_connection], payload_ctrl: Optional[PayloadController]) -> None:
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


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    p = Path(config_path)
    if not p.exists():
        logger.warning("Konfigürasyon dosyası bulunamadı: %s. Varsayılanlar yüklenecek.", config_path)
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TEKNOFEST Mission 2 Master Pipeline")
    parser.add_argument("--config", type=str, default="configs/mission2_fixedwing.yaml", help="Path to YAML config")
    parser.add_argument("--video-source", type=str, default="0", help="Camera index or video file path")
    parser.add_argument("--force-release", action="store_true", help="Bypass armed/mode lock for ground tests")
    return parser.parse_args()


def draw_hud(
    frame: np.ndarray,
    telemetry: TelemetryDispatcher,
    min_err: Optional[float],
    p1_done: bool,
    p2_done: bool,
) -> None:
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 42), (20, 20, 20), -1)

    vg = math.hypot(telemetry.ground_vx.value, telemetry.ground_vy.value)
    va = telemetry.airspeed.value
    err_str = f"{min_err:4.1f}m" if min_err is not None else "N/A"

    hud_text = (
        f"ALT: {telemetry.altitude_agl.value:4.1f}m | VG: {vg:4.1f}m/s | VA: {va:4.1f}m/s | "
        f"MODE: {telemetry.flight_mode} | MIN_ERR: {err_str}"
    )
    cv2.putText(frame, hud_text, (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 2)

    p1_color = (0, 200, 0) if p1_done else (0, 0, 220)
    p2_color = (0, 200, 0) if p2_done else (0, 0, 220)

    cv2.rectangle(frame, (w - 175, 50), (w - 10, 78), p1_color, -1)
    cv2.putText(frame, f"PAYLOAD 1: {'ATILDI' if p1_done else 'HAZIR'}", (w - 165, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    cv2.rectangle(frame, (w - 175, 86), (w - 10, 114), p2_color, -1)
    cv2.putText(frame, f"PAYLOAD 2: {'ATILDI' if p2_done else 'HAZIR'}", (w - 165, 106), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)


def main() -> None:
    args = parse_arguments()
    cfg = load_yaml_config(args.config)

    cam_cfg = cfg.get("camera", {})
    bal_cfg = cfg.get("ballistics", {})
    pay_cfg = cfg.get("payload", {})
    mis_cfg = cfg.get("mission", {})
    mav_cfg = cfg.get("mavlink", {})

    combined_tol_m = float(mis_cfg.get("release_tolerance_m", 3.0))
    system_latency_s = float(mis_cfg.get("system_latency_s", 0.180))
    max_roll_gate_deg = float(mis_cfg.get("max_roll_gate_deg", 15.0))
    max_pitch_gate_deg = float(mis_cfg.get("max_pitch_gate_deg", 10.0))

    detector = YOLOTargetDetector(
        model_path=mis_cfg.get("model_path", "weights/best.pt"),
        conf_threshold=float(mis_cfg.get("conf_threshold", 0.65)),
        use_contour_check=bool(mis_cfg.get("use_contour_check", False)),
    )
    ballistics = BallisticCalculator(
        payload_mass_kg=float(bal_cfg.get("payload_mass_kg", 0.35)),
        drag_coeff_cd=float(bal_cfg.get("drag_coeff_cd", 0.45)),
        cross_area_m2=float(bal_cfg.get("cross_area_m2", 0.008)),
        air_density_rho=float(bal_cfg.get("air_density_rho", 1.225)),
        dt=float(bal_cfg.get("dt", 0.01)),
        max_simulation_time_s=float(bal_cfg.get("max_simulation_time_s", 60.0)),
    )

    mav_conn: Optional[mavutil.mavlink_connection] = None
    conn_str = mav_cfg.get("connection_string", "udp:127.0.0.1:14551")
    try:
        mav_conn = mavutil.mavlink_connection(conn_str)
        mav_conn.wait_heartbeat(timeout=2.0)
        logger.info("MAVLink Heartbeat alındı.")
    except Exception as exc:
        logger.warning("MAVLink bağlantısı kurulamadı (%s), simüle mod devrede.", exc)

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

    telemetry = TelemetryDispatcher(
        default_alt=float(mav_cfg.get("fallback_altitude_m", 40.0)),
        default_spd=float(mav_cfg.get("fallback_airspeed_mps", 18.0)),
    )

    video_source_input = int(args.video_source) if args.video_source.isdigit() else args.video_source
    cap = cv2.VideoCapture(video_source_input)
    if not cap.isOpened():
        logger.error("Video kaynağı açılamadı: %s", args.video_source)
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    focal = float(cam_cfg.get("focal_length_px", 1000.0))
    K = np.array([[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]])

    geo_projector = GeoProjector(
        camera_matrix=K,
        mount_pitch_deg=float(cam_cfg.get("mount_pitch_deg", 25.0)),
        mount_roll_deg=float(cam_cfg.get("mount_roll_deg", 0.0)),
    )

    require_arm = bool(pay_cfg.get("require_arming", True))
    last_stale_warn_s = 0.0

    logger.info("TEKNOFEST Master Pipeline devrede. Çıkış için 'q' tuşuna basın.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("Video akışı sonlandı veya kare okunamadı.")
                break

            # 1. Telemetriyi ve Gelen ACK'leri Tek Noktadan Dağıt
            telemetry.poll(mav_conn, payload_ctrl)

            # 2. Bloklamayan Servo Durum Makinesini İlerlet
            if payload_ctrl:
                payload_ctrl.tick()

            # 3. Bayat Telemetri Koruması
            now_ts = time.monotonic()
            if telemetry.is_stale() and mav_conn is not None:
                if now_ts - last_stale_warn_s > 2.0:
                    logger.warning("Telemetri bayat; bu karede atış kararı atlanıyor.")
                    last_stale_warn_s = now_ts

                draw_hud(
                    frame,
                    telemetry,
                    None,
                    payload_ctrl.is_released(1) if payload_ctrl else False,
                    payload_ctrl.is_released(2) if payload_ctrl else False,
                )
                cv2.imshow("TEKNOFEST Mission 2 Master Pipeline", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            # Kare İçi Hata İzolasyonu (Tekil bozuk karelerde görevin çökmesini önler)
            try:
                # 4. Dünya-Sabit Çerçevede Balistik Kestirim
                impact_x, impact_y, _ = ballistics.predict_drop_offset_world(
                    uav_ground_velocity_xy=(telemetry.ground_vx.value, telemetry.ground_vy.value),
                    uav_altitude_m=telemetry.altitude_agl.value,
                    wind_xyz=telemetry.wind_xyz,
                    dt=float(bal_cfg.get("dt", 0.01)),
                )

                # Sistem gecikmesi (180ms) avansı: Uçağın yer hızına göre çarpma noktasını ötele
                lead_x = telemetry.ground_vx.value * system_latency_s
                lead_y = telemetry.ground_vy.value * system_latency_s
                effective_impact_x = impact_x + lead_x
                effective_impact_y = impact_y + lead_y

                # 5. Algılama ve Zemin Projeksiyonu
                detections: List[TargetDetection] = detector.detect(frame)
                candidate_targets: List[Tuple[float, TargetDetection]] = []

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

                    dist_err = math.hypot(xt - effective_impact_x, yt - effective_impact_y)
                    candidate_targets.append((dist_err, det))

                # 6. Önceliklendirme, Tutum Kontrolü ve Bırakma Kararı
                min_err_frame: Optional[float] = None
                is_attitude_safe = (
                    abs(telemetry.roll_deg.value) <= max_roll_gate_deg
                    and abs(telemetry.pitch_deg.value) <= max_pitch_gate_deg
                )

                if candidate_targets:
                    candidate_targets.sort(key=lambda item: item[0])
                    min_err_frame = candidate_targets[0][0]

                    for dist_err, det in candidate_targets:
                        if dist_err <= combined_tol_m and is_attitude_safe and payload_ctrl:
                            auth = telemetry.is_authorized(require_arm, force=args.force_release)
                            if det.class_name == "BLUE_SQUARE" and not payload_ctrl.is_released(1):
                                logger.info("🎯 MAVİ HEDEF MENZİLDE (Hata: %.2fm). Tetikleniyor...", dist_err)
                                payload_ctrl.trigger_release(1, is_authorized=auth)
                                break
                            elif det.class_name == "RED_SQUARE" and not payload_ctrl.is_released(2):
                                logger.info("🎯 KIRMIZI HEDEF MENZİLDE (Hata: %.2fm). Tetikleniyor...", dist_err)
                                payload_ctrl.trigger_release(2, is_authorized=auth)
                                break

                # 7. Görselleştirme ve Ekran Çizimi
                detector.draw_detections(frame, detections)
                draw_hud(
                    frame,
                    telemetry,
                    min_err_frame,
                    payload_ctrl.is_released(1) if payload_ctrl else False,
                    payload_ctrl.is_released(2) if payload_ctrl else False,
                )

            except Exception as frame_exc:
                logger.warning("Kare işlenirken geçici hata oluştu, kare atlanıyor: %s", frame_exc)

            cv2.imshow("TEKNOFEST Mission 2 Master Pipeline", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except Exception as fatal_exc:
        logger.exception("Ölümcül hata nedeniyle boru hattı durduruluyor: %s", fatal_exc)
    finally:
        logger.info("Kaynaklar serbest bırakılıyor...")
        cap.release()
        cv2.destroyAllWindows()
        if mav_conn:
            try:
                mav_conn.close()
            except Exception:
                pass
        logger.info("Master Pipeline güvenle kapatıldı.")


if __name__ == "__main__":
    main()
