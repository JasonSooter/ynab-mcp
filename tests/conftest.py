"""Environment for every test, set before anything imports upstream mcp-ynab.

Upstream reads YNAB_API_KEY at import time and exits the process if it is
missing, so it has to exist before collection. No test calls the YNAB API.
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("YNAB_API_KEY", "test-token-not-a-real-ynab-key")
os.environ.setdefault("CACHE_DB_PATH", os.path.join(tempfile.mkdtemp(), "cache.db"))
