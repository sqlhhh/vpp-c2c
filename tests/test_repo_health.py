"""Guards on the repository itself.

These run before any pipeline code exists, so CI is green from the first commit
and stays honest about the one mistake that would actually hurt us: committing a
secret. Delete none of these when the real block tests arrive.
"""
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Every variable the pipeline is specified to read. Keep in step with the manual;
# a block that reads a new ENV var adds it here and to .env.example in the same PR.
REQUIRED_ENV_VARS = {
    # Block 0 / 1
    "API_KEY", "API_BASE_URL", "SITE_ID", "RATE_LIMIT_MAX",
    # Block 2
    "POLL_INTERVAL_MIN", "POLL_INTERVAL_SEC", "DAYLIGHT_START", "DAYLIGHT_END",
    # Block 4
    "MQTT_MODE", "MQTT_TOPIC_ROOT", "MQTT_HOST", "MQTT_PORT",
    # Block 5 - AWS
    "AWS_IOT_ENDPOINT", "AWS_ROOT_CA", "AWS_CERT", "AWS_PRIVATE_KEY",
    # Block 5 - InfluxDB
    "INFLUX_URL", "INFLUX_TOKEN", "INFLUX_ORG", "INFLUX_BUCKET",
    # Block 5 - ThingSpeak standby
    "THINGSPEAK_CHANNEL_ID", "THINGSPEAK_WRITE_API_KEY",
}


def _env_example_keys():
    keys = set()
    for line in (REPO / ".env.example").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def test_env_example_exists():
    assert (REPO / ".env.example").is_file(), ".env.example is the only record of what config exists"


def test_env_example_documents_every_required_var():
    missing = REQUIRED_ENV_VARS - _env_example_keys()
    assert not missing, f".env.example is missing: {sorted(missing)}"


def test_env_example_holds_no_real_secrets():
    """A filled-in .env.example means someone pasted a live key into the repo."""
    for line in (REPO / ".env.example").read_text().splitlines():
        if line.startswith(("API_KEY=", "INFLUX_TOKEN=", "THINGSPEAK_WRITE_API_KEY=")):
            value = line.split("=", 1)[1].strip()
            assert value in ("", "your_api_key_here"), f"real-looking value in .env.example: {line}"


def test_gitignore_blocks_secrets():
    text = (REPO / ".gitignore").read_text()
    for pattern in (".env", "certs/*", "*.key"):
        assert pattern in text, f".gitignore must contain {pattern!r}"


def test_no_secret_is_tracked_by_git():
    """The check that matters: ask git what it is actually tracking."""
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO, capture_output=True, text=True,
    )
    if probe.returncode != 0:
        pytest.skip("not a git work tree")
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    offenders = [
        f for f in tracked
        if f == ".env" or f.endswith((".key", ".pem"))
        or (f.startswith("certs/") and f != "certs/.gitkeep")
    ]
    assert not offenders, f"secrets tracked by git: {offenders}"


def test_expected_layout_exists():
    for d in ("src", "tests", "certs", "docs", ".github/workflows"):
        assert (REPO / d).is_dir(), f"missing directory: {d}"
