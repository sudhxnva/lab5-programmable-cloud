import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


PART1_PATH = Path(__file__).parents[1] / "part1" / "part1.py"


def load_part1_module():
    bootstrap_compute = Mock()
    bootstrap_compute.instances().list().execute.return_value = {"items": []}

    with (
        patch("google.auth.default", return_value=(Mock(), "test-project")),
        patch(
            "googleapiclient.discovery.build", return_value=bootstrap_compute
        ),
    ):
        spec = importlib.util.spec_from_file_location("part1_under_test", PART1_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def test_list_instances_returns_empty_list_when_zone_has_no_instances():
    part1 = load_part1_module()
    compute = Mock()
    compute.instances().list().execute.return_value = {}

    assert part1.list_instances(compute, "test-project", "us-west1-b") == []


def test_build_instance_body_uses_required_network_image_and_startup_script():
    part1 = load_part1_module()

    body = part1.build_instance_body(
        "flask-test", "us-west1-b", "echo startup", "f1-micro"
    )

    assert body["machineType"] == "zones/us-west1-b/machineTypes/f1-micro"
    assert body["disks"][0]["initializeParams"]["sourceImage"] == (
        "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
    )
    assert body["networkInterfaces"][0]["network"] == "global/networks/default"
    assert body["networkInterfaces"][0]["accessConfigs"] == [
        {"name": "External NAT", "type": "ONE_TO_ONE_NAT"}
    ]
    assert body["metadata"]["items"] == [
        {"key": "startup-script", "value": "echo startup"}
    ]


def test_firewall_body_targets_only_allow_5000_tag():
    part1 = load_part1_module()

    assert part1.build_firewall_body() == {
        "name": "allow-5000",
        "network": "global/networks/default",
        "direction": "INGRESS",
        "sourceRanges": ["0.0.0.0/0"],
        "targetTags": ["allow-5000"],
        "allowed": [{"IPProtocol": "tcp", "ports": ["5000"]}],
    }


def test_external_ip_returns_nat_ip_from_instance_response():
    part1 = load_part1_module()
    instance = {"networkInterfaces": [{"accessConfigs": [{"natIP": "8.231.193.52"}]}]}

    assert part1.external_ip(instance) == "8.231.193.52"


def test_apply_network_tag_uses_current_fingerprint_and_waits():
    part1 = load_part1_module()
    compute = Mock()
    compute.instances().get().execute.return_value = {"tags": {"fingerprint": "abc"}}
    compute.instances().setTags().execute.return_value = {"name": "tag-operation"}
    compute.instances().setTags.reset_mock()
    wait_for_operation = Mock()

    part1.apply_network_tag(
        compute, "test-project", "us-west1-b", "flask-test", wait_for_operation
    )

    compute.instances().setTags.assert_called_once_with(
        project="test-project",
        zone="us-west1-b",
        instance="flask-test",
        body={"items": ["allow-5000"], "fingerprint": "abc"},
    )
    wait_for_operation.assert_called_once_with("tag-operation", "us-west1-b")
