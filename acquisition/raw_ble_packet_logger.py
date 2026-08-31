from __future__ import annotations

import csv
import threading
from datetime import datetime, timezone
from pathlib import Path


class RawBlePacketLogger:
    """Append-only raw BLE packet capture.

    This logger records what Bleak delivered before CHEF iQ parsing. It never
    changes packet bytes, ProbeState, or recorder data.
    """

    HEADER = (
        "timestamp_utc",
        "address",
        "bluetooth_name",
        "rssi_dbm",
        "manufacturer_id",
        "packet_length_bytes",
        "packet_type_hex",
        "payload_hex",
    )

    def __init__(self, path: Path, manufacturer_id: int) -> None:
        self._path = Path(path)
        self._manufacturer_id = int(manufacturer_id)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            with self._path.open("w", encoding="utf-8", newline="") as stream:
                csv.writer(stream).writerow(self.HEADER)

    @property
    def path(self) -> Path:
        return self._path

    def record(
        self,
        *,
        address: str,
        bluetooth_name: str,
        rssi: int,
        raw_packet: bytes,
    ) -> None:
        packet_type = f"0x{raw_packet[0]:02x}" if raw_packet else ""
        row = (
            datetime.now(timezone.utc).isoformat(),
            str(address),
            str(bluetooth_name),
            int(rssi),
            f"0x{self._manufacturer_id:04x}",
            len(raw_packet),
            packet_type,
            raw_packet.hex(),
        )
        with self._lock:
            with self._path.open("a", encoding="utf-8", newline="") as stream:
                csv.writer(stream).writerow(row)
