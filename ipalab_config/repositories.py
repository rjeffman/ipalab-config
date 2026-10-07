"""Validation and encoding for additional image-build repositories."""

import base64
import json
import re
from urllib.parse import urlparse

SUPPORTED_REPOSITORIES = {
    "fedora": {"copr", "dnf", "rpm"},
    "centos": {"dnf", "rpm"},
    "alma": {"dnf", "rpm"},
    "rocky": {"dnf", "rpm"},
    "external-nodes": {"copr", "dnf", "rpm"},
    "ubuntu": {"apt"},
}

_REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
_COPR_PROJECT = re.compile(r"^[@A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_APT_TOKEN = re.compile(r"^[A-Za-z0-9_.+:-]+$")


def _require_text(value, field):
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError(
            f"Repository field '{field}' must be a non-empty string"
        )
    return value


def _require_https_url(value, field):
    value = _require_text(value, field)
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"Repository field '{field}' must be an HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError(
            f"Repository field '{field}' must not contain credentials"
        )
    return value


def _validate_string_list(value, field, token_pattern=None):
    if not isinstance(value, list) or not value:
        raise ValueError(f"Repository field '{field}' must be a non-empty list")
    result = []
    for item in value:
        item = _require_text(item, field)
        if token_pattern and not token_pattern.fullmatch(item):
            raise ValueError(
                f"Invalid value in repository field '{field}': {item}"
            )
        result.append(item)
    return result


def _require_fields(repository, fields, description):
    """Require a repository entry to contain exactly the specified fields."""
    if set(repository) != fields:
        raise ValueError(description)


def _validate_copr(repository):
    """Validate and normalize a COPR project definition."""
    _require_fields(
        repository,
        {"type", "project"},
        "A COPR repository requires only 'type' and 'project'",
    )
    project = _require_text(repository["project"], "project")
    if not _COPR_PROJECT.fullmatch(project):
        raise ValueError("COPR 'project' must have the form 'owner/project'")
    return {"type": "copr", "project": project}


def _validate_dnf(repository):
    """Validate and normalize an existing DNF repository ID."""
    _require_fields(
        repository,
        {"type", "repo_id"},
        "A DNF repository requires 'type' and 'repo_id'",
    )
    repo_id = _require_text(repository["repo_id"], "repo_id")
    if not _REPOSITORY_NAME.fullmatch(repo_id):
        raise ValueError("DNF 'repo_id' contains unsupported characters")
    return {"type": "dnf", "repo_id": repo_id}


def _validate_rpm(repository):
    """Validate and normalize a signed DNF repository definition."""
    _require_fields(
        repository,
        {"type", "name", "baseurl", "gpgkey"},
        "An RPM repository requires 'type', 'name', 'baseurl', and 'gpgkey'",
    )
    name = _require_text(repository["name"], "name")
    if not _REPOSITORY_NAME.fullmatch(name):
        raise ValueError(
            "RPM repository 'name' may contain only letters, numbers, "
            "'.', '_' or '-'"
        )
    return {
        "type": "rpm",
        "name": name,
        "baseurl": _require_https_url(repository["baseurl"], "baseurl"),
        "gpgkey": _require_https_url(repository["gpgkey"], "gpgkey"),
    }


def _validate_apt(repository):
    """Validate and normalize a signed APT source definition."""
    _require_fields(
        repository,
        {"type", "name", "uris", "suites", "components", "key_url"},
        "An APT repository requires 'type', 'name', 'uris', 'suites', "
        "'components', and 'key_url'",
    )
    name = _require_text(repository["name"], "name")
    if not _REPOSITORY_NAME.fullmatch(name):
        raise ValueError(
            "APT repository 'name' may contain only letters, numbers, "
            "'.', '_' or '-'"
        )
    uris = [
        _require_https_url(uri, "uris")
        for uri in _validate_string_list(repository["uris"], "uris")
    ]
    suites = _validate_string_list(repository["suites"], "suites", _APT_TOKEN)
    components = _validate_string_list(
        repository["components"], "components", _APT_TOKEN
    )
    return {
        "type": "apt",
        "name": name,
        "uris": uris,
        "suites": suites,
        "components": components,
        "key_url": _require_https_url(repository["key_url"], "key_url"),
    }


_REPOSITORY_VALIDATORS = {
    "copr": _validate_copr,
    "dnf": _validate_dnf,
    "rpm": _validate_rpm,
    "apt": _validate_apt,
}


def _validate_repository(repository, supported_types):
    """Validate one repository entry using its type-specific validator."""
    if not isinstance(repository, dict):
        raise ValueError("Each 'extra_repositories' entry must be a mapping")
    repo_type = repository.get("type")
    if not isinstance(repo_type, str) or repo_type not in supported_types:
        raise ValueError(
            f"Repository type '{repo_type}' is not supported by this image; "
            f"supported types: {', '.join(sorted(supported_types))}"
        )
    return _REPOSITORY_VALIDATORS[repo_type](repository)


def encode_extra_repositories(repositories, dockerfile, build_context=None):
    """Validate repository definitions and encode them for a build argument."""
    if repositories is None:
        return None
    if not isinstance(repositories, list):
        raise ValueError("'extra_repositories' must be a list")
    if not repositories:
        return None

    supported_types = SUPPORTED_REPOSITORIES.get(dockerfile)
    is_custom_containerfile = (
        supported_types is None and build_context == "containerfiles"
    )
    if is_custom_containerfile:
        # Custom recipes in the generated containerfiles context can opt in by
        # consuming the encoded argument with the bundled configuration tool.
        supported_types = {"apt", "copr", "dnf", "rpm"}
    if supported_types is None:
        raise ValueError(
            "'extra_repositories' is not supported by Containerfile "
            f"'{dockerfile}'"
        )

    validated = [
        _validate_repository(repository, supported_types)
        for repository in repositories
    ]
    if is_custom_containerfile:
        backends = {
            "apt" if repository["type"] == "apt" else "dnf"
            for repository in validated
        }
        if len(backends) > 1:
            raise ValueError(
                "A custom Containerfile may not mix APT and DNF repositories"
            )
    names = [
        repository.get("name", repository.get("repo_id"))
        for repository in validated
        if repository["type"] in {"rpm", "apt", "dnf"}
    ]
    if len(names) != len(set(names)):
        raise ValueError(
            "Repository names in 'extra_repositories' must be unique"
        )

    raw_config = json.dumps(validated, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw_config).decode("ascii")
