"""
conftest.py
===========

Project-wide pytest configuration.

Placing this file at the project root makes pytest add the root to sys.path
automatically, so tests can do `from crawler.crawler import ...` without any
extra setup. Without this, tests would need either pip-install-as-package
or sys.path manipulation in every test file.
"""
