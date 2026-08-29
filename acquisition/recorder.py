import csv
import re
from pathlib import Path

from acquisition.config import (
    CELSIUS_TO_FAHRENHEIT_OFFSET,
    CELSIUS_TO_FAHRENHEIT_SCALE,
)
from acquisition.models import ProbeState, utc_now
from acquisition.session import Session


CSV_COLUMNS: tuple[str, ...] = (
    "timestamp_utc",
    "probe_name",
    "probe_address",
    "rssi_dbm",

    "food_temperature_c",
    "food_temperature_f",

    "ambient_temperature_c",
    "ambient_temperature_f",

    "tip_1_temperature_c",
    "tip_1_temperature_f",

    "tip_2_temperature_c",
    "tip_2_temperature_f",

    "tip_3_temperature_c",
    "tip_3_temperature_f",

    "tip_4_temperature_c",
    "tip_4_temperature_f",

    "battery_percent",
)


INVALID_FILENAME_CHARACTER_PATTERN: str = r"[^A-Za-z0-9_-]+"
FILENAME_WORD_SEPARATOR: str = "_"
CSV_FILE_EXTENSION: str = ".csv"


def celsius_to_fahrenheit(
    temperature_c: float | None,
) -> float | None:

    if temperature_c is None:
        return None

    return (
        temperature_c
        * CELSIUS_TO_FAHRENHEIT_SCALE
        + CELSIUS_TO_FAHRENHEIT_OFFSET
    )


def safe_filename(name: str) -> str:

    normalized = name.strip().replace(
        " ",
        FILENAME_WORD_SEPARATOR,
    )

    normalized = re.sub(
        INVALID_FILENAME_CHARACTER_PATTERN,
        FILENAME_WORD_SEPARATOR,
        normalized,
    )

    return normalized.lower()


class SessionRecorder:
    """
    Creates one CSV lazily for every probe appearing in a session.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:

        self._session = session
        self._initialized_files: set[Path] = set()

    def record(
        self,
        state: ProbeState,
    ) -> None:

        path = self._path_for(state)

        self._ensure_header(path)

        row = self._make_row(state)

        with path.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS,
            )

            writer.writerow(row)

    def _path_for(
        self,
        state: ProbeState,
    ) -> Path:

        filename = (
            safe_filename(state.friendly_name)
            + CSV_FILE_EXTENSION
        )

        return self._session.directory / filename

    def _ensure_header(
        self,
        path: Path,
    ) -> None:

        if path in self._initialized_files:
            return

        with path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS,
            )

            writer.writeheader()

        self._initialized_files.add(path)

    @staticmethod
    def _make_row(
        state: ProbeState,
    ) -> dict[str, object]:

        return {
            "timestamp_utc":
                utc_now().isoformat(),

            "probe_name":
                state.friendly_name,

            "probe_address":
                state.address,

            "rssi_dbm":
                state.rssi,

            "food_temperature_c":
                state.food_temperature_c,

            "food_temperature_f":
                celsius_to_fahrenheit(
                    state.food_temperature_c
                ),

            "ambient_temperature_c":
                state.ambient_temperature_c,

            "ambient_temperature_f":
                celsius_to_fahrenheit(
                    state.ambient_temperature_c
                ),

            "tip_1_temperature_c":
                state.tip_1_temperature_c,

            "tip_1_temperature_f":
                celsius_to_fahrenheit(
                    state.tip_1_temperature_c
                ),

            "tip_2_temperature_c":
                state.tip_2_temperature_c,

            "tip_2_temperature_f":
                celsius_to_fahrenheit(
                    state.tip_2_temperature_c
                ),

            "tip_3_temperature_c":
                state.tip_3_temperature_c,

            "tip_3_temperature_f":
                celsius_to_fahrenheit(
                    state.tip_3_temperature_c
                ),

            "tip_4_temperature_c":
                state.tip_4_temperature_c,

            "tip_4_temperature_f":
                celsius_to_fahrenheit(
                    state.tip_4_temperature_c
                ),

            "battery_percent":
                state.battery_percent,
        }
