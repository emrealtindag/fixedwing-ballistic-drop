"""scandium.control.ballistics

Ballistic drop prediction utilities for fixed-wing UAV payload release.

This module provides a BallisticCalculator class that numerically integrates
the motion of a released payload under gravity and quadratic aerodynamic
drag using the Heun (predictor-corrector) method.
"""
from __future__ import annotations

from typing import Sequence, Tuple
import math

Vector3 = Tuple[float, float, float]


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a: Vector3, s: float) -> Vector3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _length(a: Vector3) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _unit(a: Vector3) -> Vector3:
    l = _length(a)
    if l == 0.0:
        return (0.0, 0.0, 0.0)
    return (a[0] / l, a[1] / l, a[2] / l)


class BallisticCalculator:
    """Ballistic drop dynamics and predictor for payload release.

    The model integrates the motion of a point-mass payload under gravity and
    quadratic aerodynamic drag:

        F_d = 0.5 * rho * C_d * A * |v_rel|^2

    where v_rel is the velocity of the payload relative to the air (v - wind).
    The drag acceleration is applied opposite to the relative velocity vector.

    The integration uses Heun's method (explicit trapezoidal / predictor-corrector)
    with a fixed time step `dt` until the payload altitude reaches or goes below
    zero (ground impact).

    Parameters
    ----------
    payload_mass_kg: float
        Mass of the payload in kilograms. Default 0.35 kg.
    drag_coeff_cd: float
        Dimensionless drag coefficient C_d. Default 0.45.
    cross_area_m2: float
        Frontal cross-sectional area in square meters. Default 0.008 m^2.
    air_density_rho: float
        Air density in kg/m^3. Default 1.225 (sea level ISA).
    gravity_g: float
        Gravity acceleration magnitude in m/s^2. Default 9.80665.
    """

    def __init__(
        self,
        payload_mass_kg: float = 0.35,
        drag_coeff_cd: float = 0.45,
        cross_area_m2: float = 0.008,
        air_density_rho: float = 1.225,
        gravity_g: float = 9.80665,
    ) -> None:
        if payload_mass_kg <= 0.0:
            raise ValueError("payload_mass_kg must be positive")
        if cross_area_m2 < 0.0:
            raise ValueError("cross_area_m2 must be non-negative")
        if air_density_rho < 0.0:
            raise ValueError("air_density_rho must be non-negative")

        self.m = float(payload_mass_kg)
        self.Cd = float(drag_coeff_cd)
        self.A = float(cross_area_m2)
        self.rho = float(air_density_rho)
        self.g = float(gravity_g)

    def _drag_acceleration(self, velocity: Vector3, wind: Vector3) -> Vector3:
        """Compute drag acceleration vector for a given velocity and wind.

        Parameters
        ----------
        velocity: Vector3
            Payload ground-relative velocity (m/s).
        wind: Vector3
            Wind velocity (m/s) in ground frame (air motion relative to ground).

        Returns
        -------
        Vector3
            Acceleration (m/s^2) produced by aerodynamic drag (points opposite
            the relative velocity to the air).
        """
        # Relative velocity to air: v_rel = v - wind
        v_rel = _sub(velocity, wind)
        speed = _length(v_rel)
        if speed <= 0.0:
            return (0.0, 0.0, 0.0)

        # Quadratic drag magnitude: 0.5 * rho * Cd * A * speed^2
        Fd = 0.5 * self.rho * self.Cd * self.A * (speed * speed)
        # Acceleration magnitude = Fd / m
        a_mag = Fd / self.m
        # Direction opposite v_rel
        dir_unit = _scale(_unit(v_rel), -1.0)
        return _scale(dir_unit, a_mag)

    def _total_acceleration(self, velocity: Vector3, wind: Vector3) -> Vector3:
        """Total acceleration including drag and gravity.

        Gravity acts in negative z direction: (0, 0, -g).
        """
        a_drag = self._drag_acceleration(velocity, wind)
        a_grav = (0.0, 0.0, -self.g)
        return _add(a_drag, a_grav)

    def predict_drop_offset(
        self,
        uav_airspeed_xyz: Sequence[float],
        uav_altitude_m: float,
        wind_xyz: Sequence[float] = (0.0, 0.0, 0.0),
        dt: float = 0.01,
    ) -> Tuple[float, float, float]:
        """Predict horizontal offsets and time to impact for a released payload.

        The function integrates the payload trajectory starting from the release
        point at horizontal position (0,0) and vertical position `uav_altitude_m`.
        The payload initial velocity is set to `uav_airspeed_xyz` (ground-relative).

        Parameters
        ----------
        uav_airspeed_xyz: Sequence[float]
            3-element sequence (vx, vy, vz) describing the UAV (release)
            velocity in meters per second relative to ground. Typically vz ~= 0.
        uav_altitude_m: float
            Release altitude above ground in meters. Must be >= 0.
        wind_xyz: Sequence[float], optional
            3-element wind velocity vector (wx, wy, wz) in m/s describing air
            motion relative to ground. Default (0,0,0) meaning still air.
        dt: float, optional
            Integration time step in seconds. Default 0.01 s.

        Returns
        -------
        forward_offset_m: float
            Distance (m) traveled in the UAV's forward horizontal direction
            from release until impact.
        lateral_offset_m: float
            Lateral displacement (m) to the right of the UAV's forward
            direction (positive = right, negative = left).
        time_to_impact_s: float
            Time in seconds from release until ground impact.
        """
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        if uav_altitude_m <= 0.0:
            return 0.0, 0.0, 0.0

        # Ensure inputs are 3-element tuples
        if len(uav_airspeed_xyz) != 3:
            raise ValueError("uav_airspeed_xyz must be a 3-element sequence")
        if len(wind_xyz) != 3:
            raise ValueError("wind_xyz must be a 3-element sequence")

        v: Vector3 = (float(uav_airspeed_xyz[0]), float(uav_airspeed_xyz[1]), float(uav_airspeed_xyz[2]))
        wind: Vector3 = (float(wind_xyz[0]), float(wind_xyz[1]), float(wind_xyz[2]))
        pos: Vector3 = (0.0, 0.0, float(uav_altitude_m))

        # Prepare horizontal forward and lateral directions using initial horizontal velocity
        horiz_v = (v[0], v[1], 0.0)
        horiz_speed = math.hypot(horiz_v[0], horiz_v[1])
        if horiz_speed == 0.0:
            # No defined forward direction: treat forward as +x, lateral as +y
            forward_dir = (1.0, 0.0, 0.0)
            lateral_dir = (0.0, 1.0, 0.0)
        else:
            forward_dir = (horiz_v[0] / horiz_speed, horiz_v[1] / horiz_speed, 0.0)
            # Right-handed lateral direction (90 degrees clockwise in XY plane)
            lateral_dir = (forward_dir[1], -forward_dir[0], 0.0)

        time = 0.0

        # Integration loop using Heun's method
        # Stop if altitude drops to or below zero. Keep the last step intersecting ground
        # for slightly better timing/position by linear interpolation between last two points.
        max_steps = 10_000_000  # safety cap to avoid infinite loops
        steps = 0

        while pos[2] > 0.0 and steps < max_steps:
            steps += 1
            a = self._total_acceleration(v, wind)

            # Predictor step: explicit Euler predictor
            v_pred = _add(v, _scale(a, dt))
            pos_pred = _add(pos, _scale(v, dt))

            # Compute acceleration at predicted state
            a_pred = self._total_acceleration(v_pred, wind)

            # Corrector step (Heun): average accelerations and velocities
            v_next = _add(v, _scale(_add(a, a_pred), 0.5 * dt))
            pos_next = _add(pos, _scale(_add(v, v_pred), 0.5 * dt))

            time += dt

            # If pos_next crosses ground (z <= 0), perform linear interpolation between
            # pos and pos_next to estimate better impact time and position.
            if pos_next[2] <= 0.0:
                # fraction of the step when z reached zero (linear interp in z)
                z0 = pos[2]
                z1 = pos_next[2]
                if z0 == z1:
                    frac = 0.0
                else:
                    frac = z0 / (z0 - z1)
                    frac = max(0.0, min(1.0, frac))

                # Interpolate position and time
                impact_pos = (
                    pos[0] + (pos_next[0] - pos[0]) * frac,
                    pos[1] + (pos_next[1] - pos[1]) * frac,
                    0.0,
                )
                impact_time = time - dt + dt * frac

                # Compute horizontal offset relative to release
                dx = (impact_pos[0], impact_pos[1], 0.0)
                forward_offset = _dot(dx, forward_dir)
                lateral_offset = _dot(dx, lateral_dir)

                return float(forward_offset), float(lateral_offset), float(impact_time)

            # Otherwise advance
            pos = pos_next
            v = v_next

        # If loop ends without crossing ground, return current horizontal displacement and time
        dx = (pos[0], pos[1], 0.0)
        forward_offset = _dot(dx, forward_dir)
        lateral_offset = _dot(dx, lateral_dir)
        return float(forward_offset), float(lateral_offset), float(time)
