#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_PLOT_EXTRA="${INSTALL_PLOT_EXTRA:-1}"

cd "${ROOT_DIR}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON_BIN} not found in PATH." >&2
  echo "Install Python 3.10+ locally, then rerun this script." >&2
  exit 1
fi

PY_VERSION="$(${PYTHON_BIN} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

case "${PY_VERSION}" in
  3.10|3.11|3.12|3.13) ;;
  *)
    echo "ERROR: Python 3.10+ required, found ${PY_VERSION}" >&2
    exit 1
    ;;
esac

echo "Project root: ${ROOT_DIR}"
echo "Using Python: $(${PYTHON_BIN} --version)"

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating virtual environment at ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
  echo "Virtual environment already exists at ${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip, setuptools, wheel"
python -m pip install --upgrade pip setuptools wheel

if [ "${INSTALL_PLOT_EXTRA}" = "1" ]; then
  echo "Installing package with plotting extras"
  python -m pip install -e ".[plot]"
else
  echo "Installing package without plotting extras"
  python -m pip install -e .
fi

echo
echo "Setup complete."
echo "Activate with:"
echo "  source .venv/bin/activate"
echo
echo "Quick checks:"
echo "  python -c \"import muon_wire_estimator; print('import ok')\""
echo "  python scripts/run_estimator.py --help"
echo "  python scripts/run_event_scan.py --help"