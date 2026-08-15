"""scandium.perception.geo_projection

Geometry utilities to project image pixels to ground plane coordinates using
ray-ground intersection. The GeoProjector converts a pixel (u,v) into a point
on the ground (X_forward, Y_lateral) relative to the UAV using the camera
intrinsics matrix K, camera mounting rotation and the vehicle attitude
(roll, pitch) plus altitude h.

Coordinate conventions used here (simple and consistent):
 - World frame: origin at UAV projection onto ground vertically below UAV.
   X axis points forward from the UAV, Y axis points right (lateral), Z axis
   points up. The ground plane is defined as Z = 0, and the UAV is at Z = h (>0).
 - Camera frame: OpenCV convention: x to right, y down, z forward. Rays are
   expressed in camera coordinates and rotated into the world frame.

The algorithm:
 - Compute normalized image ray r_cam = [ (u - cx)/fx, (v - cy)/fy, 1 ].
 - Rotate r_cam into world using R_world_cam = R_body * R_mount (roll/pitch from
   autopilot define R_body; R_mount encodes camera mounting offsets).
 - Solve for t where origin_z + t * r_world_z = 0 (ground intersection).
 - Return (X, Y) = origin_xy + t * r_world_xy.

Notes:
 - If the ray does not intersect the ground (r_world_z >= 0) None is returned.
 - This implementation ignores yaw because only roll/pitch and mount tilt are
   provided; include yaw if available for more accurate global placement.
"""
from __future__ import annotations

from typing import Tuple, Optional
import numpy as np
import math


class GeoProjector:
    """Project pixels to ground-plane coordinates using ray-ground intersection.

    Parameters
    ----------
    K: np.ndarray
        3x3 camera intrinsic matrix (fx, fy, cx, cy).
    cam_mount_roll_rad: float
        Camera mounting roll relative to body frame in radians (positive
        rotates camera clockwise when looking forward).
    cam_mount_pitch_rad: float
        Camera mounting pitch (tilt) relative to body frame in radians. A
        positive value means camera points downwards.
    """

    def __init__(
        self,
        K: np.ndarray,
        cam_mount_roll_rad: float = 0.0,
        cam_mount_pitch_rad: float = 0.0,
    ) -> None:
        if K is None or (not isinstance(K, np.ndarray)) or K.shape != (3, 3):
            raise ValueError("K must be a 3x3 numpy array (camera intrinsic matrix)")
        self.K = K.astype(float)
        self.fx = float(self.K[0, 0])
        self.fy = float(self.K[1, 1])
        self.cx = float(self.K[0, 2])
        self.cy = float(self.K[1, 2])
        self.cam_mount_roll = float(cam_mount_roll_rad)
        self.cam_mount_pitch = float(cam_mount_pitch_rad)

    @staticmethod
    def _Rx(phi: float) -> np.ndarray:
        c = math.cos(phi)
        s = math.sin(phi)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)

    @staticmethod
    def _Ry(theta: float) -> np.ndarray:
        c = math.cos(theta)
        s = math.sin(theta)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)

    @staticmethod
    def _Rz(psi: float) -> np.ndarray:
        c = math.cos(psi)
        s = math.sin(psi)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)

    def project_pixel_to_ground(
        self,
        u: float,
        v: float,
        uav_roll_rad: float,
        uav_pitch_rad: float,
        h_m: float,
    ) -> Optional[Tuple[float, float]]:
        """Project a pixel (u,v) to ground coordinates (X_forward, Y_lateral).

        Parameters
        ----------
        u, v: float
            Pixel coordinates in image (u: x, v: y).
        uav_roll_rad: float
            UAV roll (radians) from autopilot. Positive = right wing down.
        uav_pitch_rad: float
            UAV pitch (radians) from autopilot. Positive = nose up.
        h_m: float
            UAV altitude above ground in meters (must be > 0).

        Returns
        -------
        (X_forward, Y_lateral) in meters relative to UAV projection on ground,
        or None if ray does not intersect the ground plane.
        """
        # Validate altitude
        h = float(h_m)
        if h <= 0.0:
            return None

        # Normalized image coordinates (camera frame)
        x_n = (float(u) - self.cx) / self.fx
        y_n = (float(v) - self.cy) / self.fy
        # Ray in camera frame (z forward)
        r_cam = np.array([x_n, y_n, 1.0], dtype=float)

        # Camera mounting rotation: first roll then pitch (mount angles are small)
        R_mount = self._Rx(self.cam_mount_roll) @ self._Ry(self.cam_mount_pitch)

        # Vehicle/body rotation from autopilot: roll about X, pitch about Y
        R_body = self._Rx(uav_roll_rad) @ self._Ry(uav_pitch_rad)

        # Full rotation from camera frame to world frame (world frame: X forward, Y right, Z up)
        # r_world = R_body @ R_mount @ r_cam
        r_world = R_body.dot(R_mount.dot(r_cam))

        # In our world frame the origin is at UAV at height h above ground (Z = h).
        # Ray param: p(t) = origin + t * r_world, we need Z component p_z = 0
        # => h + t * r_world_z = 0 => t = -h / r_world_z
        # Only valid if r_world_z < 0 (ray points downwards)
        rz = float(r_world[2])
        if rz >= 0.0:
            # Ray does not intersect ground (points upwards or parallel)
            return None

        t = -h / rz
        p = t * r_world
        X = float(p[0])
        Y = float(p[1])
        return X, Y


# Utility constructor from fx/fy/cx/cy convenience
def make_projector_from_focal(
    fx: float, fy: float, cx: float, cy: float, cam_mount_roll_rad: float = 0.0, cam_mount_pitch_rad: float = 0.0
) -> GeoProjector:
    K = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=float)
    return GeoProjector(K, cam_mount_roll_rad=cam_mount_roll_rad, cam_mount_pitch_rad=cam_mount_pitch_rad)
