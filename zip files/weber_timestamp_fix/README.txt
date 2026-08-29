Replace core/experiment_data.py with the supplied file.

Behavior:
- Explicit elapsed-time columns remain preferred.
- Native timestamp_utc/timestamp columns are converted to true elapsed seconds.
- ISO-8601 timezone offsets and trailing Z are supported.
- Legacy files with neither time representation still fall back to sample index.

This corrects graph duration, time-based display filtering, and thermal-fit tau.
