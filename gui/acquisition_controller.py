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
)


class AcquisitionWorker(QObject):
    """
    Performs BLE acquisition in a background QThread.

    The worker owns its own asyncio event loop through asyncio.run().
    """

    started = Signal(object)
    stopped = Signal(object)

    probe_states = Signal(object)

    status = Signal(str)
    error = Signal(str)

    finished = Signal()

    def __init__(
        self,
        session_root: Path,
    ) -> None:

        super().__init__()

        self._session_root = session_root
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        """
        Request a graceful stop.

        The acquisition loop checks this event once per
        recording interval.
        """

        self._stop_event.set()

    @Slot()
    def run(self) -> None:
        """
        Entry point executed by the QThread.
        """

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
        """
        Main asynchronous acquisition loop.
        """

        self.status.emit(
            "Acquisition worker started"
        )

        acquisition_config = replace(
            CONFIG,
            sessions_directory=self._session_root,
        )

        self.status.emit(
            "Acquisition configuration loaded"
        )

        # -------------------------------------------------
        # Build acquisition services
        # -------------------------------------------------

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
        # Create experiment/session
        # -------------------------------------------------

        session = (
            session_manager.create_session()
        )

        self.status.emit(
            f"Session created: "
            f"{session.directory.name}"
        )

        session_manager.create_manifest(
            session=session,
            probe_definitions=(
                acquisition_config.probes
            ),
        )

        self.status.emit(
            "Experiment manifest created"
        )

        recorder = SessionRecorder(
            session
        )

        self.status.emit(
            "Session recorder created"
        )

        # -------------------------------------------------
        # BLE scanner
        # -------------------------------------------------

        scanner = ChefIqScanner(
            config,
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

        # Only report acquisition started after BLE
        # scanning has successfully started.
        self.started.emit(
            session.directory
        )

        sample_cycle = 0
        first_probe_seen = False

        # -------------------------------------------------
        # Recording loop
        # -------------------------------------------------

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

                # Record one row for each currently
                # known probe.
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

                # Publish current readings to the GUI /
                # shared engineering state.
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

            # -------------------------------------------------
            # Graceful shutdown
            # -------------------------------------------------

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
        """
        Convert acquisition ProbeState into the shared
        engineering-state representation.
        """

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
    """
    Application-level controller for the acquisition worker.

    The controller lives in the GUI thread.

    The AcquisitionWorker lives in a background QThread.
    """

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
        """
        True while the background acquisition thread exists
        and is running.
        """

        return (
            self._thread is not None
            and self._thread.isRunning()
        )

    def start(
        self,
        session_root: Path,
    ) -> None:
        """
        Start a new acquisition session.
        """

        if self.running:

            self.status.emit(
                "Acquisition is already running"
            )

            return

        self._thread = QThread()

        self._worker = AcquisitionWorker(
            session_root=session_root
        )

        self._worker.moveToThread(
            self._thread
        )

        # -------------------------------------------------
        # Start worker
        # -------------------------------------------------

        self._thread.started.connect(
            self._worker.run
        )

        # -------------------------------------------------
        # Forward worker signals
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Thread cleanup
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Start QThread
        # -------------------------------------------------

        self._thread.start()

    def stop(self) -> None:
        """
        Request a graceful acquisition shutdown.
        """

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
        """
        Clear references after the worker thread exits.
        """

        self._worker = None
        self._thread = None
