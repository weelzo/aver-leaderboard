#!/usr/bin/env python3
"""Generate docker-compose.yml from scenario.toml for AVER benchmark."""

import argparse
import os
import tomli
import yaml


def load_scenario(scenario_path: str) -> dict:
    """Load and parse the scenario TOML file."""
    with open(scenario_path, "rb") as f:
        return tomli.load(f)


def resolve_env_vars(env_dict: dict) -> dict:
    """Resolve environment variable references like ${VAR_NAME}."""
    resolved = {}
    for key, value in env_dict.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            resolved[key] = os.environ.get(env_var, value)
        else:
            resolved[key] = value
    return resolved


def generate_compose(scenario: dict) -> dict:
    """Generate docker-compose configuration from scenario."""
    services = {}

    # AgentBeats client service (orchestrator)
    green_agent = scenario.get("green_agent", {})
    green_agent_id = green_agent.get("agentbeats_id", "")

    services["agentbeats-client"] = {
        "image": f"ghcr.io/agentbeats/client:latest",
        "environment": {
            "AGENTBEATS_GREEN_AGENT_ID": green_agent_id,
            "AGENTBEATS_OUTPUT_DIR": "/output",
            **resolve_env_vars(green_agent.get("env", {})),
        },
        "volumes": [
            "./output:/output",
            "./scenario.toml:/app/scenario.toml:ro",
        ],
        "depends_on": [],
        "networks": ["agentbeats-network"],
    }

    # Add participant agents
    participants = scenario.get("participants", [])
    for i, participant in enumerate(participants):
        agent_id = participant.get("agentbeats_id", "")
        agent_name = participant.get("name", f"agent-{i}")

        service_name = f"agent-{agent_name}"
        services[service_name] = {
            "image": f"ghcr.io/agentbeats/agent:latest",
            "environment": {
                "AGENTBEATS_AGENT_ID": agent_id,
                "AGENTBEATS_AGENT_NAME": agent_name,
                **resolve_env_vars(participant.get("env", {})),
            },
            "networks": ["agentbeats-network"],
        }
        services["agentbeats-client"]["depends_on"].append(service_name)

    # Add config as environment variables to client
    config = scenario.get("config", {})
    for key, value in config.items():
        env_key = f"AVER_{key.upper()}"
        if isinstance(value, list):
            services["agentbeats-client"]["environment"][env_key] = ",".join(str(v) for v in value)
        else:
            services["agentbeats-client"]["environment"][env_key] = str(value)

    compose = {
        "version": "3.8",
        "services": services,
        "networks": {
            "agentbeats-network": {
                "driver": "bridge",
            },
        },
    }

    return compose


def main():
    parser = argparse.ArgumentParser(description="Generate docker-compose.yml from scenario.toml")
    parser.add_argument("--scenario", "-s", default="scenario.toml", help="Path to scenario TOML file")
    parser.add_argument("--output", "-o", default="docker-compose.yml", help="Output docker-compose file path")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    compose = generate_compose(scenario)

    with open(args.output, "w") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

    print(f"Generated {args.output} from {args.scenario}")
    print(f"  - Green agent: {scenario.get('green_agent', {}).get('agentbeats_id', 'N/A')}")
    print(f"  - Participants: {len(scenario.get('participants', []))}")


if __name__ == "__main__":
    main()
