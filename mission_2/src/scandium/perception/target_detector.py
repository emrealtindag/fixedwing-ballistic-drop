"""scandium.perception.target_detector

Target detection utilities using a YOLOv8 model with post-filtering to
remove non-square shapes (rotors, false targets) and small noise.

This module defines a TargetDetection dataclass and a YOLOTargetDetector
class that wraps ultralytics.YOLO inference and applies aspect-ratio,
area and optional contour-based 4-corner verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List, Dict

import numpy as np
import cv2


@dataclass(frozen=True)
class TargetDetection:
    """Represents a single detected target in an image.

    Attributes
    ----------
    class_name: str
        Human-readable class name (e.g. 'BLUE_SQUARE').
    class_id: int
        Integer class id as produced by the detector.
    confidence: float
        Detection confidence score in range [0, 1].
    bbox: tuple[int, int, int, int]
        Bounding box as (x, y, w, h) where (x, y) is the top-left corner.
    center_px: tuple[int, int]
        Pixel coordinates (cx, cy) of the bounding box center.
    """

    class_name: str
    class_id: int
    confidence: float
    bbox: Tuple[int, int, int, int]
    center_px: Tuple[int, int]


class YOLOTargetDetector:
    """YOLOv8-based target detector with post-filtering for square targets.

    The class loads an Ultralyics YOLO model and exposes `detect` and
    `draw_detections` convenience methods. Detections are filtered by:
      - aspect ratio (0.80 <= w/h <= 1.20)
      - minimum area (>= 400 px)
      - optional contour polygon approximation with 4 corners

    Class id mapping (as required):
      0 -> 'BLUE_SQUARE' (4x4m)
      1 -> 'RED_SQUARE'  (2x2m)

    Parameters
    ----------
    model_path: str
        Path to a YOLOv8 model file (default: 'best.pt').
    conf_threshold: float
        Confidence threshold passed to the model (default: 0.65).
    use_contour_check: bool
        If True, perform cv2.approxPolyDP polygon approximation inside each
        bbox and keep detections whose largest contour approximates to 4
        vertices. Default False (optional behavior).
    """

    CLASS_MAP: Dict[int, str] = {0: "BLUE_SQUARE", 1: "RED_SQUARE"}

    def __init__(
        self,
        model_path: str = "best.pt",
        conf_threshold: float = 0.65,
        use_contour_check: bool = False,
    ) -> None:
        try:
            # Import here to avoid heavy dependency when module is imported but
            # not used. This will raise ImportError if ultralytics is not
            # installed which is desirable so caller can handle it.
            from ultralytics import YOLO  # type: ignore

            self.model = YOLO(model_path)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                f"Failed to load YOLO model from '{model_path}': {exc}"
            )

        if not (0.0 <= conf_threshold <= 1.0):
            raise ValueError("conf_threshold must be in [0, 1]")

        self.conf_threshold = float(conf_threshold)
        self.use_contour_check = bool(use_contour_check)

    def _extract_boxes_from_result(self, res) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract xyxy, confidences and class ids from a Ultralyics result.

        The Ultralytics `res` object may present data in different formats
        depending on versions (tensors, lists). This helper tries common
        access patterns and returns numpy arrays: xyxy (N,4), confs (N,), cls (N,).
        """
        # results[0].boxes is the common API. We accept either tensors or list-like.
        boxes = getattr(res, "boxes", None)
        if boxes is None:
            # No boxes attribute -> return empty arrays
            return (np.zeros((0, 4), dtype=float), np.zeros((0,), dtype=float), np.zeros((0,), dtype=int))

        # Attempt to access common attributes
        try:
            xyxy = np.array(boxes.xyxy).astype(float)
        except Exception:
            # Fallback: try iterating boxes
            try:
                vals = []
                confs = []
                cls = []
                for b in boxes:
                    # each b may be sequence-like [x1,y1,x2,y2,conf,cls]
                    arr = np.array(b).astype(float)
                    vals.append(arr[:4])
                    confs.append(float(arr[4]))
                    cls.append(int(arr[5]))
                if len(vals) == 0:
                    return (np.zeros((0, 4), dtype=float), np.zeros((0,), dtype=float), np.zeros((0,), dtype=int))
                return (np.vstack(vals), np.array(confs, dtype=float), np.array(cls, dtype=int))
            except Exception:
                return (np.zeros((0, 4), dtype=float), np.zeros((0,), dtype=float), np.zeros((0,), dtype=int))

        # confidences and class ids
        try:
            confs = np.array(boxes.conf).astype(float)
        except Exception:
            confs = np.zeros((xyxy.shape[0],), dtype=float)
        try:
            cls = np.array(boxes.cls).astype(int)
        except Exception:
            cls = np.zeros((xyxy.shape[0],), dtype=int)

        # Ensure shapes align
        if xyxy.shape[0] != confs.shape[0] or xyxy.shape[0] != cls.shape[0]:
            # Truncate to smallest length
            n = min(xyxy.shape[0], confs.shape[0], cls.shape[0])
            xyxy = xyxy[:n]
            confs = confs[:n]
            cls = cls[:n]

        return xyxy, confs, cls

    def _passes_contour_check(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
        """Perform contour approximation inside bbox and look for 4-corner polygon.

        Returns True if the largest contour approximates to 4 vertices and has
        a reasonable area relative to the bbox area.
        """
        try:
            roi = frame[y : y + h, x : x + w]
            if roi.size == 0:
                return False
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            # Adaptive preprocessing: blur + Canny edge detection
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return False
            # find largest contour
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area < 0.2 * (w * h):
                # too small relative to bbox
                return False
            peri = cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
            return len(approx) == 4
        except Exception:
            return False

    def detect(self, frame: np.ndarray) -> List[TargetDetection]:
        """Run detection on a single image and return filtered targets.

        Parameters
        ----------
        frame: np.ndarray
            BGR image as produced by OpenCV (H, W, 3).

        Returns
        -------
        list[TargetDetection]
            List of detections that passed the filters.
        """
        if not isinstance(frame, np.ndarray):
            raise TypeError("frame must be a numpy.ndarray (OpenCV image)")

        # Run model inference
        results = self.model.predict(frame, conf=self.conf_threshold, verbose=False)
        if len(results) == 0:
            return []
        res = results[0]

        xyxy, confs, clsids = self._extract_boxes_from_result(res)

        detections: List[TargetDetection] = []
        for i in range(xyxy.shape[0]):
            conf = float(confs[i])
            clsid = int(clsids[i])
            if conf < self.conf_threshold:
                continue

            x1, y1, x2, y2 = xyxy[i].astype(int)
            # ensure valid box coordinates
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = max(x1 + 1, x2)
            y2 = max(y1 + 1, y2)
            w = x2 - x1
            h = y2 - y1

            # Minimum area filter (pixels)
            area = w * h
            if area < 400:
                continue

            # Aspect ratio filter for square-like targets
            aspect = float(w) / float(h) if h != 0 else 0.0
            if not (0.80 <= aspect <= 1.20):
                continue

            # Optional contour polygon check (4 corners)
            if self.use_contour_check and not self._passes_contour_check(frame, x1, y1, w, h):
                continue

            class_name = self.CLASS_MAP.get(clsid, f"CLASS_{clsid}")
            cx = x1 + (w // 2)
            cy = y1 + (h // 2)
            det = TargetDetection(
                class_name=class_name,
                class_id=clsid,
                confidence=conf,
                bbox=(x1, y1, w, h),
                center_px=(int(cx), int(cy)),
            )
            detections.append(det)

        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[TargetDetection]) -> np.ndarray:
        """Draw bounding boxes and labels onto a copy of the frame.

        Colors (BGR): BLUE_SQUARE -> blue, RED_SQUARE -> green (as requested: blue/green).

        Parameters
        ----------
        frame: np.ndarray
            BGR image to draw on. The function returns a copy; the original is
            not modified.
        detections: list[TargetDetection]
            Detections to render.

        Returns
        -------
        np.ndarray
            Image copy with drawings.
        """
        out = frame.copy()
        for d in detections:
            x, y, w, h = d.bbox
            if d.class_name == "BLUE_SQUARE":
                color = (255, 0, 0)  # blue (BGR)
            elif d.class_name == "RED_SQUARE":
                color = (0, 255, 0)  # green (BGR)
            else:
                color = (0, 255, 255)  # yellow for unknown

            # Rectangle
            cv2.rectangle(out, (x, y), (x + w, y + h), color, thickness=2)

            # Label background
            label = f"{d.class_name} {d.confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x, y - th - 6), (x + tw + 6, y), color, thickness=-1)
            cv2.putText(
                out,
                label,
                (x + 3, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                thickness=1,
                lineType=cv2.LINE_AA,
            )

            # Draw center
            cx, cy = d.center_px
            cv2.drawMarker(out, (cx, cy), color=(0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=8, thickness=1)

        return out
