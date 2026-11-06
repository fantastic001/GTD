#!/bin/bash
set -euo pipefail

THIS_DIR="$(readlink -f "$(dirname "$0")")"
MONTHLY_REPORT_FILE="${MONTHLY_REPORT_FILE:-monthly-report.html}"
MONTHLY_REPORT_SUBJECT="GTD monthly report $(date +%Y-%m)"

echo "${THIS_DIR}"

(
    cd "${THIS_DIR}/../"
    MONTHLY_REPORT_FILE="${MONTHLY_REPORT_FILE}" ./ci/build_monthly.sh
    REPORT_FILE="${MONTHLY_REPORT_FILE}" \
        REPORT_SUBJECT="${MONTHLY_REPORT_SUBJECT}" \
        REPORT_EXTRAS="skip" \
        ./ci/send.sh
)
