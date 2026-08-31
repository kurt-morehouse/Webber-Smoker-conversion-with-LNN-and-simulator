from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class CalibrationPreflight:
    ready: bool
    heater_power_w: float | None
    heater_power_source: str | None
    errors: tuple[str, ...]


def calibration_preflight(session_path: Path) -> CalibrationPreflight:
    """Cheap validation that MUST complete before calibration starts."""
    session_path = Path(session_path)
    manifest_path = session_path / "manifest.json"
    errors: list[str] = []

    if not manifest_path.is_file():
        return CalibrationPreflight(
            False, None, None,
            (f"Missing manifest.json: {manifest_path}",),
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return CalibrationPreflight(
            False, None, None,
            (f"Cannot read manifest.json: {type(exc).__name__}: {exc}",),
        )

    heater = manifest.get("heater") or {}
    commanded = heater.get("commanded_power_w")
    rated = heater.get("rated_power_w")

    def positive(value):
        try:
            return value is not None and float(value) > 0
        except (TypeError, ValueError):
            return False

    if positive(commanded):
        watts = float(commanded)
        source = "heater.commanded_power_w"
    elif positive(rated):
        watts = float(rated)
        source = "heater.rated_power_w"
    else:
        watts = None
        source = None
        errors.append(
            "Heater power is missing. Set heater.commanded_power_w "
            "or heater.rated_power_w to a positive value."
        )

    # Probe file validation is deliberately performed from raw manifest JSON,
    # so this check itself cannot launch/load the simulator.
    for probe in manifest.get("probes") or []:
        filename = (
            probe.get("data_file")
            or probe.get("csv_file")
            or probe.get("filename")
        )
        if filename:
            path = session_path / filename
            if not path.is_file():
                errors.append(f"Missing probe data file: {path}")

    return CalibrationPreflight(
        ready=not errors,
        heater_power_w=watts,
        heater_power_source=source,
        errors=tuple(errors),
    )
