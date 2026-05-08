#!/bin/bash
#  Licensed to the Apache Software Foundation (ASF) under one or more
#  contributor license agreements.  See the NOTICE file distributed with
#  this work for additional information regarding copyright ownership.
#  The ASF licenses this file to You under the Apache License, Version 2.0
#  (the "License"); you may not use this file except in compliance with
#  the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
set -Eeuo pipefail

# Constants
SCRIPT_FILE="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "${SCRIPT_FILE}")"
MODULE_DIR="$(dirname "${SCRIPT_DIR}")"

# All …/tests dirs under package src roots in one pytest run.
mapfile -d '' TEST_DIRS < <(find "${MODULE_DIR}/packages" -path "*/src/*/tests" -type d -print0) || true
if [[ ${#TEST_DIRS[@]} -eq 0 ]]; then
	echo "error: no tests directories found under ${MODULE_DIR}/packages" >&2
	exit 1
fi

cd "${MODULE_DIR}"
uv run pytest -v -s --cache-clear \
	--cov="${MODULE_DIR}/packages/ghappkit/src/ghappkit" \
	--cov="${MODULE_DIR}/packages/ghappkit-github/src/ghappkit_github" \
	--cov="${MODULE_DIR}/packages/ghappkit-testing/src/ghappkit_testing" \
	--cov-report=term-missing \
	--cov-report=xml \
	"${TEST_DIRS[@]}"
