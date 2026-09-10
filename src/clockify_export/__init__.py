"""clockify-export — export Clockify time entries to CSV."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("clockify-export")
except PackageNotFoundError:  # pragma: no cover - running from source without install
    __version__ = "0.0.0"