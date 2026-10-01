#!/usr/bin/env python3
"""Create a Compute Engine VM that runs the Flask tutorial application."""

import argparse
import time
from pathlib import Path

import google.auth
import googleapiclient.discovery


FIREWALL_RULE = "allow-5000"
NETWORK = "global/networks/default"
IMAGE = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
STARTUP_SCRIPT_PATH = Path(__file__).with_name("startup_script.sh")


def list_instances(compute, project, zone):
    """Return the instances in a zone, or an empty list when it has none."""
    result = compute.instances().list(project=project, zone=zone).execute()
    return result.get("items", [])


def build_firewall_body():
    return {
        "name": FIREWALL_RULE,
        "network": NETWORK,
        "direction": "INGRESS",
        "sourceRanges": ["0.0.0.0/0"],
        "targetTags": [FIREWALL_RULE],
        "allowed": [{"IPProtocol": "tcp", "ports": ["5000"]}],
    }


def build_instance_body(instance_name, zone, startup_script, machine_type):
    return {
        "name": instance_name,
        "machineType": f"zones/{zone}/machineTypes/{machine_type}",
        "disks": [
            {
                "boot": True,
                "autoDelete": True,
                "initializeParams": {"sourceImage": IMAGE},
            }
        ],
        "networkInterfaces": [
            {
                "network": NETWORK,
                "accessConfigs": [
                    {"name": "External NAT", "type": "ONE_TO_ONE_NAT"}
                ],
            }
        ],
        "metadata": {
            "items": [{"key": "startup-script", "value": startup_script}]
        },
    }


def wait_for_operation(compute, project, operation_name, zone=None):
    """Poll an operation until it completes or reports an API error."""
    while True:
        if zone:
            result = compute.zoneOperations().get(
                project=project, zone=zone, operation=operation_name
            ).execute()
        else:
            result = compute.globalOperations().get(
                project=project, operation=operation_name
            ).execute()

        if result.get("status") == "DONE":
            if "error" in result:
                raise RuntimeError(f"Operation {operation_name} failed: {result['error']}")
            return
        time.sleep(1)


def ensure_firewall(compute, project, waiter):
    """Create the port-5000 firewall rule only when it is absent."""
    rules = compute.firewalls().list(project=project).execute().get("items", [])
    if any(rule.get("name") == FIREWALL_RULE for rule in rules):
        print(f"Firewall rule {FIREWALL_RULE} already exists.")
        return

    print(f"Creating firewall rule {FIREWALL_RULE}...")
    operation = compute.firewalls().insert(
        project=project, body=build_firewall_body()
    ).execute()
    waiter(operation["name"], None)


def apply_network_tag(compute, project, zone, instance_name, waiter):
    """Apply the firewall tag using the instance's latest tag fingerprint."""
    instance = compute.instances().get(
        project=project, zone=zone, instance=instance_name
    ).execute()
    tags = instance.get("tags", {})
    items = tags.get("items", [])
    if FIREWALL_RULE not in items:
        items.append(FIREWALL_RULE)

    operation = compute.instances().setTags(
        project=project,
        zone=zone,
        instance=instance_name,
        body={"items": items, "fingerprint": tags["fingerprint"]},
    ).execute()
    waiter(operation["name"], zone)


def external_ip(instance):
    """Return the first external NAT IP address assigned to an instance."""
    for interface in instance.get("networkInterfaces", []):
        for access_config in interface.get("accessConfigs", []):
            if "natIP" in access_config:
                return access_config["natIP"]
    raise ValueError("Instance has no external NAT IP address")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a VM and install the Flask tutorial application."
    )
    parser.add_argument("--project", help="Google Cloud project ID")
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--instance-name", default="flask-tutorial-vm")
    parser.add_argument("--machine-type", default="f1-micro")
    return parser.parse_args()


def main():
    args = parse_args()
    credentials, default_project = google.auth.default()
    project = args.project or default_project
    if not project:
        raise ValueError("Set --project or configure a Google Cloud default project.")

    startup_script = STARTUP_SCRIPT_PATH.read_text(encoding="utf-8")
    compute = googleapiclient.discovery.build(
        "compute", "v1", credentials=credentials
    )

    def waiter(operation_name, zone):
        wait_for_operation(compute, project, operation_name, zone)

    ensure_firewall(compute, project, waiter)

    print(f"Creating {args.instance_name} in {args.zone}...")
    operation = compute.instances().insert(
        project=project,
        zone=args.zone,
        body=build_instance_body(
            args.instance_name, args.zone, startup_script, args.machine_type
        ),
    ).execute()
    waiter(operation["name"], args.zone)

    print(f"Applying {FIREWALL_RULE} network tag...")
    apply_network_tag(compute, project, args.zone, args.instance_name, waiter)

    instance = compute.instances().get(
        project=project, zone=args.zone, instance=args.instance_name
    ).execute()
    print(f"The Flask application is available at: http://{external_ip(instance)}:5000")


if __name__ == "__main__":
    main()
