from dataclasses import dataclass
from pathlib import Path

from core.experiment import (
    Experiment,
    load_experiment,
)

from core.experiment_data import (
    ProbeData,
    load_probe_csv,
)


@dataclass(frozen=True)
class RecordedExperiment:
    experiment: Experiment
    probes: tuple[ProbeData, ...]


def load_recorded_experiment(
    directory: Path,
) -> RecordedExperiment:

    experiment = load_experiment(
        directory
    )

    probe_data: list[ProbeData] = []

    for probe in (
        experiment.manifest.probes
    ):

        csv_path = (
            experiment.directory
            / probe.data_file
        )

        data = load_probe_csv(
            path=csv_path,
            friendly_name=(
                probe.friendly_name
            ),
            role=probe.role,
        )

        probe_data.append(data)

    return RecordedExperiment(
        experiment=experiment,
        probes=tuple(probe_data),
    )
