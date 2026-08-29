#!/usr/bin/env bash
set -euo pipefail

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_failure_recovery_e2e.py -v
