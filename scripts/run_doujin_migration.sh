#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")/.." || exit

# Activate virtual environment
source venv/bin/activate

# Run the migration script
python scripts/doujin_migration.py

# Deactivate virtual environment
deactivate
