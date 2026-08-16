"""scandium.control.ballistics

Ballistic drop prediction utilities for fixed-wing UAV payload release.

This module provides a BallisticCalculator class that numerically integrates
the motion of a released payload under gravity and quadratic aerodynamic
drag using the Heun (predictor-corrector) method with bounded execution time.
"""
from __future__ import annotations

import logging
import math
from typing import Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

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
    """Ballistic drop dynamics and predictor for payload release."""

    def __init__(
        self,
        payload_mass_kg: float = 0.35,
        drag_coeff_cd: float = 0.45,
        cross_area_m2: float = 0.008,
        air_density_rho: float = 1.225,
        gravity_g: float = 9.80665,
        max_simulation_time_s: float = 60.0,
    ) -> None:
        self.m = float(payload_mass_kg) if payload_mass_kg > 0 else 0.35
        self.Cd = float(drag_coeff_cd) if drag_coeff_cd >= 0 else 0.45
        self.A = float(cross_area_m2) if cross_area_m2 >= 0 else 0.008
        self.rho = float(air_density_rho) if air_density_rho >= 0 else 1.225
        self.g = float(gravity_g) if gravity_g > 0 else 9.80665
        self.max_simulation_time_s = float(max_simulation_time_s)

    def _drag_acceleration(self, velocity: Vector3, wind: Vector3) -> Vector3:
        v_rel = _sub(velocity, wind)
        speed = _length(v_rel)
        if speed <= 1e-9:
            return (0.0, 0.0, 0.0)

        # Aerodinamik sürtünme kuvveti: Fd = 0.5 * rho * Cd * A * v_rel^2
        Fd = 0.5 * self.rho * self.Cd * self.A * (speed * speed)
        a_mag = Fd / max(1e-6, self.m)
        dir_unit = _scale(_unit(v_rel), -1.0)
        return _scale(dir_unit, a_mag)

    def _total_acceleration(self, velocity: Vector3, wind: Vector3) -> Vector3:
        a_drag = self._drag_acceleration(velocity, wind)
        a_grav = (0.0, 0.0, -self.g)
        return _add(a_drag, a_grav)

    def predict_drop_offset(
        self,
        uav_airspeed_xyz: Sequence[float] | float,
        uav_altitude_m: float,
        wind_xyz: Sequence[float] = (0.0, 0.0, 0.0),
        dt: float = 0.01,
    ) -> Tuple[float, float, float]:
        """Heun Predictor-Corrector integrali ile düşüş mesafesini hesaplar."""
        SAFE_FALLBACK = (0.0, 0.0, 0.0)

        # Giriş validasyonu
        if uav_altitude_m <= 0.0:
            logger.warning("predict_drop_offset: altitude_m <= 0 (%.3f); returning fallback", uav_altitude_m)
            return SAFE_FALLBACK

        if dt <= 0.0 or dt > 1.0:
            logger.warning("predict_drop_offset: unreasonable dt=%.4f; returning fallback", dt)
            return SAFE_FALLBACK

        try:
            if isinstance(uav_airspeed_xyz, (int, float)):
                v: Vector3 = (float(uav_airspeed_xyz), 0.0, 0.0)
            elif len(uav_airspeed_xyz) >= 3:
                v = (float(uav_airspeed_xyz[0]), float(uav_airspeed_xyz[1]), float(uav_airspeed_xyz[2]))
            else:
                v = (float(uav_airspeed_xyz[0]), 0.0, 0.0)

            wind: Vector3 = (float(wind_xyz[0]), float(wind_xyz[1]), float(wind_xyz[2])) if len(wind_xyz) >= 3 else (0.0, 0.0, 0.0)
        except Exception as exc:
            logger.warning("predict_drop_offset invalid input format: %s", exc)
            return SAFE_FALLBACK

        pos: Vector3 = (0.0, 0.0, float(uav_altitude_m))

        # Yatay uçuş yönü ve yanal eksen vektörleri
        horiz_v = (v[0], v[1], 0.0)
        horiz_speed = math.hypot(horiz_v[0], horiz_v[1])
        if horiz_speed == 0.0:
            forward_dir = (1.0, 0.0, 0.0)
            lateral_dir = (0.0, 1.0, 0.0)
        else:
            forward_dir = (horiz_v[0] / horiz_speed, horiz_v[1] / horiz_speed, 0.0)
            lateral_dir = (forward_dir[1], -forward_dir[0], 0.0)

        sim_time = 0.0
        max_steps = int(self.max_simulation_time_s / dt)
        steps = 0

        # Heun Entegrasyon Döngüsü (Predictor-Corrector)
        while pos[2] > 0.0 and steps < max_steps and sim_time < self.max_simulation_time_s:
            steps += 1
            a = self._total_acceleration(v, wind)

            # 1. Tahmin Adımı (Euler Predictor)
            v_pred = _add(v, _scale(a, dt))
            pos_pred = _add(pos, _scale(v, dt))

            # 2. Düzeltme Adımı (Heun Corrector)
            a_pred = self._total_acceleration(v_pred, wind)
            v_next = _add(v, _scale(_add(a, a_pred), 0.5 * dt))
            pos_next = _add(pos, _scale(_add(v, v_pred), 0.5 * dt))

            sim_time += dt

            # Zemin kesişimi (Lineer İnterpolasyon ile milisaniye hassasiyeti)
            if pos_next[2] <= 0.0:
                z0, z1 = pos[2], pos_next[2]
                frac = (z0 / (z0 - z1)) if (z0 != z1) else 0.0
                frac = max(0.0, min(1.0, frac))

                impact_x = pos[0] + (pos_next[0] - pos[0]) * frac
                impact_y = pos[1] + (pos_next[1] - pos[1]) * frac
                impact_time = sim_time - dt + (dt * frac)

                dx = (impact_x, impact_y, 0.0)
                forward_offset = _dot(dx, forward_dir)
                lateral_offset = _dot(dx, lateral_dir)

                return float(forward_offset), float(lateral_offset), float(impact_time)

            pos = pos_next
            v = v_next

        # Zaman aşımı durumunda fallback
        dx = (pos[0], pos[1], 0.0)
        return float(_dot(dx, forward_dir)), float(_dot(dx, lateral_dir)), float(sim_time)


def predict_drop_offset(
    altitude_m: float,
    airspeed_mps: float,
    wind_mps: Tuple[float, float] = (0.0, 0.0),
    payload_mass_kg: float = 0.35,
    drag_coeff_cd: float = 0.45,
    cross_area_m2: float = 0.008,
    air_density_rho: float = 1.225,
    dt: float = 0.01,
    max_simulation_time_s: float = 60.0,
) -> Tuple[float, float, float]:
    """Modül seviyesinde doğrudan fonksiyon çağrısı için sarmalayıcı."""
    calc = BallisticCalculator(
        payload_mass_kg=payload_mass_kg,
        drag_coeff_cd=drag_coeff_cd,
        cross_area_m2=cross_area_m2,
        air_density_rho=air_density_rho,
        max_simulation_time_s=max_simulation_time_s,
    )
    return calc.predict_drop_offset(
        uav_airspeed_xyz=(airspeed_mps, 0.0, 0.0),
        uav_altitude_m=altitude_m,
        wind_xyz=(wind_mps[0], wind_mps[1], 0.0),
        dt=dt,
    )
