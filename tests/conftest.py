import pytest
import subprocess
import time
import requests
import os

TEST_PORT = 8765
BASE_URL = f"http://localhost:{TEST_PORT}"


@pytest.fixture(scope="module")
def backend_server():
    """Launch backend on test port, yield, then shutdown."""
    env = os.environ.copy()
    env["PORT"] = str(TEST_PORT)

    proc = subprocess.Popen(
        ["python", "main.py"],
        cwd="backend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server ready (poll health endpoint)
    for _ in range(15):  # 15s timeout
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=1)
            if r.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError("Backend failed to start")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)
