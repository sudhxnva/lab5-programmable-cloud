import importlib.util
from pathlib import Path


PART3_PATH = Path(__file__).parents[1] / "part3" / "part3.py"


def load_part3_module():
    spec = importlib.util.spec_from_file_location("part3_under_test", PART3_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vm2_body_has_external_nat_and_flask_firewall_tag():
    part3 = load_part3_module()

    body = part3.build_vm2_body("flask-vm2", "us-west1-b", "echo flask", "e2-micro")

    assert body["machineType"] == "zones/us-west1-b/machineTypes/e2-micro"
    assert body["tags"] == {"items": ["allow-5000"]}
    assert body["networkInterfaces"][0]["accessConfigs"] == [
        {"name": "External NAT", "type": "ONE_TO_ONE_NAT"}
    ]
    assert body["metadata"]["items"] == [
        {"key": "startup-script", "value": "echo flask"}
    ]


def test_vm1_body_passes_credentials_only_to_vm1_metadata():
    part3 = load_part3_module()

    body = part3.build_vm1_body(
        "vm1-launcher",
        "us-west1-b",
        "start",
        {"service-credentials": "secret"},
        "e2-micro",
    )

    assert body["machineType"] == "zones/us-west1-b/machineTypes/e2-micro"
    assert body["metadata"]["items"] == [
        {"key": "startup-script", "value": "start"},
        {"key": "service-credentials", "value": "secret"},
    ]
