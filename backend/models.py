"""
Backend-side model re-export.

The backend reads the exact same schema the SDK writes
(sdk/agenttrace/models.py). Importing the classes directly here —
rather than redefining them — means the reader (backend) and the
writer (SDK) can never drift out of sync with each other.

Requires `agenttrace-sdk` to be installed (`pip install -e ../sdk`,
already listed as a dependency in requirements.txt as a path
requirement / installed explicitly in the Dockerfile).
"""

from agenttrace.models import Base, Run, Step, StepReplay

__all__ = ["Base", "Run", "Step", "StepReplay"]
