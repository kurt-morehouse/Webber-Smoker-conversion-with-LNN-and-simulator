from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.digital_twin import DigitalTwinManager
from core.engineering_journal import write_engineering_report
from core.sensitivity_analysis import heater_power_sweep
from gui.app_state import AppState


class SimulatorTab(QWidget):
    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self._state = app_state
        self._twins = DigitalTwinManager()
        self._twin = None

        self._session_label = QLabel("No calibrated session selected.")

        self._heater_watts = QDoubleSpinBox()
        self._heater_watts.setRange(0.0, 10000.0)
        self._heater_watts.setDecimals(0)
        self._heater_watts.setValue(1100.0)
        self._heater_watts.setSuffix(" W")

        self._outside_f = QDoubleSpinBox()
        self._outside_f.setRange(-100.0, 200.0)
        self._outside_f.setValue(75.0)
        self._outside_f.setSuffix(" °F")

        self._initial_f = QDoubleSpinBox()
        self._initial_f.setRange(-100.0, 1000.0)
        self._initial_f.setValue(75.0)
        self._initial_f.setSuffix(" °F")

        self._target_f = QDoubleSpinBox()
        self._target_f.setRange(-100.0, 1000.0)
        self._target_f.setValue(225.0)
        self._target_f.setSuffix(" °F")

        self._duration_hours = QDoubleSpinBox()
        self._duration_hours.setRange(0.0, 48.0)
        self._duration_hours.setDecimals(2)
        self._duration_hours.setValue(3.0)
        self._duration_hours.setSuffix(" h")

        form = QFormLayout()
        form.addRow("Heater power:", self._heater_watts)
        form.addRow("Outside ambient:", self._outside_f)
        form.addRow("Initial chamber:", self._initial_f)
        form.addRow("Target chamber:", self._target_f)
        form.addRow("Prediction time:", self._duration_hours)

        # Engineering dashboard
        self._dashboard = QTextEdit()
        self._dashboard.setReadOnly(True)

        self._run_button = QPushButton("Run Digital Twin")
        self._run_button.setEnabled(False)
        self._run_button.clicked.connect(self._run_prediction)

        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout()
        dashboard_layout.addWidget(self._run_button)
        dashboard_layout.addWidget(self._dashboard, stretch=1)
        dashboard_page.setLayout(dashboard_layout)

        # Sensitivity analysis
        self._sensitivity_button = QPushButton("Run Heater-Power Sensitivity")
        self._sensitivity_button.setEnabled(False)
        self._sensitivity_button.clicked.connect(self._run_sensitivity)

        self._sensitivity_table = QTableWidget()
        self._sensitivity_table.setColumnCount(4)
        self._sensitivity_table.setHorizontalHeaderLabels(
            ["Power (W)", "Equilibrium (°F)", "At prediction time (°F)", "Time to target"]
        )
        self._sensitivity_table.horizontalHeader().setStretchLastSection(True)

        sensitivity_page = QWidget()
        sensitivity_layout = QVBoxLayout()
        sensitivity_layout.addWidget(
            QLabel("Sweep: ±50% around selected heater power")
        )
        sensitivity_layout.addWidget(self._sensitivity_button)
        sensitivity_layout.addWidget(self._sensitivity_table, stretch=1)
        sensitivity_page.setLayout(sensitivity_layout)

        # Engineering journal
        self._journal_button = QPushButton("Generate Engineering Report")
        self._journal_button.setEnabled(False)
        self._journal_button.clicked.connect(self._generate_report)
        self._journal_output = QTextEdit()
        self._journal_output.setReadOnly(True)

        journal_page = QWidget()
        journal_layout = QVBoxLayout()
        journal_layout.addWidget(self._journal_button)
        journal_layout.addWidget(self._journal_output, stretch=1)
        journal_page.setLayout(journal_layout)

        self._tabs = QTabWidget()
        self._tabs.addTab(dashboard_page, "Engineering Dashboard")
        self._tabs.addTab(sensitivity_page, "Sensitivity")
        self._tabs.addTab(journal_page, "Engineering Journal")

        layout = QVBoxLayout()
        layout.addWidget(self._session_label)
        layout.addLayout(form)
        layout.addWidget(self._tabs, stretch=1)
        self.setLayout(layout)

        self._state.session_changed.connect(self._session_changed)
        self._session_changed(self._state.selected_session)

    def _session_changed(self, session_path) -> None:
        self._twin = None

        if session_path is None:
            self._session_label.setText("No calibrated session selected.")
            self._set_enabled(False)
            return

        try:
            twin = self._twins.load(session_path)
        except FileNotFoundError:
            self._session_label.setText(
                f"{session_path.name}: no saved calibration"
            )
            self._dashboard.setPlainText(
                "Analyze and save a chamber calibration in Sessions first."
            )
            self._set_enabled(False)
            return
        except Exception as exc:
            self._session_label.setText("Digital twin load failed")
            self._dashboard.setPlainText(
                f"{type(exc).__name__}: {exc}"
            )
            self._set_enabled(False)
            return

        self._twin = twin
        calibration = twin.calibration

        self._session_label.setText(
            f"Digital twin: {session_path.name} — "
            f"{calibration.source_probe} / {calibration.source_channel}"
        )
        self._heater_watts.setValue(calibration.heater_power_w)
        self._outside_f.setValue(calibration.outside_temperature_f)
        self._initial_f.setValue(calibration.initial_temperature_f)
        self._set_enabled(True)
        self._show_model_summary()

    def _set_enabled(self, enabled: bool) -> None:
        self._run_button.setEnabled(enabled)
        self._sensitivity_button.setEnabled(enabled)
        self._journal_button.setEnabled(enabled)

    def _show_model_summary(self) -> None:
        if self._twin is None:
            return

        c = self._twin.calibration
        self._dashboard.setPlainText(
            "DIGITAL TWIN LOADED\\n"
            "===================\\n"
            f"Fit R²: {c.fit_r_squared:.4f}\\n"
            f"K heat loss: {c.heat_loss_coefficient_w_per_f:.3f} W/°F\\n"
            f"C effective thermal mass: "
            f"{c.effective_thermal_capacitance_j_per_f:,.0f} J/°F\\n"
            f"Tau: {c.time_constant_seconds / 3600.0:.2f} h\\n"
            f"Measured-run equilibrium: {c.equilibrium_temperature_f:.1f} °F\\n\\n"
            "Set the conditions above, then Run Digital Twin."
        )

    def _run_prediction(self) -> None:
        if self._twin is None:
            return

        model = self._twin.model
        heater = self._heater_watts.value()
        outside = self._outside_f.value()
        initial = self._initial_f.value()
        target = self._target_f.value()
        duration = self._duration_hours.value() * 3600.0

        prediction = model.temperature_after(
            initial_temperature_f=initial,
            elapsed_seconds=duration,
            heater_power_w=heater,
            outside_temperature_f=outside,
        )
        required = model.required_power_w(
            target_temperature_f=target,
            outside_temperature_f=outside,
        )
        time_to_target = model.time_to_temperature_seconds(
            initial_temperature_f=initial,
            target_temperature_f=target,
            heater_power_w=heater,
            outside_temperature_f=outside,
        )

        margin = heater - required

        lines = [
            "ENGINEERING DASHBOARD",
            "=" * 21,
            f"Selected heater: {heater:.0f} W",
            f"Outside: {outside:.1f} °F",
            f"Initial: {initial:.1f} °F",
            f"Target: {target:.1f} °F",
            "",
            f"Predicted equilibrium: {prediction.equilibrium_temperature_f:.1f} °F",
            f"Predicted after {self._duration_hours.value():.2f} h: "
            f"{prediction.chamber_temperature_f:.1f} °F",
            f"Required power for target: {required:.0f} W",
            f"Power margin: {margin:+.0f} W",
        ]

        if time_to_target is None:
            lines.append("Time to target: UNREACHABLE at selected power")
        else:
            lines.append(
                f"Time to target: {time_to_target / 3600.0:.2f} h"
            )

        lines += [
            "",
            "Model health:",
            f"Calibration R²: {self._twin.calibration.fit_r_squared:.4f}",
            f"Tau: {self._twin.time_constant_hours:.2f} h",
            "",
            "Model: C dT/dt = P - K(T - T_out)",
        ]

        self._dashboard.setPlainText("\\n".join(lines))

    def _run_sensitivity(self) -> None:
        if self._twin is None:
            return

        points = heater_power_sweep(
            self._twin.model,
            initial_temperature_f=self._initial_f.value(),
            outside_temperature_f=self._outside_f.value(),
            target_temperature_f=self._target_f.value(),
            duration_seconds=self._duration_hours.value() * 3600.0,
            center_power_w=self._heater_watts.value(),
        )

        self._sensitivity_table.setRowCount(len(points))

        for row, point in enumerate(points):
            if point.time_to_target_seconds is None:
                time_text = "Unreachable"
            else:
                time_text = f"{point.time_to_target_seconds / 3600.0:.2f} h"

            values = (
                f"{point.heater_power_w:.0f}",
                f"{point.equilibrium_temperature_f:.1f}",
                f"{point.temperature_after_duration_f:.1f}",
                time_text,
            )

            for column, value in enumerate(values):
                self._sensitivity_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        self._sensitivity_table.resizeColumnsToContents()

    def _generate_report(self) -> None:
        session = self._state.selected_session
        if session is None or self._twin is None:
            return

        try:
            path = write_engineering_report(
                session,
                target_temperature_f=self._target_f.value(),
            )
        except Exception as exc:
            self._journal_output.setPlainText(
                f"Report generation failed: {type(exc).__name__}: {exc}"
            )
            return

        self._journal_output.setPlainText(
            "ENGINEERING REPORT GENERATED\\n"
            "============================\\n"
            f"{path}\\n\\n"
            "The report combines experiment notes with the saved fitted "
            "thermal parameters and target-power estimate. Raw CSV files "
            "were not modified."
        )
