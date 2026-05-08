#!/bin/bash
set -Eeuo pipefail

# Copyright 2025 yu-iskw
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and

# Constants
SCRIPT_FILE="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "${SCRIPT_FILE}")"
MODULE_DIR="$(dirname "${SCRIPT_DIR}")"
# Optional: set PYTHON_BIN (e.g. CI matrix interpreter). When unset, uv uses the
# project's .python-version so the venv matches the lockfile pins.
if [[ -n "${PYTHON_BIN:-}" ]] && [[ ! -x "${PYTHON_BIN}" ]]; then
	echo "Error: PYTHON_BIN is not executable: ${PYTHON_BIN}"
	exit 1
fi

# Arguments
deps="production"
while (($# > 0)); do
	if [[ $1 == "--deps" ]]; then
		if [[ $2 != "production" && $2 != "development" ]]; then
			echo "Error: deps must be one of 'production' or 'development'"
			exit 1
		fi
		deps="$2"
		shift 2
	else
		echo "Unknown argument: $1"
		exit 1
	fi
done

# Change to the module directory
cd "${MODULE_DIR}"

# Install uv and dependencies
if ! command -v uv >/dev/null 2>&1; then
	_bootstrap_py=""
	if command -v python >/dev/null 2>&1; then
		_bootstrap_py="$(command -v python)"
	elif command -v python3 >/dev/null 2>&1; then
		_bootstrap_py="$(command -v python3)"
	else
		echo "Error: python is not available on PATH (needed to bootstrap uv)"
		exit 1
	fi
	"${_bootstrap_py}" -m pip install --force-reinstall -r "${MODULE_DIR}/requirements.setup.txt"
fi

# Create virtual environment
if [[ -n "${PYTHON_BIN:-}" ]]; then
	uv venv --allow-existing --python "${PYTHON_BIN}"
else
	uv venv --allow-existing
fi

# Install package and dependencies
if [[ ${deps} == "production" ]]; then
	if [[ -n "${PYTHON_BIN:-}" ]]; then
		uv sync --python "${PYTHON_BIN}" --all-packages --no-dev
	else
		uv sync --all-packages --no-dev
	fi
else
	if [[ -n "${PYTHON_BIN:-}" ]]; then
		uv sync --python "${PYTHON_BIN}" --all-packages --all-extras --group dev
	else
		uv sync --all-packages --all-extras --group dev
	fi
fi
