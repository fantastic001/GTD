#!/bin/bash
set -euo pipefail

THIS_DIR="$(cd "$(dirname "$0")" && pwd)"
MONTHLY_REPORT_FILE="${MONTHLY_REPORT_FILE:-monthly-report.html}"

(
    cd "${THIS_DIR}/.."
    # shellcheck disable=SC1091
    . "${THIS_DIR}/../env/bin/activate"
    python -m gtd monthly_report > "${MONTHLY_REPORT_FILE}"
)
