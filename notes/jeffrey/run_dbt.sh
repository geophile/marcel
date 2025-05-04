#!/usr/bin/env bash

# Exit if any command fails
set -e

# Usage help
usage() {
  echo "Usage: $0 [--source ENV_FILE] [--venv VENV_NAME]"
  echo "  --source: environment file to source (default: .uams-ue1)"
  echo "  --venv:   pyenv virtualenv name (default: dbt_fdm)"
  exit 1
}

# Defaults
ENV_FILE=".tenethealth-ue1"
VENV_NAME="dbt_fdm"
LAYER_NAME="silver/periop_fdm_athenahealth"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      ENV_FILE="$2"
      shift 2
      ;;
    --venv)
      VENV_NAME="$2"
      shift 2
      ;;
    --layer)
      LAYER_NAME="$2"
      shift 2
      ;;
    -*|--*)
      echo "Unknown option $1"
      usage
      ;;
  esac
done

echo "👉 Using env file: $ENV_FILE"
echo "👉 Using pyenv virtualenv: $VENV_NAME"

# Step 1: Go to foundational-data-models
cd foundational-data-models

# Step 2: Create the virtualenv (if needed)
if [ ! -d "$HOME/.pyenv/versions/$VENV_NAME" ]; then
  echo "Creating pyenv virtualenv $VENV_NAME..."
  pyenv virtualenv 3.11.11 "$VENV_NAME"
fi

# Step 3: Activate virtualenv
source "$HOME/.pyenv/versions/$VENV_NAME/bin/activate"

# Step 4: Install requirements
pip install -r requirements-dev.txt

# Step 5: Go to gold layer
cd "layers/$LAYER_NAME"

# Step 6: Load environment
if [ ! -f "workspace_config/$ENV_FILE" ]; then
  echo "❌ Cannot find workspace_config/$ENV_FILE"
  exit 1
fi
source "workspace_config/$ENV_FILE"

# Step 7: Run dbt commands
dbt deps
dbt seed
dbt run
dbt test
dbt clean

echo "✅ Done!"
