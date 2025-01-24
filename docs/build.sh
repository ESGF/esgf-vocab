#!/bin/bash

SCRIPT_DIR_PATH="$(dirname $0)"
ENV_DIR_PATH="${SCRIPT_DIR_PATH}/../.venv"
source "${ENV_DIR_PATH}/bin/activate"
cd "${SCRIPT_DIR_PATH}"
make html