#!/usr/bin/env bash
set -euo pipefail

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_normal_e2e.py -v
