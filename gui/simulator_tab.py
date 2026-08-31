from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.app_state import AppState

from core.engineering_state import CalibrationSnapshot

from simulator.service import (
    SimulatorService,
)


class SimulatorTab(QWidget):

    def __init__(
        self,
        app_state: AppState,
    ) -> None:

        super().__init__()

        self._state = app_state
        self._service = SimulatorService()

        self._session_label = QLabel(
            "No session selected."
        )

        self._run_button = QPushButton(
            "Run Calibration"
        )

        self._run_button.setEnabled(
            False
        )

        self._output = QTextEdit()
        self._output.setReadOnly(True)

        self._run_button.clicked.connect(
            self._run_calibration
        )

        self._state.session_changed.connect(
            self._session_changed
        )

        layout = QVBoxLayout()

        layout.addWidget(
            self._session_label
        )

        layout.addWidget(
            self._run_button
        )

        layout.addWidget(
            self._output
        )

        self.setLayout(layout)

    def _session_changed(
        self,
        session_path,
    ) -> None:

        if session_path is None:

            self._session_label.setText(
                "No session selected."
            )

            self._run_button.setEnabled(
                False
            )

            return

        self._session_label.setText(
            f"Selected session: "
            f"{session_path.name}"
        )

        self._run_button.setEnabled(
            True
        )

        self._output.append(
            f"Session selected: "
            f"{session_path}"
        )

    def _run_calibration(
        self,
    ) -> None:

        session_path = (
            self._state.selected_session
        )

        if session_path is None:
            return

        self._run_button.setEnabled(
            False
        )

        self._output.clear()

        self._output.append(
            "WEBER THERMAL CALIBRATION"
        )

        self._output.append(
            "=" * 50
        )

        self._output.append(
            f"Session: {session_path.name}"
        )

        self._output.append(
            ""
        )

        self._output.append(
            "Loading measurements..."
        )

        try:

            (
                experiment,
                calibration,
                prediction,
            ) = (
                self._service
                .calibrate_session(
                    session_path
                )
            )

        except Exception as exc:

            self._output.append("")
            self._output.append(
                "CALIBRATION FAILED"
            )

            self._output.append(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            self._run_button.setEnabled(
                True
            )

            return

        self._output.append(
            "Measurements loaded."
        )

        self._output.append("")
        self._output.append(
            f"Experiment: "
            f"{experiment.metadata.name}"
        )

        self._output.append(
            f"Heater: "
            f"{experiment.metadata.heater_power_w:.0f} W"
        )

        self._output.append(
            f"Internal samples: "
            f"{len(experiment.internal.time_seconds):,}"
        )

        self._output.append(
            f"External samples: "
            f"{len(experiment.external.time_seconds):,}"
        )

        self._output.append("")
        self._output.append(
            "CALIBRATION RESULT"
        )

        self._output.append(
            f"RMSE: "
            f"{calibration.rmse_c:.3f} °C"
        )

        parameters = (
            calibration.parameters
        )

        self._output.append(
            f"Heater efficiency: "
            f"{parameters.heater_efficiency:.3f}"
        )

        self._output.append(
            f"Chamber heat capacity: "
            f"{parameters.chamber_heat_capacity_j_per_k:,.0f} J/K"
        )

        self._output.append(
            f"Body heat capacity: "
            f"{parameters.body_heat_capacity_j_per_k:,.0f} J/K"
        )

        required_power = (
            prediction
            .estimated_power_for_target_w
        )

        self._output.append("")

        if required_power is None:

            self._output.append(
                "225°F power estimate unavailable."
            )

        else:

            self._output.append(
                f"Estimated power for 225°F: "
                f"{required_power:.0f} W"
            )

        snapshot = CalibrationSnapshot(
            session_path=session_path,
            rmse_c=calibration.rmse_c,
            required_power_w=required_power,
        )

        self._state.set_calibration(
            snapshot
        )

        self._run_button.setEnabled(
            True
        )
