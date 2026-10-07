"""Configure validated extra repositories inside an image build."""

import glob
import json
import os
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse

REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
COPR_PROJECT = re.compile(r"^[@A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
APT_TOKEN = re.compile(r"^[A-Za-z0-9_.+:-]+$")


def require_name(value):
    """Validate a repository name for use in generated config filenames."""
    if not isinstance(value, str) or not REPOSITORY_NAME.fullmatch(value):
        raise ValueError(f"Invalid repository name: {value!r}")
    return value


def require_https_url(value, label):
    """Require an HTTPS URL without embedded credentials or whitespace."""
    if not isinstance(value, str):
        raise TypeError("'value' must be a str.")
    parsed = urlparse(value)
    if any(
        parsed.scheme != "https",
        not parsed.netloc,
        parsed.username,
        parsed.password,
    ) or any(character.isspace() for character in value):
        raise ValueError(f"{label} must be an HTTPS URL without credentials")
    return value


def enable_copr(project):
    """Enable a COPR project, installing the DNF plugin when needed."""
    if not isinstance(project, str) or not COPR_PROJECT.fullmatch(project):
        raise ValueError(f"Invalid COPR project: {project!r}")

    command = ["dnf", "copr", "enable", "-y", project]
    result = subprocess.run(
        command, check=False, capture_output=True, text=True
    )
    if result.returncode == 0:
        return

    # Depending on the Fedora release, the COPR command is provided by either
    # the DNF5 plugins or dnf-plugins-core.
    for package in ("dnf5-plugins", "dnf-plugins-core"):
        install = subprocess.run(
            ["dnf", "install", "-y", package],
            check=False,
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            continue
        result = subprocess.run(
            command, check=False, capture_output=True, text=True
        )
        if result.returncode == 0:
            return

    raise RuntimeError(
        f"Could not enable COPR repository {project!r}: {result.stderr.strip()}"
    )


def enable_dnf_repo(repo_id):
    """Enable an existing repo ID in the image's DNF repository files."""
    repo_id = require_name(repo_id)
    header = re.compile(r"^\s*\[([^]]+)\]\s*(?:[#;].*)?$")
    enabled = re.compile(r"^(\s*)enabled\s*=.*$", re.IGNORECASE)
    found = False

    for filename in glob.glob("/etc/yum.repos.d/*.repo"):
        with open(filename, "r", encoding="utf-8") as repo_file:
            lines = repo_file.readlines()
        changed = False
        for index, line in enumerate(lines):
            match = header.match(line.rstrip("\n"))
            if not match or match.group(1) != repo_id:
                continue

            found = True
            section_end = next(
                (
                    item
                    for item in range(index + 1, len(lines))
                    if header.match(lines[item].rstrip("\n"))
                ),
                len(lines),
            )
            for item in range(index + 1, section_end):
                if enabled.match(lines[item]):
                    lines[item] = enabled.sub(r"\1enabled=1", lines[item])
                    break
            else:
                lines.insert(index + 1, "enabled=1\n")
            changed = True
            break

        if changed:
            with open(filename, "w", encoding="utf-8") as repo_file:
                repo_file.writelines(lines)

    if not found:
        raise ValueError(f"DNF repository ID '{repo_id}' was not found")


def configure_dnf(repositories):
    """Write DNF repository files and enable requested COPR projects."""
    os.makedirs("/etc/yum.repos.d", exist_ok=True)
    for repository in repositories:
        if not isinstance(repository, dict):
            raise ValueError("Each repository configuration must be an object")
        repository_type = repository.get("type")
        if repository_type == "copr":
            enable_copr(repository["project"])
            continue
        if repository_type == "dnf":
            enable_dnf_repo(repository["repo_id"])
            continue
        if repository_type != "rpm":
            raise ValueError(
                f"DNF image received unsupported repository type "
                f"{repository_type!r}"
            )

        name = require_name(repository["name"])
        baseurl = require_https_url(repository["baseurl"], "RPM baseurl")
        gpgkey = require_https_url(repository["gpgkey"], "RPM gpgkey")
        with open(
            f"/etc/yum.repos.d/ipalab-{name}.repo", "w", encoding="utf-8"
        ) as repo_file:
            repo_file.write(
                f"[ipalab-{name}]\n"
                f"name={name}\n"
                f"baseurl={baseurl}\n"
                "enabled=1\n"
                "gpgcheck=1\n"
                f"gpgkey={gpgkey}\n"
            )


def download_key(url, path):
    """Download an HTTPS signing key into an APT keyring path."""
    require_https_url(url, "APT key_url")
    request = urllib.request.Request(
        url, headers={"User-Agent": "ipalab-config"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        require_https_url(response.geturl(), "APT key_url redirect")
        key_data = response.read(1024 * 1024 + 1)
    if not key_data or len(key_data) > 1024 * 1024:
        raise ValueError("Repository signing key is empty or larger than 1 MiB")
    is_armored = key_data.lstrip().startswith(
        b"-----BEGIN PGP PUBLIC KEY BLOCK-----"
    )
    extension = "asc" if is_armored else "gpg"
    keyring = f"/etc/apt/keyrings/ipalab-{path}.{extension}"
    os.makedirs(os.path.dirname(keyring), exist_ok=True)
    with open(keyring, "wb") as key_file:
        key_file.write(key_data)
    return keyring


def configure_apt(repositories):
    """Write signed APT source definitions for the requested repositories."""
    os.makedirs("/etc/apt/sources.list.d", exist_ok=True)
    for repository in repositories:
        if not isinstance(repository, dict) or repository.get("type") != "apt":
            raise ValueError("APT image received a non-APT repository")
        name = require_name(repository["name"])
        uris = repository["uris"]
        suites = repository["suites"]
        components = repository["components"]
        if not all(
            isinstance(values, list)
            and values
            and all(
                isinstance(value, str) and APT_TOKEN.fullmatch(value)
                for value in values
            )
            for values in (suites, components)
        ):
            raise ValueError(
                f"Invalid suites or components for APT repo {name!r}"
            )
        if not isinstance(uris, list) or not uris:
            raise ValueError(f"Invalid URIs for APT repo {name!r}")
        for uri in uris:
            require_https_url(uri, "APT URI")

        keyring = download_key(repository["key_url"], name)
        source = (
            "Types: deb\n"
            f"URIs: {' '.join(uris)}\n"
            f"Suites: {' '.join(suites)}\n"
            f"Components: {' '.join(components)}\n"
            f"Signed-By: {keyring}\n"
        )
        with open(
            f"/etc/apt/sources.list.d/ipalab-{name}.sources",
            "w",
            encoding="utf-8",
        ) as source_file:
            source_file.write(source)


def main():
    """Read encoded repository data and configure the selected backend."""
    backend = sys.argv[1]
    repositories = json.load(sys.stdin)
    if not isinstance(repositories, list):
        raise ValueError("Decoded repository configuration must be a list")
    if backend == "dnf":
        configure_dnf(repositories)
    elif backend == "apt":
        configure_apt(repositories)
    else:
        raise ValueError(f"Unsupported repository backend: {backend}")


if __name__ == "__main__":
    main()
