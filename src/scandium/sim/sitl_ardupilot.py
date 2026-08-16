"""scandium.sim.sitl_ardupilot

ArduPilot Fixed-Wing (ArduPlane) SITL orchestrator for Scandium.
Manages sim_vehicle.py lifecycle for automated flight simulation testing.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SitlConfig:
    """ArduPilot Fixed-Wing SITL konfigürasyon parametreleri."""
    vehicle_type: str = "plane"          # Sabit kanat (ArduPlane)
    frame_type: Optional[str] = None     # Standart sabit kanat gövdesi
    home_lat: float = 40.072842
    home_lon: float = 32.866287
    home_alt: float = 584.0
    home_heading: float = 0.0
    speedup: float = 1.0
    instance: int = 0
    sysid: int = 1
    defaults_path: Optional[str] = None
    sim_address: str = "127.0.0.1"


class ArduPilotSitlOrchestrator:
    """ArduPlane SITL simülasyon süreç yöneticisi."""

    def __init__(
        self,
        ardupilot_path: Optional[Path] = None,
        config: Optional[SitlConfig] = None,
    ) -> None:
        self._ardupilot_path = ardupilot_path or self._find_ardupilot()
        self._config = config or SitlConfig()
        self._process: Optional[subprocess.Popen[str]] = None
        self._started = False

    def _find_ardupilot() -> Optional[Path]:
        candidates = [
            Path.home() / "ardupilot",
            Path("/opt/ardupilot"),
            Path("../ardupilot"),
        ]
        for candidate in candidates:
            if candidate.exists() and (candidate / "Tools" / "autotest").exists():
                return candidate
        return None

    def start(self, wait_ready: bool = True, timeout_s: float = 60.0) -> bool:
        if self._ardupilot_path is None:
            logger.error("ArduPilot kurulum dizini bulunamadı.")
            return False

        sim_vehicle = self._ardupilot_path / "Tools" / "autotest" / "sim_vehicle.py"
        if not sim_vehicle.exists():
            logger.error("sim_vehicle.py bulunamadı: %s", sim_vehicle)
            return False

        home_str = f"{self._config.home_lat},{self._config.home_lon},{self._config.home_alt},{self._config.home_heading}"

        cmd = [
            "python3",
            str(sim_vehicle),
            f"--vehicle={self._config.vehicle_type}",
            f"--home={home_str}",
            f"--speedup={self._config.speedup}",
            f"--instance={self._config.instance}",
            f"--sysid={self._config.sysid}",
            "--no-mavproxy",
            "-w",
        ]

        if self._config.frame_type:
            cmd.append(f"--frame={self._config.frame_type}")

        if self._config.defaults_path:
            cmd.append(f"--add-param-file={self._config.defaults_path}")

        try:
            logger.info("ArduPlane SITL başlatılıyor (Vehicle: %s)...", self._config.vehicle_type)
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self._ardupilot_path),
            )

            if wait_ready:
                self._wait_for_ready(timeout_s)

            self._started = True
            logger.info("SITL başarıyla başlatıldı (PID: %d)", self._process.pid)
            return True
        except Exception as exc:
            logger.error("SITL başlatma hatası: %s", exc)
            return False

    def _wait_for_ready(self, timeout_s: float) -> None:
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            if self._process is None or self._process.poll() is not None:
                raise RuntimeError("SITL süreci beklenmedik şekilde kapandı.")
            time.sleep(1.0)
            if time.time() - start_time > 5.0:
                break

    def stop(self) -> None:
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
            finally:
                self._process = None
                self._started = False
                logger.info("SITL durduruldu.")

    @property
    def connection_string(self) -> str:
        port = 14550 + self._config.instance * 10
        return f"udp:{self._config.sim_address}:{port}"

    def __enter__(self) -> "ArduPilotSitlOrchestrator":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
