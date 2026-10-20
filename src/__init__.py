"""Event Contacts Discovery Package.

Automatically loads .env configuration on package import if present.
"""
import os
from pathlib import Path


def load_dotenv_if_present():
    """Lightweight in-memory .env loader (zero external dependencies)."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignore empty lines and comments
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                # Do not overwrite existing environment variables
                if key and key not in os.environ:
                    os.environ[key] = val


load_dotenv_if_present()
