#!/usr/bin/env python3
"""Prepare public, locked dependency bundles for network-disabled Docker builds."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / ".build" / "mentor"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=("api", "web"))
    args = parser.parse_args()
    BUNDLE.mkdir(parents=True, exist_ok=True)
    if args.component == "api":
        if sys.version_info[:2] != (3, 11):
            parser.error("Use Python 3.11 to prepare the qualified runtime bundle")
        wheelhouse = BUNDLE / "python-wheels"
        wheelhouse.mkdir(exist_ok=True)
        command = [sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "--no-input",
                   "--only-binary=:all:", "--require-hashes", "--index-url", "https://pypi.org/simple",
                   "--implementation", "cp", "--python-version", "3.11", "--abi", "cp311"]
        for platform in ("manylinux_2_36_x86_64", "manylinux_2_35_x86_64", "manylinux_2_34_x86_64",
                         "manylinux_2_31_x86_64", "manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64"):
            command += ["--platform", platform]
        subprocess.run([*command, "--dest", str(wheelhouse), "-r", str(ROOT / "apps/api/requirements-runtime.lock")], check=True)
        environment = {**os.environ, "TIKTOKEN_CACHE_DIR": str(BUNDLE / "tokenizer-cache")}
        subprocess.run([sys.executable, "-c", "import tiktoken; tiktoken.get_encoding('cl100k_base')"], env=environment, check=True)
    else:
        packages = json.loads((ROOT / "apps/web/package-lock.json").read_text())["packages"].values()
        urls = set()
        for package in packages:
            if "os" in package and "linux" not in package["os"]:
                continue
            if "cpu" in package and "x64" not in package["cpu"]:
                continue
            if "libc" in package and "glibc" not in package["libc"]:
                continue
            url = package.get("resolved")
            if not url:
                continue
            if not url.startswith("https://registry.npmjs.org/") or not package.get("integrity"):
                raise RuntimeError("Every bundled npm tarball must have a locked public registry URL and integrity hash")
            urls.add(url)
        urls = sorted(urls)
        user_config = BUNDLE / "npm-user.config"
        global_config = BUNDLE / "npm-global.config"
        user_config.write_text("")
        global_config.write_text("")
        npm_environment = {key: value for key, value in os.environ.items()
                           if not key.upper().startswith(("NPM_CONFIG_", "NPM_TOKEN", "NODE_AUTH_TOKEN"))}
        for offset in range(0, len(urls), 50):
            subprocess.run(["npm", "cache", "add", *urls[offset:offset + 50],
                            "--cache", str(BUNDLE / "npm-cache"), f"--userconfig={user_config}", f"--globalconfig={global_config}",
                            "--ignore-scripts", "--no-audit", "--no-fund"], env=npm_environment, check=True)
        print(f"Cached {len(urls)} locked npm tarballs for Linux amd64; npm ci verifies their integrity in the offline build")


if __name__ == "__main__":
    main()
