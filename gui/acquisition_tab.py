from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.acquisition_controller import (
    AcquisitionController,
)

from gui.app_state import AppState


CELSIUS_TO_FAHRENHEIT_SCALE = 9.0 / 5.0
CELSIUS_TO_FAHRENHEIT_OFFSET = 32.0


def celsius_to_fahrenheit(
    value_c: float | None,
) -> float | None:
    """
    Convert Celsius to Fahrenheit.
    """

    if value_c is None:
        return None

    return (
        value_c
        * CELSIUS_TO_FAHRENHEIT_SCALE
        + CELSIUS_TO_FAHRENHEIT_OFFSET
    )


def format_temperature(
    value_c: float | None,
) -> str:
    """
    Format a Celsius temperature for
    Fahrenheit display in the GUI.
    """

    value_f = celsius_to_fahrenheit(
        value_c
    )

    if value_f is None:
        return "---"

    return f"{value_f:.1f} °F"


class AcquisitionTab(QWidget):
    """
    User interface for Chef iQ CQ60 acquisition.

    This tab does not own the BLE worker thread.
    It acts as a view/controller for the
    application-level AcquisitionController.
    """

    def __init__(
        self,
        app_state: AppState,
        acquisition_controller: AcquisitionController,
    ) -> None:

        super().__init__()

        self._state = app_state

        self._controller = (
            acquisition_controller
        )

        # -------------------------------------------------
        # Title and overall state
        # -------------------------------------------------

        self._title = QLabel(
            "Chef iQ CQ60 Acquisition"
        )

        self._status = QLabel(
            "Recorder not running."
        )

        self._session = QLabel(
            "Session: ---"
        )

        self._sample_status = QLabel(
            "Live probes: 0"
        )

        # -------------------------------------------------
        # Live probe display
        # -------------------------------------------------

        self._probe_output = QTextEdit()

        self._probe_output.setReadOnly(
            True
        )

        # -------------------------------------------------
        # Diagnostic acquisition log
        # -------------------------------------------------

        self._diagnostic_log = QTextEdit()

        self._diagnostic_log.setReadOnly(
            True
        )

        self._diagnostic_log.setMaximumHeight(
            160
        )

        # -------------------------------------------------
        # Controls
        # -------------------------------------------------

        self._start_button = QPushButton(
            "Start Acquisition"
        )

        self._stop_button = QPushButton(
            "Stop Acquisition"
        )

        self._stop_button.setEnabled(
            False
        )

        # -------------------------------------------------
        # UI signals
        # -------------------------------------------------

        self._start_button.clicked.connect(
            self._start
        )

        self._stop_button.clicked.connect(
            self._stop
        )

        # -------------------------------------------------
        # Acquisition controller signals
        # -------------------------------------------------

        self._controller.acquisition_started.connect(
            self._acquisition_started
        )

        self._controller.acquisition_stopped.connect(
            self._acquisition_stopped
        )

        self._controller.probe_states.connect(
            self._probe_states_received
        )

        self._controller.status.connect(
            self._acquisition_status
        )

        self._controller.error.connect(
            self._acquisition_error
        )

        self._state.session_changed.connect(
            self._selected_session_changed
        )

        # -------------------------------------------------
        # Button layout
        # -------------------------------------------------

        button_layout = QGridLayout()

        button_layout.addWidget(
            self._start_button,
            0,
            0,
        )

        button_layout.addWidget(
            self._stop_button,
            0,
            1,
        )

        # -------------------------------------------------
        # Main layout
        # -------------------------------------------------

        layout = QVBoxLayout()

        layout.addWidget(
            self._title
        )

        layout.addWidget(
            self._status
        )

        layout.addWidget(
            self._session
        )

        layout.addWidget(
            self._sample_status
        )

        layout.addWidget(
            QLabel("Live Probe Data")
        )

        layout.addWidget(
            self._probe_output,
            stretch=1,
        )

        layout.addWidget(
            QLabel("Acquisition Activity")
        )

        layout.addWidget(
            self._diagnostic_log
        )

        layout.addLayout(
            button_layout
        )

        self.setLayout(
            layout
        )

        self._synchronize_ui()

    # =====================================================
    # Commands
    # =====================================================

    def _start(
        self,
    ) -> None:

        session = (
            self._state.selected_session
        )

        if session is None:
            self._status.setText(
                "Create or select an experiment before starting acquisition."
            )
            self._diagnostic_log.append(
                "No prepared session selected."
            )
            return

        session = Path(session)

        if not (
            session / "manifest.json"
        ).is_file():
            self._status.setText(
                "Selected experiment has no manifest.json."
            )
            self._diagnostic_log.append(
                f"Invalid prepared session: {session}"
            )
            return

        self._probe_output.clear()
        self._diagnostic_log.clear()

        self._sample_status.setText(
            "Live probes: 0"
        )

        self._status.setText(
            "Starting acquisition..."
        )

        self._session.setText(
            f"Session: {session.name}"
        )

        self._start_button.setEnabled(
            False
        )

        self._stop_button.setEnabled(
            True
        )

        self._controller.start(
            session
        )

    def _stop(
        self,
    ) -> None:

        self._status.setText(
            "Stopping acquisition..."
        )

        self._stop_button.setEnabled(
            False
        )

        self._controller.stop()

    # =====================================================
    # Acquisition lifecycle
    # =====================================================

    def _acquisition_started(
        self,
        session_path,
    ) -> None:

        self._status.setText(
            "Recording Chef iQ probes."
        )

        self._session.setText(
            f"Session: "
            f"{session_path.name}"
        )

        self._start_button.setEnabled(
            False
        )

        self._stop_button.setEnabled(
            True
        )

    def _acquisition_stopped(
        self,
        session_path,
    ) -> None:

        self._status.setText(
            "Recorder stopped."
        )

        self._session.setText(
            f"Last session: "
            f"{session_path.name}"
        )

        self._start_button.setEnabled(
            True
        )

        self._stop_button.setEnabled(
            False
        )

    # =====================================================
    # Diagnostic status
    # =====================================================

    def _acquisition_status(
        self,
        message: str,
    ) -> None:

        timestamp = (
            datetime.now()
            .strftime("%H:%M:%S")
        )

        self._diagnostic_log.append(
            f"{timestamp}  {message}"
        )

        self._status.setText(
            message
        )

    # =====================================================
    # Live probe data
    # =====================================================

    def _probe_states_received(
        self,
        readings,
    ) -> None:

        probe_count = len(
            readings
        )

        self._sample_status.setText(
            f"Live probes: "
            f"{probe_count}"
        )

        lines: list[str] = []

        for probe in readings:

            lines.append(
                (
                    f"{probe.friendly_name}\n"
                    f"  Food: "
                    f"{format_temperature(probe.food_temperature_c)}\n"
                    f"  Ambient: "
                    f"{format_temperature(probe.ambient_temperature_c)}\n"
                    f"  Tip 1: "
                    f"{format_temperature(probe.tip_1_temperature_c)}\n"
                    f"  Tip 2: "
                    f"{format_temperature(probe.tip_2_temperature_c)}\n"
                    f"  Tip 3: "
                    f"{format_temperature(probe.tip_3_temperature_c)}\n"
                    f"  Tip 4: "
                    f"{format_temperature(probe.tip_4_temperature_c)}\n"
                    f"  Battery: "
                    f"{probe.battery_percent}\n"
                    f"  RSSI: "
                    f"{probe.rssi}"
                )
            )

        if lines:

            self._probe_output.setPlainText(
                "\n\n".join(lines)
            )

        else:

            self._probe_output.setPlainText(
                "Waiting for Chef iQ probe data..."
            )

    # =====================================================
    # Errors
    # =====================================================

    def _acquisition_error(
        self,
        message: str,
    ) -> None:

        timestamp = (
            datetime.now()
            .strftime("%H:%M:%S")
        )

        self._status.setText(
            "Acquisition error."
        )

        self._diagnostic_log.append(
            f"{timestamp}  ERROR: "
            f"{message}"
        )

        self._probe_output.append(
            f"\nERROR: {message}"
        )

        self._start_button.setEnabled(
            True
        )

        self._stop_button.setEnabled(
            False
        )

    def _selected_session_changed(
        self,
        session_path,
    ) -> None:
        if self._controller.running:
            return

        if session_path is None:
            self._session.setText(
                "Session: ---"
            )
        else:
            self._session.setText(
                f"Prepared session: {Path(session_path).name}"
            )

        self._synchronize_ui()

    # =====================================================
    # Initial synchronization
    # =====================================================

    def _synchronize_ui(
        self,
    ) -> None:

        running = (
            self._controller.running
        )

        self._start_button.setEnabled(
            (
                not running
                and self._state.selected_session
                is not None
            )
        )

        self._stop_button.setEnabled(
            running
        )

        if running:

            self._status.setText(
                "Acquisition running."
            )

        else:

            self._status.setText(
                "Recorder not running."
            )
