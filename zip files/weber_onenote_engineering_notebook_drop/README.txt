WEBER ONENOTE-STYLE ENGINEERING NOTEBOOK DROP

ADD:
  core/engineering_notebook.py
  gui/engineering_notebook_tab.py

REPLACE:
  gui/main_window.py

WHAT CHANGES
------------
A new top-level "Engineering Notebook" tab is added to the application.

The layout is intentionally OneNote-like:
- left pane = experiment pages
- right pane = the selected experiment page
- section tabs = Setup, Data & Analysis, Findings, Photos, Page Preview

All narrative sections use true multi-line QTextEdit controls.
Pressing Return/Enter creates a real newline. Newlines are preserved in both:
  engineering_notebook.json
  engineering_notebook.md

SECTIONS
--------
Setup:
- Objective
- Hardware configuration
- Modifications
- Test conditions

Data & Analysis:
- Acquisition summary
- Analysis highlights

Findings:
- Observations
- Conclusions
- Next actions

Photos:
- Attach one or more experiment photographs
- Copies are stored under the experiment in engineering_photos/
- JPG/PNG/WebP previews are displayed when Qt can decode them
- HEIC can still be attached even when preview support is unavailable

Page Preview:
- Shows the complete notebook page as a readable engineering record

AUTO-FILL
---------
"Auto-Fill Known Data" reads available manifest/session/calibration metadata
and inserts it into Acquisition Summary and Analysis Highlights.

DATA SAFETY
-----------
The notebook is a sidecar system. It does not modify acquisition CSV files.
Raw measurement data remains untouched.

NOTE
----
The older Engineering Journal generator can remain in Simulator. This new
Notebook is the editable human-facing engineering record; the Journal can
continue to serve as an automatically generated report.
