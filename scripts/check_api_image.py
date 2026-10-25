"""Executed inside a read-only, network-disabled production API test container."""
import importlib.util
import json
import os
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

for _ in range(60):
    try:
        with urlopen("http://127.0.0.1:8000/api/health/live", timeout=2) as response:
            if response.status == 200:
                break
    except (HTTPError, URLError, TimeoutError):
        time.sleep(0.5)
else:
    raise RuntimeError("Production API image did not become live")
with urlopen("http://127.0.0.1:8000/api/health", timeout=10) as response:
    health = json.load(response)
assert health["database_backend"] == "postgresql"
assert health["schema"] == "ready"
assert health["auth_enabled"] is True
assert health["deployment_mode"] == "multi_user"
try:
    urlopen("http://127.0.0.1:8000/api/courses/", timeout=3)
except HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError("Unauthenticated course access must be denied")
# The isolated test has no approved inference server: readiness must stay closed.
try:
    urlopen("http://127.0.0.1:8000/api/health/ready", timeout=10)
except HTTPError as error:
    assert error.code == 503
else:
    raise AssertionError("Readiness must refuse an unavailable inference server")
assert os.getuid() == 10001
assert shutil.which("docker") is None
assert importlib.util.find_spec("pytest") is None
import tiktoken
assert tiktoken.get_encoding("cl100k_base").encode("MENTOR")
print("Production API image: migrated PostgreSQL, authentication, read-only/non-root runtime and closed readiness verified")
