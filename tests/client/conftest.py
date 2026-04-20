# Isolated conftest for client-only tests.
# This file intentionally does NOT import any server-side modules,
# so client tests can run without server dependencies installed.
#
# Run client tests with:
#   pytest tests/client/ --noconftest
# (--noconftest skips the parent tests/conftest.py which requires server deps)
