#!/bin/sh
# Generate and verify the digits on first start, then run the API.
# The dataset lives in a volume, so this happens once.
set -eu

if [ ! -f "${PISCOPE_DATA_DIR}/manifest.json" ]; then
    echo "No dataset in ${PISCOPE_DATA_DIR}; generating ${PISCOPE_DIGITS} digits."
    piscope-digits --data-dir "${PISCOPE_DATA_DIR}" generate --digits "${PISCOPE_DIGITS}"
fi

exec "$@"
