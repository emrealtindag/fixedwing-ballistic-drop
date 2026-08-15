"""Module to project image pixels to ground plane coordinates using ray-ground intersection.

Assumptions & coordinate conventions
- World frame: right-handed, origin at the UAV's camera projection onto the ground (i.e. camera position is at (0, 0, altitude_agl_m)).
  - X axis: forward (positive ahead of the aircraft)
  - Y axis: right (positive to the aircraft's right)
  - Z axis: up (positive upwards from the ground); ground plane is Z = 0

- Camera frame (standard computer-vision convention):
  - x_c: right
  - y_c: down
  - z_c: forward (out of the camera)

- To convert a direction vector from camera frame to the world frame the following steps are applied:
  1. Permute camera axes to align with the body/world basis: camera forward -> body/world +X, camera right -> +Y, camera down -> -Z.
     This permutation matrix is encoded in _CAM_TO_BODY_PERM.
  2. Apply camera mount rotation (mount_roll, mount_pitch). These are rotations of the camera with respect to the aircraft body.
     Both mount angles are given in degrees. Positive mount_pitch_deg means the camera is pitched downwards (i.e. points more towards the ground).
  3. Apply the UAV attitude rotations (uav_roll_deg, uav_pitch_deg, yaw assumed zero). Positive roll is right-wing-down; positive pitch is nose-up.

- Intrinsics: `camera_matrix` is the 3x3 intrinsic matrix K. A pixel (u, v) is converted to a homogeneous ray in camera coordinates r_cam = inv(K) * [u, v, 1]^T.

Returned values
- (X_forward_m, Y_lateral_m): Coordinates (meters) of the ray-ground intersection point expressed in the world frame where the camera
  projection onto the ground is taken as the origin.
  - X_forward_m: meters in front of the aircraft (positive forward)
  - Y_lateral_m: meters to the right of the aircraft (positive right)

Notes on signs & edge cases
- If the ray is (nearly) parallel to the ground or points upwards such that the intersection is behind the camera, the function
  returns (inf, inf) to signal no valid forward ground intersection.
- This module intentionally keeps conventions explicit. If your system uses a different body/world axis convention (e.g. NED where Z points down), adapt the permutation and sign choices accordingly.

Example
>>> import numpy as np
>>> K = np.array([[700, 0, 640],[0,700,360],[0,0,1]])
>>> gp = GeoProjector(K, mount_pitch_deg=25.0, mount_roll_deg=0.0)
>>> gp.pixel_to_ground((640,360), altitude_agl_m=100.0, uav_roll_deg=0.0, uav_pitch_deg=0.0)
(0.0, some_value)

"""
from __future__ import annotations

from typing import Tuple

import numpy as np


# Permutation matrix that maps camera axes [x_c, y_c, z_c] (right, down, forward)
# to a body/world basis [x_b, y_b, z_b] (forward, right, up):
# x_b = z_c
# y_b = x_c
# z_b = -y_c
_CAM_TO_BODY_PERM = np.array([[0.0, 0.0, 1.0],
                              [1.0, 0.0, 0.0],
                              [0.0, -1.0, 0.0]])


def _deg2rad(deg: float) -> float:
    return float(deg) * np.pi / 180.0


def _rot_x(roll_rad: float) -> np.ndarray:
    """Rotation matrix about X axis (right-handed).

    Positive angle rotates Y -> Z.
    """
    c = np.cos(roll_rad)
    s = np.sin(roll_rad)
    return np.array([[1.0, 0.0, 0.0],
                     [0.0, c, -s],
                     [0.0, s, c]])


def _rot_y(pitch_rad: float) -> np.ndarray:
    """Rotation matrix about Y axis (right-handed).

    Positive angle rotates Z -> X.
    """
    c = np.cos(pitch_rad)
    s = np.sin(pitch_rad)
    return np.array([[c, 0.0, s],
                     [0.0, 1.0, 0.0],
                     [-s, 0.0, c]])


def _rot_z(yaw_rad: float) -> np.ndarray:
    """Rotation matrix about Z axis (right-handed).

    Positive angle rotates X -> Y.
    """
    c = np.cos(yaw_rad)
    s = np.sin(yaw_rad)
    return np.array([[c, -s, 0.0],
                     [s, c, 0.0],
                     [0.0, 0.0, 1.0]])


class GeoProjector:
    """Project image pixels to ground-plane coordinates using ray-ground intersection.

    Parameters
    - camera_matrix: 3x3 intrinsic matrix K (numpy.ndarray).
    - mount_pitch_deg: camera mount pitch relative to the aircraft body in degrees.
        Positive values mean the camera is pitched down toward the ground (common for fixed-wing mapping setups).
    - mount_roll_deg: camera mount roll relative to the aircraft body in degrees.

    The class does not model camera translation offset w.r.t. the aircraft CG; it assumes the camera center
    is located directly above the world origin at height altitude_agl_m when calling pixel_to_ground.
    If your camera has a lateral/forward/backward offset from the aircraft reference point, apply that as
    a post-translation to the returned (X_forward_m, Y_lateral_m).
    """

    def __init__(self, camera_matrix: np.ndarray, mount_pitch_deg: float = 25.0, mount_roll_deg: float = 0.0):
        if camera_matrix.shape != (3, 3):
            raise ValueError("camera_matrix must be a 3x3 numpy array")
        self.K = camera_matrix.astype(float)
        self.K_inv = np.linalg.inv(self.K)
        self.mount_pitch_deg = float(mount_pitch_deg)
        self.mount_roll_deg = float(mount_roll_deg)

        # Precompute mount rotation: rotation from camera frame (after permutation) into body frame
        # Apply mount roll (about camera's X->body Y) then mount pitch (about camera's Y->body Y after perm)
        # For clarity we build R_mount such that: v_body = R_mount @ (P @ v_cam)
        mount_roll_rad = _deg2rad(self.mount_roll_deg)
        mount_pitch_rad = _deg2rad(self.mount_pitch_deg)

        # Note: after permutation, applying roll (about forward axis) and pitch (about right axis)
        # corresponds to rotations about body axes. Build R_mount in body axes order: R_body = R_y(pitch) @ R_x(roll)
        R_mount_x = _rot_x(mount_roll_rad)
        R_mount_y = _rot_y(mount_pitch_rad)
        # R_mount_body_cam maps a vector in camera coords (after permutation) into body coords
        self.R_mount_body_cam = R_mount_y @ R_mount_x @ _CAM_TO_BODY_PERM

    def pixel_to_ground(self, pixel_xy: Tuple[int, int], altitude_agl_m: float,
                        uav_roll_deg: float = 0.0, uav_pitch_deg: float = 0.0) -> Tuple[float, float]:
        """Compute the ground intersection (X_forward_m, Y_lateral_m) for a pixel.

        Parameters
        - pixel_xy: (u, v) pixel coordinates in image (integers are accepted).
        - altitude_agl_m: altitude above ground level in meters (positive).
        - uav_roll_deg: aircraft roll angle in degrees. Positive roll = right wing down.
        - uav_pitch_deg: aircraft pitch angle in degrees. Positive pitch = nose up.

        Returns
        - (X_forward_m, Y_lateral_m): intersection point in meters in the world frame where the camera
          projection onto the ground is taken as the origin.
          If the ray does not intersect the ground in front of the camera (ray points upward or is parallel),
          (inf, inf) is returned to indicate no valid forward ground intersection.

        Raises
        - ValueError if altitude_agl_m is non-positive.
        """
        u, v = pixel_xy
        if altitude_agl_m <= 0.0:
            raise ValueError("altitude_agl_m must be positive")

        # Build the unit ray in camera coordinates (direction from camera center through pixel)
        pixel_h = np.array([float(u), float(v), 1.0])
        r_cam = self.K_inv @ pixel_h
        # We only care about direction, normalize for numerical stability
        r_cam = r_cam / np.linalg.norm(r_cam)

        # Map camera ray into body frame, then into world frame using UAV attitude
        # First: body <- camera
        r_body = self.R_mount_body_cam @ r_cam

        # Build UAV attitude rotation (body -> world). We assume yaw = 0 (unknown) and only use roll/pitch.
        roll_rad = _deg2rad(float(uav_roll_deg))
        pitch_rad = _deg2rad(float(uav_pitch_deg))
        yaw_rad = 0.0

        # R_world_body = R_z(yaw) @ R_y(pitch) @ R_x(roll)
        R_world_body = _rot_z(yaw_rad) @ _rot_y(pitch_rad) @ _rot_x(roll_rad)

        # r_world is the direction vector in world frame
        r_world = R_world_body @ r_body

        # Camera position in world coordinates: (0, 0, altitude)
        cam_pos_world = np.array([0.0, 0.0, float(altitude_agl_m)])

        # Solve for t where cam_pos_world + t * r_world intersects ground plane z=0
        # t = (z_ground - cam_z) / r_z = (0 - cam_z) / r_z
        r_world_z = float(r_world[2])
        # If ray is (nearly) parallel to ground or points upward (r_z >= 0), no forward intersection
        if np.isclose(r_world_z, 0.0, atol=1e-8) or r_world_z >= 0.0:
            return float("inf"), float("inf")

        t = -cam_pos_world[2] / r_world_z
        if t <= 0.0:
            # Intersection is behind the camera (ray points upwards) -> no valid forward intersection
            return float("inf"), float("inf")

        intersection = cam_pos_world + t * r_world

        X_forward_m = float(intersection[0])
        Y_lateral_m = float(intersection[1])

        return X_forward_m, Y_lateral_m
