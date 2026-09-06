"""
Backend-side SQLAlchemy models.

These read against the exact same schema the SDK writes
(sdk/agenttrace/models.py). In Phase 3 we'll decide whether to:
  (a) import the SDK's models directly (backend depends on
      agenttrace-sdk being installed), or
  (b) mirror them here to keep backend/ deployable independently.

Leaning towards (a) for v1 to avoid schema drift, since both live in
the same repo/monorepo and the backend already needs the SDK's models
to reflect the tables.
"""

# TODO(Phase 3): import or mirror Run, Step, StepReplay models here.
