"""Permissive stand-in for the probatio (voluptuous fork) package."""

import sys
import types


class _P:
    def __init__(self, *a, **k):
        self.args = a

    def __call__(self, *a, **k):
        return a[0] if a else None

    def extend(self, *a, **k):
        return self


m = types.ModuleType("probatio")
for name in (
    "Schema",
    "All",
    "Coerce",
    "Range",
    "Optional",
    "Required",
    "In",
    "Port",
    "Match",
    "Length",
    "Secret",
):
    setattr(m, name, _P)
sys.modules["probatio"] = m
