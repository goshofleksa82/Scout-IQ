"""Compatibility import; implementation is in app/schemas/__init__.py."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("app.schemas")
