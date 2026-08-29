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
    utc_now_iso,
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

        started_at = datetime.now(timezone.utc)

        session_id = started_at.strftime(
            SESSION_DIRECTORY_TIME_FORMAT
        )

        directory = (
            self._config.sessions_directory
            / session_id
        )

        directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        session = Session(
            session_id=session_id,
            directory=directory,
            started_at_utc=started_at,
        )

        self._write_metadata(session)

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
            ),
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
                "Weber acquisition "
                f"{session.directory.name}"
            ),

            started_at_utc=utc_now_iso(),

            probes=probes,

            heater=HeaterManifest(),
            environment=EnvironmentManifest(),
            weber=WeberManifest(),

            tags=("acquisition",),
        )

        save_manifest(
            session.directory,
            manifest,
        )

        return manifest
