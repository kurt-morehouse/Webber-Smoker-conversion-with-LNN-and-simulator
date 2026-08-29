from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
)

from gui.app_state import AppState
from gui.acquisition_controller import AcquisitionController
from gui.acquisition_tab import AcquisitionTab
from gui.sessions_tab import SessionsTab
from gui.simulator_tab import SimulatorTab
from gui.predictions_tab import PredictionsTab
from gui.engineering_notebook_tab import EngineeringNotebookTab


WINDOW_TITLE = "Weber Smoker Engineering Console"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(
            WINDOW_TITLE
        )

        self.resize(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
        )

        # -------------------------------------------------
        # Shared application state
        # -------------------------------------------------

        self._state = AppState()

        # -------------------------------------------------
        # Application-level acquisition service
        #
        # This owns the QThread and BLE acquisition worker.
        # It remains alive regardless of which tab is open.
        # -------------------------------------------------

        self._acquisition_controller = (
            AcquisitionController()
        )

        # -------------------------------------------------
        # Tabs
        # -------------------------------------------------

        self._tabs = QTabWidget()

        self._acquisition_tab = AcquisitionTab(
            app_state=self._state,
            acquisition_controller=
                self._acquisition_controller
            )


        self._sessions_tab = SessionsTab(
            app_state=self._state,
        )

        self._simulator_tab = SimulatorTab(
            app_state=self._state,
        )

        self._predictions_tab = PredictionsTab(
            app_state=self._state,
        )

        self._notebook_tab = EngineeringNotebookTab(
            app_state=self._state,
        )

        self._tabs.addTab(
            self._acquisition_tab,
            "Acquisition",
        )

        self._tabs.addTab(
            self._sessions_tab,
            "Sessions",
        )

        self._tabs.addTab(
            self._simulator_tab,
            "Simulator",
        )

        self._tabs.addTab(
            self._predictions_tab,
            "Predictions",
        )

        self._tabs.addTab(
            self._notebook_tab,
            "Engineering Notebook",
        )

        self.setCentralWidget(
            self._tabs
        )

        # -------------------------------------------------
        # Acquisition events feed shared application state.
        # -------------------------------------------------

        self._acquisition_controller.acquisition_started.connect(
            self._acquisition_started
        )

        self._acquisition_controller.acquisition_stopped.connect(
            self._acquisition_stopped
        )

        self._acquisition_controller.probe_states.connect(
            self._probe_states_changed
        )

        self._acquisition_controller.error.connect(
            self._acquisition_error
        )

    # =====================================================
    # Acquisition events
    # =====================================================

    def _acquisition_started(
        self,
        session_path,
    ) -> None:

        self._state.set_active_session(
            session_path
        )

        self._state.set_acquisition_running(
            True
        )

        # Immediately make the new session visible.
        self._state.refresh_sessions()

    def _acquisition_stopped(
        self,
        session_path,
    ) -> None:

        self._state.set_acquisition_running(
            False
        )

        self._state.set_active_session(
            None
        )

        # Refresh the experiment list because the
        # manifest has now been completed.
        self._state.refresh_sessions()

        # Make the completed experiment the selected one.
        self._state.set_selected_session(
            session_path
        )

    def _probe_states_changed(
        self,
        readings,
    ) -> None:

        self._state.set_live_probes(
            readings
        )

    def _acquisition_error(
        self,
        message: str,
    ) -> None:

        print(
            "Acquisition error:",
            message,
        )
