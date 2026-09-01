import asyncio
import threading
import traceback

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
)

from acquisition.ble_scanner import ChefIqScanner
from acquisition.config import CONFIG
from acquisition.probe_registry import ProbeRegistry
from acquisition.probe_service import ProbeService
from acquisition.recorder import SessionRecorder
from acquisition.session import SessionManager

from core.engineering_state import (
    LiveProbeReading,
    utc_now,
)

from core.experiment_manifest import (
    complete_manifest,
    load_manifest,
)


class AcquisitionWorker(QObject):
    """
    Performs BLE acquisition in a background QThread.

    Acquisition attaches to an experiment/session that already exists.
    It never creates a second session behind the GUI's back.
    """

    started = Signal(object)
    stopped = Signal(object)
    probe_states = Signal(object)
    status = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        session_directory: Path,
    ) -> None:
        super().__init__()

        self._session_directory = Path(
            session_directory
        )
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        self._stop_event.set()

    @Slot()
    def run(self) -> None:
        try:
            asyncio.run(
                self._run_async()
            )
        except Exception as exc:
            traceback.print_exc()
            self.error.emit(
                f"{type(exc).__name__}: {exc}"
            )
        finally:
            self.finished.emit()

    async def _run_async(
        self,
    ) -> None:
        self.status.emit(
            "Acquisition worker started"
        )

        session_root = (
            self._session_directory.parent
        )

        acquisition_config = replace(
            CONFIG,
            sessions_directory=session_root,
        )

        self.status.emit(
            "Acquisition configuration loaded"
        )

        registry = ProbeRegistry(
            acquisition_config.probes
        )

        probe_service = ProbeService(
            registry
        )

        session_manager = SessionManager(
            acquisition_config
        )

        # -------------------------------------------------
        # Attach to the prepared experiment.
        # -------------------------------------------------

        session = session_manager.open_session(
            self._session_directory
        )

        # Validate manifest structure, but do not require CSV files yet:
        # acquisition is about to create them.
        load_manifest(
            session.directory,
            validate_files=False,
        )

        self.status.emit(
            f"Using prepared session: "
            f"{session.directory.name}"
        )

        recorder = SessionRecorder(
            session
        )

        self.status.emit(
            "Session recorder created"
        )

        scanner = ChefIqScanner(
            acquisition_config,
            probe_service,
            raw_packet_directory=session.directory,
        )

        self.status.emit(
            "Starting BLE scanner"
        )

        await scanner.start()

        self.status.emit(
            "BLE scanner started"
        )

        self.started.emit(
            session.directory
        )

        sample_cycle = 0
        first_probe_seen = False

        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(
                    acquisition_config
                    .record_interval_seconds
                )

                states = (
                    probe_service
                    .get_states()
                )

                probe_count = len(
                    states
                )

                self.status.emit(
                    f"Probe states: "
                    f"{probe_count}"
                )

                if (
                    probe_count > 0
                    and not first_probe_seen
                ):
                    first_probe_seen = True
                    self.status.emit(
                        "First probe state received"
                    )

                for state in states:
                    recorder.record(
                        state
                    )

                if states:
                    sample_cycle += 1
                    self.status.emit(
                        f"Recorded sample cycle "
                        f"{sample_cycle}"
                    )

                readings = tuple(
                    self._to_live_reading(
                        state
                    )
                    for state in states
                )

                self.probe_states.emit(
                    readings
                )

        finally:
            self.status.emit(
                "Stopping BLE scanner"
            )

            await scanner.stop()

            self.status.emit(
                "BLE scanner stopped"
            )

            complete_manifest(
                session.directory
            )

            self.status.emit(
                "Experiment manifest completed"
            )

            self.stopped.emit(
                session.directory
            )

            self.status.emit(
                "Acquisition stopped cleanly"
            )

    @staticmethod
    def _to_live_reading(
        state,
    ) -> LiveProbeReading:
        return LiveProbeReading(
            address=state.address,
            friendly_name=(
                state.friendly_name
            ),
            food_temperature_c=(
                state.food_temperature_c
            ),
            ambient_temperature_c=(
                state.ambient_temperature_c
            ),
            tip_1_temperature_c=(
                state.tip_1_temperature_c
            ),
            tip_2_temperature_c=(
                state.tip_2_temperature_c
            ),
            tip_3_temperature_c=(
                state.tip_3_temperature_c
            ),
            tip_4_temperature_c=(
                state.tip_4_temperature_c
            ),
            battery_percent=(
                state.battery_percent
            ),
            rssi=state.rssi,
            timestamp_utc=utc_now(),
        )


class AcquisitionController(QObject):
    acquisition_started = Signal(object)
    acquisition_stopped = Signal(object)
    probe_states = Signal(object)
    status = Signal(str)
    error = Signal(str)

    def __init__(
        self,
    ) -> None:
        super().__init__()

        self._thread: QThread | None = None
        self._worker: AcquisitionWorker | None = None

    @property
    def running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.isRunning()
        )

    def start(
        self,
        session_directory: Path,
    ) -> None:
        """
        Start acquisition in an existing prepared session.
        """
        if self.running:
            self.status.emit(
                "Acquisition is already running"
            )
            return

        session_directory = Path(
            session_directory
        )

        if not (
            session_directory
            / "manifest.json"
        ).is_file():
            self.error.emit(
                "Selected session has no manifest.json. "
                "Create/select an experiment before starting acquisition."
            )
            return

        self._thread = QThread()

        self._worker = AcquisitionWorker(
            session_directory=session_directory
        )

        self._worker.moveToThread(
            self._thread
        )

        self._thread.started.connect(
            self._worker.run
        )

        self._worker.started.connect(
            self.acquisition_started
        )
        self._worker.stopped.connect(
            self.acquisition_stopped
        )
        self._worker.probe_states.connect(
            self.probe_states
        )
        self._worker.status.connect(
            self.status
        )
        self._worker.error.connect(
            self.error
        )

        self._worker.finished.connect(
            self._thread.quit
        )
        self._worker.finished.connect(
            self._worker.deleteLater
        )
        self._thread.finished.connect(
            self._thread.deleteLater
        )
        self._thread.finished.connect(
            self._cleanup
        )

        self._thread.start()

    def stop(self) -> None:
        if self._worker is None:
            self.status.emit(
                "Acquisition is not running"
            )
            return

        self.status.emit(
            "Stop requested"
        )
        self._worker.request_stop()

    def _cleanup(self) -> None:
        self._worker = None
        self._thread = None
