"""Demo pipeline tying perception, ballistics, Geo projection and MAVLink payload control.

This script reads frames from a camera or video file, runs YOLO target
detection, projects detections to ground coordinates using a ray-ground
intersection (GeoProjector), computes ballistic drop offsets and triggers
payload release via MAVLink when a detected target is within the computed
release point.

Usage example:
    python scripts/demo_pipeline.py --video-source 0 --mavlink-conn serial:/dev/ttyUSB0:115200

The script is written for demo/testing. In real operations ensure additional
safety checks (arming state, flight mode, operator consent) before enabling
payload release.
"""
from __future__ import annotations

import argparse
import time
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from src.scandium.perception.target_detector import YOLOTargetDetector
from src.scandium.perception.geo_projection import GeoProjector
from src.scandium.control.ballistics import BallisticCalculator
from src.scandium.mavlink.payload_controller import PayloadController

try:
    from pymavlink import mavutil  # type: ignore
    PYMAVLINK_AVAILABLE = True
except Exception:
    PYMAVLINK_AVAILABLE = False


logger = logging.getLogger("demo_pipeline")
logging.basicConfig(level=logging.INFO)


class DummyTransport:
    """Fallback transport when MAVLink is not available; logs commands only."""

    def __init__(self) -> None:
        self.target_system = 1
        self.target_component = 1

    def set_servo(self, channel: int, pwm: int) -> None:  # pragma: no cover - dummy
        logger.info("DummyTransport.set_servo called: channel=%s pwm=%s", channel, pwm)

    def set_servo_pwm(self, channel: int, pwm: int) -> None:  # pragma: no cover - dummy
        logger.info("DummyTransport.set_servo_pwm called: channel=%s pwm=%s", channel, pwm)


def connect_mavlink(conn_str: Optional[str], timeout: float = 5.0):
    """Attempt to connect to MAVLink; return connection or None.

    If pymavlink is not installed or connection fails, returns None.
    """
    if not conn_str:
        return None
    if not PYMAVLINK_AVAILABLE:
        logger.warning("pymavlink not available; skipping MAVLink connection")
        return None
    try:
        logger.info("Connecting to MAVLink on %s", conn_str)
        conn = mavutil.mavlink_connection(conn_str)
        # Wait for a heartbeat
        conn.wait_heartbeat(timeout=timeout)
        logger.info("MAVLink heartbeat received (system %s comp %s)", conn.target_system, conn.target_component)
        return conn
    except Exception as exc:  # pragma: no cover - env dependent
        logger.exception("Failed to connect to MAVLink: %s", exc)
        return None


def get_telemetry(conn) -> Tuple[float, float, float, float]:
    """Retrieve approximate groundspeed (m/s), altitude_agl (m), roll (deg), pitch (deg).

    If connection is None or messages are not available returns CLI defaults.
    """
    default_speed = 18.0
    default_alt = 40.0
    default_roll = 0.0
    default_pitch = 0.0

    if conn is None:
        return default_speed, default_alt, default_roll, default_pitch

    try:
        gs = None
        alt = None
        roll = None
        pitch = None

        m_vfr = conn.recv_match(type="VFR_HUD", blocking=False)
        if m_vfr is not None and hasattr(m_vfr, "groundspeed"):
            gs = float(m_vfr.groundspeed)

        m_pos = conn.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
        if m_pos is not None:
            # relative_alt is mm in many autopilots
            if hasattr(m_pos, "relative_alt"):
                alt = float(m_pos.relative_alt) / 1000.0
            elif hasattr(m_pos, "rel_alt"):
                alt = float(m_pos.rel_alt) / 1000.0

        m_att = conn.recv_match(type="ATTITUDE", blocking=False)
        if m_att is not None:
            # ATTITUDE gives roll,pitch in radians
            if hasattr(m_att, "roll"):
                roll = float(m_att.roll) * 180.0 / np.pi
            if hasattr(m_att, "pitch"):
                pitch = float(m_att.pitch) * 180.0 / np.pi

        if gs is None:
            gs = default_speed
        if alt is None:
            alt = default_alt
        if roll is None:
            roll = default_roll
        if pitch is None:
            pitch = default_pitch

        return gs, alt, roll, pitch
    except Exception as exc:  # pragma: no cover - env dependent
        logger.exception("Error reading telemetry: %s", exc)
        return default_speed, default_alt, default_roll, default_pitch


def draw_hud(frame: np.ndarray, speed: float, altitude: float, predicted_offset: float) -> None:
    """Draw a simple HUD overlay onto the frame (in-place).

    Shows artificial horizon line, speed, altitude, and predicted drop offset.
    """
    h, w = frame.shape[:2]
    # Artificial horizon: center line
    cv2.line(frame, (0, h // 2), (w, h // 2), (200, 200, 200), 1)
    # Text info
    info = [f"Speed: {speed:.1f} m/s", f"Alt: {altitude:.1f} m", f"Pred offset: {predicted_offset:.1f} m"]
    for i, txt in enumerate(info):
        cv2.putText(frame, txt, (10, 20 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo pipeline: detection -> ballistics -> payload release")
    parser.add_argument("--video-source", type=str, default="0", help="Video source (camera index or file path). Default 0")
    parser.add_argument("--model-path", type=str, default="weights/best.pt", help="Path to YOLO model (default: weights/best.pt)")
    parser.add_argument("--mavlink-conn", type=str, default="", help="MAVLink connection string (e.g. serial:/dev/ttyUSB0:115200)")
    parser.add_argument("--focal-length-px", type=float, default=1000.0, help="Approximate camera focal length in pixels for distance estimation")
    parser.add_argument("--conf-threshold", type=float, default=0.65, help="YOLO confidence threshold")
    parser.add_argument("--use-contour-check", action="store_true", help="Enable contour 4-corner verification in detector")
    parser.add_argument("--release-tolerance-m", type=float, default=3.0, help="Tolerance (m) when comparing predicted offset and estimated target distance")
    parser.add_argument("--lateral-tolerance-m", type=float, default=2.0, help="Allowed lateral error (m) from image center to consider locked target")
    parser.add_argument("--altitude", type=float, default=40.0, help="Fallback altitude AGL (m) if MAVLink not provided")
    parser.add_argument("--airspeed", type=float, default=18.0, help="Fallback airspeed (m/s) if MAVLink not provided")
    parser.add_argument("--mount-pitch", type=float, default=25.0, help="Camera mount pitch (deg)")
    args = parser.parse_args()

    # Video source parsing
    try:
        vs_idx = int(args.video_source)
        video_source: int | str = vs_idx
    except Exception:
        video_source = args.video_source

    # Initialize detector and ballistics
    detector = YOLOTargetDetector(model_path=args.model_path, conf_threshold=args.conf_threshold, use_contour_check=args.use_contour_check)
    ballistics = BallisticCalculator()

    mav_conn = connect_mavlink(args.mavlink_conn) if args.mavlink_conn else None
    transport = mav_conn if mav_conn is not None else DummyTransport()
    payload_ctrl = PayloadController(transport)

    # Video capture
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        logger.error("Failed to open video source: %s", args.video_source)
        return

    geo_proj: Optional[GeoProjector] = None
    camera_K: Optional[np.ndarray] = None

    logger.info("Starting demo pipeline. Press 'q' to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("End of video or camera error")
                break

            h, w = frame.shape[:2]
            img_cx = w / 2.0
            img_cy = h / 2.0

            # Initialize camera intrinsics and GeoProjector on first frame
            if geo_proj is None:
                f_px = float(args.focal_length_px)
                camera_K = np.array([[f_px, 0.0, img_cx], [0.0, f_px, img_cy], [0.0, 0.0, 1.0]], dtype=float)
                geo_proj = GeoProjector(camera_K, mount_pitch_deg=float(args.mount_pitch), mount_roll_deg=0.0)
                logger.info("GeoProjector initialized with f=%.1f cx=%.1f cy=%.1f", f_px, img_cx, img_cy)

            # Telemetry
            groundspeed, altitude_agl, roll_deg, pitch_deg = get_telemetry(mav_conn)

            # Use telemetry fallbacks if no MAVLink
            if mav_conn is None:
                groundspeed = float(args.airspeed)
                altitude_agl = float(args.altitude)

            # Ballistic prediction
            uav_airspeed = (float(groundspeed), 0.0, 0.0)
            try:
                predicted_forward, predicted_lateral, tti = ballistics.predict_drop_offset(uav_airspeed, float(altitude_agl), wind_xyz=(0.0, 0.0, 0.0), dt=0.01)
            except Exception as exc:
                logger.exception("Ballistic prediction failed: %s", exc)
                predicted_forward = float('inf')
                predicted_lateral = 0.0

            # Detect targets
            detections = detector.detect(frame)
            vis = detector.draw_detections(frame, detections)

            # For each detection compute ground projection and decide release
            for det in detections:
                # det.center_px is expected to be (cx, cy)
                try:
                    center_px = (int(det.center_px[0]), int(det.center_px[1]))
                except Exception:
                    logger.warning("Detection has no valid center_px: %s", det)
                    continue

                try:
                    X_target_m, Y_lateral_m = geo_proj.pixel_to_ground(center_px, float(altitude_agl), uav_roll_deg=float(roll_deg), uav_pitch_deg=float(pitch_deg))
                except Exception as exc:
                    logger.exception("Geo projection failed for pixel %s: %s", center_px, exc)
                    continue

                # If projection returned invalid values skip
                if not np.isfinite(X_target_m) or not np.isfinite(Y_lateral_m):
                    logger.debug("Ray does not intersect ground in front for pixel %s", center_px)
                    continue

                # Overlay detection info
                label = f"{det.class_name} X={X_target_m:.1f}m Y={Y_lateral_m:.1f}m"
                cv2.putText(vis, label, (det.bbox[0], det.bbox[1] + det.bbox[3] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1, cv2.LINE_AA)

                # Trigger decision
                within_forward = abs(X_target_m - float(predicted_forward)) <= float(args.release_tolerance_m)
                within_lateral = abs(Y_lateral_m) <= float(args.lateral_tolerance_m)

                if within_forward and within_lateral:
                    if det.class_name == "BLUE_SQUARE":
                        ok = payload_ctrl.release_payload_1()
                        if ok:
                            cv2.putText(vis, "RELEASED PAYLOAD 1", (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
                    elif det.class_name == "RED_SQUARE":
                        ok = payload_ctrl.release_payload_2()
                        if ok:
                            cv2.putText(vis, "RELEASED PAYLOAD 2", (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

            # Draw HUD and status
            draw_hud(vis, float(groundspeed), float(altitude_agl), float(predicted_forward) if np.isfinite(predicted_forward) else 0.0)

            # Show payload status
            # payload_ctrl may expose flags or a status property; attempt both safely
            try:
                p1 = int(getattr(payload_ctrl, "payload1_released", getattr(payload_ctrl, "status", None) and int(getattr(payload_ctrl.status, "payload1_released", 0)) or 0))
                p2 = int(getattr(payload_ctrl, "payload2_released", getattr(payload_ctrl, "status", None) and int(getattr(payload_ctrl.status, "payload2_released", 0)) or 0))
                count = int(getattr(payload_ctrl, "status", None) and int(getattr(payload_ctrl.status, "total_released_count", 0)) or 0)
            except Exception:
                p1, p2, count = 0, 0, 0

            status_txt = f"P1:{p1} P2:{p2} Count:{count}"
            cv2.putText(vis, status_txt, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow("Demo Pipeline", vis)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if mav_conn is not None:
            try:
                mav_conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
