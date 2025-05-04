import getopt
import sys

from marcel.api import *

def usage():
    print(f'Usage: {sys.argv[0]} [--source ENV_FILE] [--venv VENV_NAME]')
    print( '  --source: environment file to source (default: .uams-ue1)')
    print( '  --venv:   pyenv virtualenv name (default: dbt_fdm)')
    sys.exit(1)


# Defaults
ENV_FILE=".tenethealth-ue1"
VENV_NAME="dbt_fdm"
LAYER_NAME="silver/periop_fdm_athenahealth"


def args():
    try:
        args, vals = getopt.getopt(sys.argv[1:],
                                   's:v:l:',
                                   'source', 'venv', 'layer')
        print(f'args: {args}')
        print(f'vals: {vals}')
    except getopt.error:
        usage()
    

def main():
    args()
    print('👉 Using env file: $ENV_FILE')
    print('👉 Using pyenv virtualenv: $VENV_NAME')
    # Step 1: Go to foundational-data-models
    cd('foundational-data-models')
    # Step 2: Create the virtualenv (if needed)
    venv_dir = f'{env(var="HOME")}/.pyenv/versions/{VENV_NAME}')
    if not venv_dir.exists():
        print(f'Creating pyenv virtualenv {VENV_NAME}...')
        bash(f"pyenv virtualenv 3.11.11 '{VENV_NAME}'")
    # Step 3: Activate virtualenv
    source '$HOME/.pyenv/versions/$VENV_NAME/bin/activate'

# Step 4: Install requirements
pip install -r requirements-dev.txt

# Step 5: Go to gold layer
cd 'layers/$LAYER_NAME'

# Step 6: Load environment
if [ ! -f 'workspace_config/$ENV_FILE' ]; then
  echo '❌ Cannot find workspace_config/$ENV_FILE'
  exit 1
fi
source 'workspace_config/$ENV_FILE'

# Step 7: Run dbt commands
dbt deps
dbt seed
dbt run
dbt test
dbt clean

echo '✅ Done!'
