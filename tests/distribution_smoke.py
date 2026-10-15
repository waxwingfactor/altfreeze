"""Exercise installed wheel and sdist from fresh, non-checkout directories.

Network is needed only for installation/build dependencies. The product workflow
below uses local files. This script is also shipped in the source distribution.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path


def run(command, cwd, *, expected=0):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    result = subprocess.run([str(c) for c in command], cwd=cwd, env=env,
                            text=True, capture_output=True, timeout=180)
    if result.returncode != expected:
        raise AssertionError(f"Unexpected exit {result.returncode}: {result.stdout}\n{result.stderr}")
    return result


def exercise(python, folder, example_script):
    run([python, "-c", "import altfreeze,pathlib; p=pathlib.Path(altfreeze.__file__); assert 'site-packages' in str(p), str(p)"], folder)
    run([python, example_script, "demo"], folder)
    command = [python, "-m", "altfreeze"]
    run(command + ["export", "demo/orchard.epub", "--out", "packet"], folder)
    failed = run(command + ["apply", "demo/orchard.epub", "packet", "--out", "blocked"], folder, expected=2)
    assert json.loads(failed.stderr)["ok"] is False
    assert not (folder / "blocked").exists()
    decisions = json.loads((folder / "packet/decisions.json").read_text(encoding="utf-8"))
    for index, row in enumerate(decisions["items"]):
        row.update(action="replace", alt=f"Three blue bars in context {index + 1}: 水 & growth.", reviewer="Release smoke reviewer")
    (folder / "returned.json").write_text(json.dumps(decisions), encoding="utf-8")
    run(command + ["check", "demo/orchard.epub", "packet", "--decisions", "returned.json"], folder)
    run(command + ["apply", "demo/orchard.epub", "packet", "--decisions", "returned.json", "--out", "final"], folder)
    run(command + ["check", "final/publication.epub", "final/review"], folder)
    result = run(command + ["reconcile", "demo/orchard.epub", "packet", "demo/orchard-revised.epub", "--decisions", "returned.json", "--out", "next"], folder)
    report = json.loads(result.stdout)
    assert report["retained"] == 1 and report["invalidated"] == 1, report
    run(command + ["apply", "demo/orchard-revised.epub", "next", "--out", "incomplete"], folder, expected=2)
    assert not (folder / "incomplete").exists()
    moved = folder / "relocated"
    moved.mkdir()
    (folder / "final").rename(moved / "final")
    run(command + ["check", "relocated/final/publication.epub", "relocated/final/review"], folder)
    return {"unresolved_refused": True, "round_trip": True, "selective_revision": True,
            "postapply_baseline": True, "relocated": True, "installed_import": True}


def main():
    dist = Path(sys.argv[1]).resolve()
    wheels = list(dist.glob("altfreeze-*-py3-none-any.whl"))
    sources = list(dist.glob("altfreeze-*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "Expected one wheel and one source distribution"
    with tempfile.TemporaryDirectory(prefix="altfreeze-installed-") as temp:
        root = Path(temp)
        with tarfile.open(sources[0]) as archive:
            names = archive.getnames()
            for required in ("examples/make_demo.py", "examples/orchard.epub", "tests/test_adversarial.py", "docs/contract.md", "README.md", "LICENSE"):
                assert any(name.endswith("/" + required) for name in names), required
            fixture = next(n for n in names if n.endswith("/examples/make_demo.py"))
            example_script = root / "make_demo.py"
            example_script.write_bytes(archive.extractfile(fixture).read())
        evidence = {}
        for label, artifact in (("wheel", wheels[0]), ("sdist", sources[0])):
            folder = root / label
            folder.mkdir()
            environment = folder / "env"
            venv.create(environment, with_pip=True)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run([python, "-m", "pip", "install", artifact], folder)
            evidence[label] = exercise(python, folder, example_script)
        print(json.dumps({"ok": True, "environments": evidence}, sort_keys=True))


if __name__ == "__main__":
    main()
