#!/usr/bin/env fish

# Change to the project directory
cd (dirname (status -f))/..

# Activate virtual environment
source venv/bin/activate.fish

# Run the migration script
python scripts/doujin_migration.py

# Deactivate virtual environment (not needed in fish, but included for clarity)
