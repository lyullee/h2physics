#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMBA_NUM_THREADS=1
setup_path="$(realpath "${BASH_SOURCE[0]}")"
export H2_HANGANG_ROOT="$(dirname "$(dirname "$setup_path")")"
export H2_HANGANG_SETUP_SHA256="$(sha256sum "$setup_path" | cut -d ' ' -f 1)"
