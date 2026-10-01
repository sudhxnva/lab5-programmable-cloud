import importlib.util
from pathlib import Path


PART2_PATH = Path(__file__).parents[1] / "part2" / "part2.py"


def load_part2_module():
    spec = importlib.util.spec_from_file_location("part2_under_test", PART2_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_name_is_derived_from_source_instance():
    part2 = load_part2_module()

    assert part2.snapshot_name("flask-tutorial-vm") == "base-snapshot-flask-tutorial-vm"


def test_clone_body_uses_snapshot_as_boot_disk_source():
    part2 = load_part2_module()

    body = part2.build_clone_body(
        "flask-clone-1", "us-west1-b", "base-snapshot-flask-tutorial-vm", "e2-micro"
    )

    assert body["machineType"] == "zones/us-west1-b/machineTypes/e2-micro"
    assert body["disks"] == [
        {
            "boot": True,
            "autoDelete": True,
            "initializeParams": {
                "sourceSnapshot": "global/snapshots/base-snapshot-flask-tutorial-vm"
            },
        }
    ]
    assert body["networkInterfaces"][0]["accessConfigs"] == [
        {"name": "External NAT", "type": "ONE_TO_ONE_NAT"}
    ]


def test_timing_markdown_lists_each_clone_duration():
    part2 = load_part2_module()

    assert part2.timing_markdown([("flask-clone-1", 12.345), ("flask-clone-2", 10.0)]) == (
        "# Part 2 VM Creation Timing\n\n"
        "| Instance | Creation time (seconds) |\n"
        "| --- | ---: |\n"
        "| flask-clone-1 | 12.345 |\n"
        "| flask-clone-2 | 10.000 |\n"
    )
