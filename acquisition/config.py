from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Chef iQ BLE protocol
# ---------------------------------------------------------------------------

CHEFIQ_MANUFACTURER_ID: int = 0x05CD
CHEFIQ_MAX_PROBE_PACKET_LENGTH_BYTES: int = 18


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

DISPLAY_INTERVAL_SECONDS: float = 2.0
RECORD_INTERVAL_SECONDS: float = 2.0
STALE_TIMEOUT_SECONDS: float = 30.0


# ---------------------------------------------------------------------------
# Temperature conversion
# ---------------------------------------------------------------------------

CELSIUS_TO_FAHRENHEIT_SCALE: float = 9.0 / 5.0
CELSIUS_TO_FAHRENHEIT_OFFSET: float = 32.0


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

DATA_DIRECTORY: Path = Path("data")
SESSIONS_DIRECTORY: Path = DATA_DIRECTORY / "sessions"
SESSION_METADATA_FILENAME: str = "session.json"


@dataclass(frozen=True)
class ProbeDefinition:
    """
    match_fragment may be a complete CoreBluetooth UUID or any unique portion
    of it. This accommodates the address strings already observed on macOS.
    """

    match_fragment: str
    friendly_name: str


PROBES: tuple[ProbeDefinition, ...] = (
    ProbeDefinition(
        match_fragment="902B6F7B-D0F4-EC70-1C01-8D7DE6A68397",
        friendly_name="outside on top",
    ),
    ProbeDefinition(
        match_fragment="424F-31F7-E5C6-3C2FD749BFBE",
        friendly_name="inside in water 1",
    ),
    ProbeDefinition(
        match_fragment="551D2CE-42AA-68FB-434E-C7BD2ABBF5E3",
        friendly_name="inside in water 2",
    ),
)


@dataclass(frozen=True)
class AppConfig:
    manufacturer_id: int = CHEFIQ_MANUFACTURER_ID
    max_probe_packet_length_bytes: int = CHEFIQ_MAX_PROBE_PACKET_LENGTH_BYTES

    display_interval_seconds: float = DISPLAY_INTERVAL_SECONDS
    record_interval_seconds: float = RECORD_INTERVAL_SECONDS
    stale_timeout_seconds: float = STALE_TIMEOUT_SECONDS

    sessions_directory: Path = SESSIONS_DIRECTORY
    session_metadata_filename: str = SESSION_METADATA_FILENAME

    probes: tuple[ProbeDefinition, ...] = PROBES


CONFIG = AppConfig()
