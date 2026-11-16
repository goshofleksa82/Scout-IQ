"""Compatibility import; implementation is in app/services/sessions.py."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("app.services.sessions")
