# Project Overview

## Purpose

Prepare a submission for the Lab10 classroom WEP-router competition. The primary deliverable is `informe.pdf`, with editable source in `informe.tex`; `README.md` documents local practice and the classroom workflow.

## Scope and Current State

Submission preparation is complete. Offline recovery of the included public capture is verified. Live capture and recovery on the classroom router, hardware compatibility, and any active adversarial tests remain pending; see `project_progress.md` for the deployment handoff.

## Design

Use the Aircrack-ng suite directly. `lab10.py` is a small Python standard-library CLI for environment checks, passive capture setup, and offline recovery; it does not automate active radio tests. Evidence distinguishes the public sample and local checks from results that require the classroom router.
