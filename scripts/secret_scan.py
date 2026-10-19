"""Deliberate checksum-pinned Gitleaks download and redacted source scan."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tarfile
import tempfile
import urllib.request

URL = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz"
SHA = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rubrictrace-scan-") as tmp:
        root = Path(tmp)
        data = urllib.request.urlopen(URL, timeout=40).read(20_000_000)
        if hashlib.sha256(data).hexdigest() != SHA:
            raise RuntimeError("Gitleaks checksum mismatch")
        archive = root / "tool.tar.gz"
        archive.write_bytes(data)
        with tarfile.open(archive) as t:
            member = t.getmember("gitleaks")
            if not member.isfile():
                raise RuntimeError("Unexpected scanner member")
            source = t.extractfile(member)
            binary = root / "gitleaks"
            binary.write_bytes(source.read())
        binary.chmod(0o700)
        return subprocess.run(
            [
                str(binary),
                "dir",
                ".",
                "--redact",
                "--ignore-gitleaks-allow",
                "--max-archive-depth",
                "3",
                "--no-banner",
                "--report-format",
                "json",
                "--report-path",
                str(args.report.resolve()),
            ],
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
