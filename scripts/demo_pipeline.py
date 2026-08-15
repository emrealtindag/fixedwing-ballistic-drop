"""Demo pipeline tying perception, ballistics and MAVLink payload controller.

This script reads frames from a camera or video file, runs YOLO target
detection, estimates the ground distance to detected square targets using a
simple pinhole camera model (requires approximate focal length in pixels),
computes ballistic drop offsets and triggers payload release via MAVLink when
a detected target is within the computed release point.

Assumptions and simplifications (for demo purposes):
 - The pinhole distance estimate uses: distance_m = focal_length_px * target_real_height_m / bbox_height_px
 - The UAV airspeed is approximated from VFR_HUD.groundspeed and assumed
   to be aligned with the camera optical axis (forward = +x).
 - Camera pointing is assumed such that distance along optical axis corresponds
   to forward range to target (typical for forward-facing cameras).

Usage:
    python scripts/demo_pipeline.py --video-source 0 --mavlink-conn serial:/dev/ttyUSB0:115200

"""
from __future__ import annotations

import argparse
import time
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from scandium.perception.target_detector import YOLOTargetDetector, TargetDetection
from scandium.control.ballistics import BallisticCalculator
from scandium.mavlink.payload_controller import PayloadController

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


def get_telemetry(conn) -> Tuple[float, float]:
    """Retrieve an approximate groundspeed (m/s) and altitude (m).

    Tries to fetch non-blocking VFR_HUD and GLOBAL_POSITION_INT messages. If
    not available, returns (groundspeed=20.0, altitude=120.0) as defaults.
    """
    default_speed = 20.0
    default_alt = 120.0

    if conn is None:
        return default_speed, default_alt

    try:
        # Non-blocking reads for VFR_HUD and GLOBAL_POSITION_INT
        gs = None
        alt = None
        m_vfr = conn.recv_match(type="VFR_HUD", blocking=False)
        if m_vfr is not None and hasattr(m_vfr, "groundspeed"):
            gs = float(m_vfr.groundspeed)
        m_pos = conn.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
        if m_pos is not None:
            # relative_alt is in millimeters
            if hasattr(m_pos, "relative_alt"):
                alt = float(m_pos.relative_alt) / 1000.0
            elif hasattr(m_pos, "rel_alt"):
                alt = float(m_pos.rel_alt) / 1000.0
        # Fallbacks
        if gs is None:
            gs = default_speed
        if alt is None:
            alt = default_alt
        return gs, alt
    except Exception as exc:  # pragma: no cover - env dependent
        logger.exception("Error reading telemetry: %s", exc)
        return default_speed, default_alt


def estimate_target_distance_m(bbox_h_px: int, class_name: str, focal_length_px: float) -> Optional[float]:
    """Estimate distance to target using simple pinhole formula.

    distance_m = focal_length_px * real_height_m / bbox_height_px

    Returns None if bbox_h_px is zero.
    """
    if bbox_h_px <= 0:
        return None
    # Real sizes (meters) per class
    real_height = {"BLUE_SQUARE": 4.0, "RED_SQUARE": 2.0}.get(class_name)
    if real_height is None:
        return None
    return (focal_length_px * real_height) / float(bbox_h_px)


def pixel_to_lateral_m(cx: int, img_cx: int, distance_m: float, focal_length_px: float) -> float:
    """Convert horizontal pixel offset to meters at estimated distance using pinhole model.

    x_m = (cx - img_cx) * distance_m / focal_length_px
    """
    return (float(cx) - float(img_cx)) * (distance_m / float(focal_length_px))


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
    parser.add_argument("--model-path", type=str, default="best.pt", help="Path to YOLO model (default: best.pt)")
    parser.add_argument("--mavlink-conn", type=str, default="", help="MAVLink connection string (e.g. serial:/dev/ttyUSB0:115200)")
    parser.add_argument("--focal-length-px", type=float, default=1000.0, help="Approximate camera focal length in pixels for distance estimation")
    parser.add_argument("--conf-threshold", type=float, default=0.65, help="YOLO confidence threshold")
    parser.add_argument("--use-contour-check", action="store_true", help="Enable contour 4-corner verification in detector")
    parser.add_argument("--release-tolerance-m", type=float, default=3.0, help="Tolerance (m) when comparing predicted offset and estimated target distance")
    parser.add_argument("--lateral-tolerance-m", type=float, default=2.0, help="Allowed lateral error (m) from image center to consider locked target")
    args = parser.parse_args()

    # Video source parsing
    try:
        vs_idx = int(args.video_source)
        video_source = vs_idx
    except Exception:
        video_source = args.video_source

    # Initialize subsystems
    detector = YOLOTargetDetector(model_path=args.model_path, conf_threshold=args.conf_threshold, use_contour_check=args.use_contour_check)
    ballistics = BallisticCalculator()  # defaults as specified

    mav_conn = connect_mavlink(args.mavlink_conn) if args.mavlink_conn else None
    transport = mav_conn if mav_conn is not None else DummyTransport()
    payload_ctrl = PayloadController(transport)

    # Video capture
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        logger.error("Failed to open video source: %s", args.video_source)
        return

    logger.info("Starting demo pipeline. Press 'q' to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("End of video or camera error")
                break

            # Telemetry
            groundspeed, altitude = get_telemetry(mav_conn)
            # UAV airspeed vector approximated as forward-groundspeed along x
            uav_airspeed = (groundspeed, 0.0, 0.0)

            # Ballistic prediction (no wind)
            forward_offset, lateral_offset, tti = ballistics.predict_drop_offset(uav_airspeed, altitude, wind_xyz=(0.0, 0.0, 0.0), dt=0.01)

            # Detect targets
            detections = detector.detect(frame)

            # Draw detections
            vis = detector.draw_detections(frame, detections)

            # Process each detection for distance and potential release
            h, w = frame.shape[:2]
            img_cx = w // 2
            for det in detections:
                # Estimate distance using bounding box height
                _, _, bw, bh = det.bbox
                est_dist = estimate_target_distance_m(bh, det.class_name, args.focal_length_px)
                if est_dist is None:
                    continue
                # Lateral offset in meters
                cx, cy = det.center_px
                lat_m = pixel_to_lateral_m(cx, img_cx, est_dist, args.focal_length_px)

                # Debug overlay per detection
                label = f"dist={est_dist:.1f}m lat={lat_m:.1f}m pred={forward_offset:.1f}m"
                cv2.putText(vis, label, (det.bbox[0], det.bbox[1] + det.bbox[3] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1, cv2.LINE_AA)

                # Determine if within release conditions
                within_forward = abs(forward_offset - est_dist) <= args.release_tolerance_m
                within_lateral = abs(lat_m) <= args.lateral_tolerance_m

                if within_forward and within_lateral:
                    # Trigger based on class
                    if det.class_name == "BLUE_SQUARE":
                        ok = payload_ctrl.release_payload_1()
                        if ok:
                            cv2.putText(vis, "RELEASED PAYLOAD 1", (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
                    elif det.class_name == "RED_SQUARE":
                        ok = payload_ctrl.release_payload_2()
                        if ok:
                            cv2.putText(vis, "RELEASED PAYLOAD 2", (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

            # Draw HUD
            draw_hud(vis, groundspeed, altitude, forward_offset)

            # Show status of payloads
            status = payload_ctrl.status
            status_txt = f"P1:{int(status.payload1_released)} P2:{int(status.payload2_released)} Count:{status.total_released_count}"
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
