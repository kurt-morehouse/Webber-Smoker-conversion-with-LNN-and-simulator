import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from acquisition.config import AppConfig

from core.experiment_manifest import (
    CURRENT_SCHEMA_VERSION,
    EnvironmentManifest,
    ExperimentManifest,
    HeaterManifest,
    ProbeManifest,
    WeberManifest,
    save_manifest,
)

SESSION_DIRECTORY_TIME_FORMAT: str = "%Y%m%d_%H%M%S"


@dataclass(frozen=True)
class Session:
    session_id: str
    directory: Path
    started_at_utc: datetime


class SessionManager:
    def __init__(
        self,
        config: AppConfig,
    ) -> None:
        self._config = config

    def create_session(self) -> Session:
        """
        Create the experiment directory and session metadata.

        This may happen before acquisition so the engineering notebook can be
        filled in while the physical experiment is being prepared.
        """
        started_at = datetime.now(timezone.utc)

        session_id = started_at.strftime(
            SESSION_DIRECTORY_TIME_FORMAT
        )

        directory = (
            self._config.sessions_directory
            / session_id
        )

        # Avoid a same-second collision without changing the familiar ID form.
        suffix = 2
        while directory.exists():
            directory = (
                self._config.sessions_directory
                / f"{session_id}_{suffix}"
            )
            suffix += 1

        directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        session = Session(
            session_id=directory.name,
            directory=directory,
            started_at_utc=started_at,
        )

        self._write_metadata(session)
        return session

    def open_session(
        self,
        directory: Path,
    ) -> Session:
        """
        Re-open an already prepared session for acquisition.
        """
        directory = Path(directory).expanduser().resolve()

        if not directory.is_dir():
            raise FileNotFoundError(
                f"Session directory not found: {directory}"
            )

        metadata_path = (
            directory
            / self._config.session_metadata_filename
        )

        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"Session metadata not found: {metadata_path}"
            )

        data = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )

        started_text = str(
            data.get("started_at_utc") or ""
        )

        if not started_text:
            raise ValueError(
                f"Session metadata has no started_at_utc: {metadata_path}"
            )

        started_at = datetime.fromisoformat(
            started_text
        )

        return Session(
            session_id=str(
                data.get("session_id")
                or directory.name
            ),
            directory=directory,
            started_at_utc=started_at,
        )

    def create_prepared_session(
        self,
        probe_definitions,
    ) -> Session:
        """
        Create a complete pre-acquisition experiment shell:
        directory + session.json + manifest.json.
        """
        session = self.create_session()

        self.create_manifest(
            session=session,
            probe_definitions=probe_definitions,
        )

        return session

    def _write_metadata(
        self,
        session: Session,
    ) -> None:
        metadata = {
            "session_id": session.session_id,
            "started_at_utc":
                session.started_at_utc.isoformat(),
            "application":
                "Webber Smoker Chef iQ Monitor",
        }

        path = (
            session.directory
            / self._config.session_metadata_filename
        )

        path.write_text(
            json.dumps(
                metadata,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def create_manifest(
        self,
        session,
        probe_definitions,
    ) -> ExperimentManifest:
        probes = tuple(
            ProbeManifest(
                device_id=probe.match_fragment,
                friendly_name=probe.friendly_name,
                data_file=(
                    probe.friendly_name
                    .lower()
                    .replace(" ", "_")
                    + ".csv"
                ),
                role=probe.friendly_name,
            )
            for probe in probe_definitions
        )

        manifest = ExperimentManifest(
            schema_version=CURRENT_SCHEMA_VERSION,
            experiment_id=session.directory.name,
            name=(
                "Weber experiment "
                f"{session.directory.name}"
            ),
            # The experiment/session exists now. Acquisition start is a
            # separate lifecycle event and does not create a second session.
            started_at_utc=(
                session.started_at_utc.isoformat()
            ),
            probes=probes,
            heater=HeaterManifest(),
            environment=EnvironmentManifest(),
            weber=WeberManifest(),
            tags=("experiment",),
        )

        save_manifest(
            session.directory,
            manifest,
        )

        return manifest
