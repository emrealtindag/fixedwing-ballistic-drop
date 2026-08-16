"""scandium.perception.tracker
ByteTrack ve Kalman Filtresi Tabanlı Hedef Takipçisi.
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np

class TargetKalmanFilter:
    """Tek bir zemin hedefinin (X, Y) koordinatlarını ve hızını süzen Kalman Filtresi."""

    def __init__(self, init_x: float, init_y: float) -> None:
        # Durum Vektörü: [x, y, vx, vy]
        self.state = np.array([init_x, init_y, 0.0, 0.0], dtype=np.float64)
        # Kovaryans Matrisi
        self.P = np.eye(4, dtype=np.float64) * 5.0
        # Durum Geçiş Matrisi (dt = 0.033s varsayılan)
        self.F = np.eye(4, dtype=np.float64)
        # Ölçüm Matrisi: Sadece [x, y] ölçülür
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float64)
        # Gürültü Matrisleri
        self.Q = np.eye(4, dtype=np.float64) * 0.1
        self.R = np.eye(2, dtype=np.float64) * 0.8

    def predict(self, dt: float = 0.033) -> Tuple[float, float]:
        self.F[0, 2] = dt
        self.F[1, 3] = dt
        self.state = self.F @ self.state
        self.P = self.F @ self.P @ self.F.T + self.Q
        return float(self.state[0]), float(self.state[1])

    def update(self, meas_x: float, meas_y: float) -> Tuple[float, float]:
        z = np.array([meas_x, meas_y], dtype=np.float64)
        y = z - (self.H @ self.state)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.state = self.state + (K @ y)
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return float(self.state[0]), float(self.state[1])
