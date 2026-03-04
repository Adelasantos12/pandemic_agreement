"""Legacy compatibility ASGI entrypoint.

Some existing Railway services may still be configured with:
    uvicorn apps.api.main:app

This shim re-exports the ML workspace app so old start commands keep working.
"""

from research.railway_app import app  # re-export
