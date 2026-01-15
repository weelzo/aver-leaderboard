#!/usr/bin/env python3
"""Record provenance data for AVER benchmark runs."""

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone

import yaml


def get_image_digest(image: str) -> str:
    """Get the digest of a Docker image."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{index .RepoDigests 0}}", image],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_git_info() -> dict:
    """Get current git repository information."""
    info = {}
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if result.returncode == 0:
            info["commit"] = result.stdout.strip()

        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()

        result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if result.returncode == 0:
            info["remote"] = result.stdout.strip()
    except Exception:
        pass
    return info


def record_provenance(compose_path: str) -> dict:
    """Record provenance data from docker-compose configuration."""
    with open(compose_path, "r") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    images = {}

    for service_name, service_config in services.items():
        image = service_config.get("image", "")
        if image:
            images[service_name] = {
                "image": image,
                "digest": get_image_digest(image),
            }

    provenance = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git": get_git_info(),
        "images": images,
        "environment": {
            "runner_os": os.environ.get("RUNNER_OS", "unknown"),
            "runner_arch": os.environ.get("RUNNER_ARCH", "unknown"),
            "github_workflow": os.environ.get("GITHUB_WORKFLOW", "unknown"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
            "github_run_number": os.environ.get("GITHUB_RUN_NUMBER", "unknown"),
            "github_actor": os.environ.get("GITHUB_ACTOR", "unknown"),
            "github_repository": os.environ.get("GITHUB_REPOSITORY", "unknown"),
        },
    }

    return provenance


def main():
    parser = argparse.ArgumentParser(description="Record provenance data for benchmark run")
    parser.add_argument("--compose", "-c", default="docker-compose.yml", help="Path to docker-compose file")
    parser.add_argument("--output", "-o", default="output/provenance.json", help="Output provenance file path")
    args = parser.parse_args()

    provenance = record_provenance(args.compose)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"Recorded provenance to {args.output}")
    print(f"  - Timestamp: {provenance['timestamp']}")
    print(f"  - Images: {len(provenance['images'])}")


if __name__ == "__main__":
    main()
