"""Compatibility import; implementation is in app/api/users.py."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("app.api.users")
