from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.app_state import AppState
from core.engineering_state import CalibrationSnapshot
from core.calibration_preflight import calibration_preflight
from simulator.service import SimulatorService


class SimulatorTab(QWidget):

    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self._state = app_state
        self._service = SimulatorService()

        self._session_label = QLabel("No session selected.")
        self._preflight_label = QLabel(
            "Select a session to validate calibration inputs."
        )
        self._preflight_label.setWordWrap(True)

        self._run_button = QPushButton("Run Calibration")
        self._run_button.setEnabled(False)

        self._output = QTextEdit()
        self._output.setReadOnly(True)

        self._run_button.clicked.connect(self._run_calibration)
        self._state.session_changed.connect(self._session_changed)

        layout = QVBoxLayout()
        layout.addWidget(self._session_label)
        layout.addWidget(self._preflight_label)
        layout.addWidget(self._run_button)
        layout.addWidget(self._output)
        self.setLayout(layout)

        # Validate an already-selected session too.
        if self._state.selected_session is not None:
            self._session_changed(self._state.selected_session)

    def _session_changed(self, session_path) -> None:
        self._run_button.setEnabled(False)

        if session_path is None:
            self._session_label.setText("No session selected.")
            self._preflight_label.setText(
                "Select a session to validate calibration inputs."
            )
            return

        self._session_label.setText(f"Selected session: {session_path.name}")
        self._apply_preflight(session_path)

    def _apply_preflight(self, session_path):
        report = calibration_preflight(session_path)

        if report.ready:
            self._preflight_label.setText(
                "Calibration preflight: READY\n"
                f"Heater power: {report.heater_power_w:.0f} W "
                f"({report.heater_power_source})"
            )
            self._run_button.setEnabled(True)
        else:
            text = "Calibration preflight: NOT READY\n" + "\n".join(
                f"• {error}" for error in report.errors
            )
            self._preflight_label.setText(text)
            self._run_button.setEnabled(False)

        return report

    def _run_calibration(self) -> None:
        session_path = self._state.selected_session
        if session_path is None:
            return

        # CRITICAL: validate again at the actual execution boundary.
        report = self._apply_preflight(session_path)
        if not report.ready:
            self._output.clear()
            self._output.append("WEBER THERMAL CALIBRATION")
            self._output.append("=" * 50)
            self._output.append(f"Session: {session_path.name}")
            self._output.append("")
            self._output.append("CALIBRATION NOT STARTED")
            for error in report.errors:
                self._output.append(f"- {error}")
            return

        self._run_button.setEnabled(False)
        self._output.clear()
        self._output.append("WEBER THERMAL CALIBRATION")
        self._output.append("=" * 50)
        self._output.append(f"Session: {session_path.name}")
        self._output.append(
            f"Validated heater power: {report.heater_power_w:.0f} W"
        )
        self._output.append("Loading measurements...")

        try:
            experiment, calibration, prediction = (
                self._service.calibrate_session(session_path)
            )
        except Exception as exc:
            self._output.append("")
            self._output.append("CALIBRATION FAILED")
            self._output.append(f"{type(exc).__name__}: {exc}")
            self._apply_preflight(session_path)
            return

        self._output.append("Measurements loaded.")
        self._output.append("")
        self._output.append(
            f"Experiment: {experiment.metadata.name}"
        )
        self._output.append(
            f"Heater: {experiment.metadata.heater_power_w:.0f} W"
        )
        self._output.append(
            f"Internal samples: {len(experiment.internal.time_seconds):,}"
        )
        self._output.append(
            f"External samples: {len(experiment.external.time_seconds):,}"
        )
        self._output.append("")
        self._output.append("CALIBRATION RESULT")
        self._output.append(f"RMSE: {calibration.rmse_c:.3f} °C")

        parameters = calibration.parameters
        self._output.append(
            f"Heater efficiency: {parameters.heater_efficiency:.3f}"
        )
        self._output.append(
            "Chamber heat capacity: "
            f"{parameters.chamber_heat_capacity_j_per_k:,.0f} J/K"
        )
        self._output.append(
            "Body heat capacity: "
            f"{parameters.body_heat_capacity_j_per_k:,.0f} J/K"
        )

        required_power = prediction.estimated_power_for_target_w
        self._output.append("")
        if required_power is None:
            self._output.append("225°F power estimate unavailable.")
        else:
            self._output.append(
                f"Estimated power for 225°F: {required_power:.0f} W"
            )

        snapshot = CalibrationSnapshot(
            session_path=session_path,
            rmse_c=calibration.rmse_c,
            required_power_w=required_power,
        )
        self._state.set_calibration(snapshot)
        self._apply_preflight(session_path)
