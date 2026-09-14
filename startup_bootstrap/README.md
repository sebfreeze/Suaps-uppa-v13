# Startup bootstrap

Render can prepend this directory to `PYTHONPATH` so `sitecustomize.py` runs before the Streamlit server starts. The wrapper preserves the existing security bootstrap and executes the private bulk-enrollment payload when dependencies are available.

No production student identifiers are stored in this directory or in the repository.
