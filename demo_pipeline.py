"""scripts.demo_pipeline

End-to-end execution pipeline for TEKNOFEST Fixed-Wing Mission 2.
Integrates YOLO Detection, Ray-Ground Geo-Projection (Yaw aware),
Heun Ballistics, and Defensive MAVLink Payload Controller.
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import cv2
import numpy as np
import yaml
from pymavlink import mavutil

# Proje İçi Modül Importları
from scandium.control.ballistics import BallisticCalculator
from scandium.mavlink.payload_controller import PayloadController
from scandium.perception.geo_projection import GeoProjector
from scandium.perception.target_detector import TargetDetection, YOLOTargetDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mission2_pipeline")


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """YAML konfigürasyon dosyasını güvenle yükler."""
    p = Path(config_path)
    if not p.exists():
        logger.warning("Konfigürasyon dosyası bulunamadı: %s. Varsayılanlar kullanılacak.", config_path)
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TEKNOFEST Mission 2 Live Pipeline")
    parser.add_argument("--config", type=str, default="configs/mission2_fixedwing.yaml", help="Path to config YAML")
    parser.add_argument("--video-source", type=str, default="0", help="Camera index (e.g. '0') or video file path")
    parser.add_argument("--model-path", type=str, default=None, help="Path to YOLO weights (overrides config)")
    parser.add_argument("--mavlink-conn", type=str, default=None, help="MAVLink connection string (overrides config)")
    parser.add_argument("--force-release", action="store_true", help="Bypass vehicle armed check for ground testing")
    return parser.parse_args()


def connect_mavlink(conn_str: str) -> mavutil.mavlink_connection | None:
    try:
        logger.info("MAVLink hattına bağlanılıyor: %s", conn_str)
        conn = mavutil.mavlink_connection(conn_str)
        conn.wait_heartbeat(timeout=3.0)
        logger.info("MAVLink Heartbeat alındı (Sistem ID: %s)", conn.target_system)
        return conn
    except Exception as exc:
        logger.warning("MAVLink bağlantısı kurulamadı (%s). Simüle modda çalışılıyor.", exc)
        return None


def fetch_telemetry(
    mav_conn: mavutil.mavlink_connection | None,
    default_alt: float = 40.0,
    default_airspeed: float = 18.0,
) -> Tuple[float, float, float, float, float, Tuple[float, float, float]]:
    """Otopilottan anlık irtifa, hız, roll, pitch, yaw ve rüzgar verilerini çeker."""
    airspeed = default_airspeed
    groundspeed = default_airspeed
    altitude_agl = default_alt
    roll_deg = 0.0
    pitch_deg = 0.0
    yaw_deg = 0.0
    wind_xyz = (0.0, 0.0, 0.0)

    if mav_conn is None:
        return altitude_agl, airspeed, roll_deg, pitch_deg, yaw_deg, wind_xyz

    # Kuyruktaki tüm mesajları tüketip en güncel olanları al
    while True:
        msg = mav_conn.recv_match(blocking=False)
        if msg is None:
            break

        msg_type = msg.get_type()
        if msg_type == "VFR_HUD":
            airspeed = float(getattr(msg, "airspeed", airspeed))
            groundspeed = float(getattr(msg, "groundspeed", groundspeed))
            altitude_agl = float(getattr(msg, "alt", altitude_agl))
        elif msg_type == "GLOBAL_POSITION_INT":
            relative_alt_mm = getattr(msg, "relative_alt", None)
            if relative_alt_mm is not None:
                altitude_agl = relative_alt_mm / 1000.0
        elif msg_type == "ATTITUDE":
            roll_deg = math.degrees(float(getattr(msg, "roll", 0.0)))
            pitch_deg = math.degrees(float(getattr(msg, "pitch", 0.0)))
            yaw_deg = math.degrees(float(getattr(msg, "yaw", 0.0)))
        elif msg_type == "WIND":
            w_spd = float(getattr(msg, "speed", 0.0))
            w_dir = math.radians(float(getattr(msg, "direction", 0.0)))
            wind_xyz = (w_spd * math.cos(w_dir), w_spd * math.sin(w_dir), 0.0)

    return altitude_agl, max(1.0, airspeed), roll_deg, pitch_deg, yaw_deg, wind_xyz


def draw_hud(
    frame: np.ndarray,
    altitude: float,
    airspeed: float,
    yaw: float,
    bal_offset: float,
    p1_status: bool,
    p2_status: bool,
) -> None:
    """OpenCV HUD kokpit göstergelerini çizer."""
    h, w = frame.shape[:2]
    # Üst bilgi çubuğu
    cv2.rectangle(frame, (0, 0), (w, 40), (20, 20, 20), -1)
    hud_text = (
        f"ALT: {altitude:4.1f}m | SPD: {airspeed:4.1f}m/s | YAW: {yaw:5.1f}deg | "
        f"BAL_OFFSET: {bal_offset:4.1f}m"
    )
    cv2.putText(frame, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Bırakma durum kutucukları
    p1_color = (0, 200, 0) if p1_status else (0, 0, 220)
    p2_color = (0, 200, 0) if p2_status else (0, 0, 220)
    cv2.rectangle(frame, (w - 180, 50), (w - 10, 80), p1_color, -1)
    cv2.putText(frame, f"PAYLOAD 1: {'ATILDI' if p1_status else 'HAZIR'}", (w - 170, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    cv2.rectangle(frame, (w - 180, 90), (w - 10, 120), p2_color, -1)
    cv2.putText(frame, f"PAYLOAD 2: {'ATILDI' if p2_status else 'HAZIR'}", (w - 170, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


def main() -> None:
    args = parse_arguments()
    cfg = load_yaml_config(args.config)

    # Parametreleri Config ve Argümanlardan Birleştir
    cam_cfg = cfg.get("camera", {})
    bal_cfg = cfg.get("ballistics", {})
    pay_cfg = cfg.get("payload", {})
    mis_cfg = cfg.get("mission", {})
    mav_cfg = cfg.get("mavlink", {})

    model_path = args.model_path or mis_cfg.get("model_path", "weights/best.pt")
    mav_conn_str = args.mavlink_conn or mav_cfg.get("connection_string", "udp:127.0.0.1:14551")
    conf_thresh = mis_cfg.get("conf_threshold", 0.65)
    use_contour = mis_cfg.get("use_contour_check", False)

    mount_pitch = cam_cfg.get("mount_pitch_deg", 25.0)
    mount_roll = cam_cfg.get("mount_roll_deg", 0.0)
    focal_len = cam_cfg.get("focal_length_px", 1000.0)

    rel_tol_m = mis_cfg.get("release_tolerance_m", 3.0)
    lat_tol_m = mis_cfg.get("lateral_tolerance_m", 2.0)

    # Modülleri Başlat
    logger.info("Modüller başlatılıyor...")
    detector = YOLOTargetDetector(model_path=model_path, conf_threshold=conf_thresh, use_contour_check=use_contour)
    ballistics = BallisticCalculator(
        payload_mass_kg=bal_cfg.get("payload_mass_kg", 0.35),
        drag_coeff_cd=bal_cfg.get("drag_coeff_cd", 0.45),
        cross_area_m2=bal_cfg.get("cross_area_m2", 0.008),
        air_density_rho=bal_cfg.get("air_density_rho", 1.225),
        dt=bal_cfg.get("dt", 0.01),
        max_simulation_time_s=bal_cfg.get("max_simulation_time_s", 60.0),
    )

    mav_conn = connect_mavlink(mav_conn_str)
    payload_ctrl = None
    if mav_conn:
        payload_ctrl = PayloadController(
            mav_connection=mav_conn,
            servo_channel=pay_cfg.get("servo_channel", 9),
            pwm_payload_1=pay_cfg.get("pwm_payload_1", 1500),
            pwm_payload_2=pay_cfg.get("pwm_payload_2", 2000),
            require_arming=pay_cfg.get("require_arming", True),
            ack_retries=pay_cfg.get("ack_retries", 2),
            ack_timeout_s=pay_cfg.get("ack_timeout_s", 1.0),
            target_system=pay_cfg.get("target_system", 1),
            target_component=pay_cfg.get("target_component", 1),
        )

    # Video Kaynağını Aç
    video_src = int(args.video_source) if args.video_source.isdigit() else args.video_source
    cap = cv2.VideoCapture(video_src)
    if not cap.isOpened():
        logger.error("Video kaynağı açılamadı: %s", video_src)
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    K = np.array([[focal_len, 0.0, width / 2.0], [0.0, focal_len, height / 2.0], [0.0, 0.0, 1.0]])
    geo_projector = GeoProjector(camera_matrix=K, mount_pitch_deg=mount_pitch, mount_roll_deg=mount_roll)

    logger.info("Ana döngü başlatıldı. Çıkış için 'q' tuşuna basın.")
    p1_released, p2_released = False, False

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.info("Video akışı bitti veya kare okunamadı.")
            break

        # Telemetriyi Oku
        alt, spd, roll, pitch, yaw, wind = fetch_telemetry(
            mav_conn,
            default_alt=mav_cfg.get("fallback_altitude_m", 40.0),
            default_airspeed=mav_cfg.get("fallback_airspeed_mps", 18.0),
        )

        # Balistik Tahmin Hesapla
        fwd_offset, lat_offset, tof = ballistics.predict_drop_offset(
            uav_airspeed_xyz=(spd, 0.0, 0.0),
            uav_altitude_m=alt,
            wind_xyz=wind,
        )

        # YOLO ile Hedefleri Bul
        detections = detector.detect(frame)

        for det in detections:
            # Işın-Zemin Projeksiyonu (Yaw desteği ile)
            x_target, y_target = geo_projector.pixel_to_ground(
                pixel_xy=det.center_px,
                altitude_agl_m=alt,
                uav_roll_deg=roll,
                uav_pitch_deg=pitch,
                uav_yaw_deg=yaw,
            )

            if not np.isfinite(x_target) or not np.isfinite(y_target):
                continue

            # Karar Koşulları
            dist_error = abs(x_target - fwd_offset)
            is_in_drop_window = (dist_error <= rel_tol_m) and (abs(y_target) <= lat_tol_m)

            # Hedef Eşleşmesi ve Bırakma
            if is_in_drop_window and payload_ctrl:
                if det.class_name == "BLUE_SQUARE" and not p1_released:
                    logger.info("🎯 MAVİ HEDEF BALİSTİK MENZİLDE! 1. Yük Bırakılıyor...")
                    if payload_ctrl.release_payload_1(force=args.force_release):
                        p1_released = True
                elif det.class_name == "RED_SQUARE" and not p2_released:
                    logger.info("🎯 KIRMIZI HEDEF BALİSTİK MENZİLDE! 2. Yük Bırakılıyor...")
                    if payload_ctrl.release_payload_2(force=args.force_release):
                        p2_released = True

        # Görselleştirme
        detector.draw_detections(frame, detections)
        draw_hud(frame, alt, spd, yaw, fwd_offset, p1_released, p2_released)

        cv2.imshow("TEKNOFEST Mission 2 Live HUD", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    if mav_conn:
        mav_conn.close()
    logger.info("Pipeline güvenle sonlandırıldı.")


if __name__ == "__main__":
    main()
