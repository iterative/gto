from collections import OrderedDict
from datetime import datetime
from typing import Union

from git import Repo

from gto.index import FileIndexManager, RepoIndexManager, init_index_manager
from gto.registry import GitRegistry
from gto.tag import parse_name


def get_index(repo: Union[str, Repo], file=False):
    """Get index state"""
    if file:
        return FileIndexManager(
            path=repo if isinstance(repo, str) else repo.working_dir
        )
    return RepoIndexManager.from_repo(repo)


def _get_state(repo: Union[str, Repo]):
    """Show current registry state"""
    return GitRegistry.from_repo(repo).state


def get_envs(repo: Union[str, Repo], in_use: bool = False):
    return GitRegistry.from_repo(repo).get_envs(in_use=in_use)


def add(repo: Union[str, Repo], type: str, name: str, path: str, virtual: bool = False):
    """Add an artifact to the Index"""
    return init_index_manager(path=repo).add(type, name, path, virtual)


def remove(repo: Union[str, Repo], name: str):
    """Remove an artifact from the Index"""
    return init_index_manager(path=repo).remove(name)


def register(
    repo: Union[str, Repo], name: str, ref: str, version: str = None, bump: str = None
):
    """Register new artifact version"""
    return GitRegistry.from_repo(repo).register(
        name=name, ref=ref, version=version, bump=bump
    )


def deprecate(repo: Union[str, Repo], name: str, version: str):
    """Unregister artifact version"""
    return GitRegistry.from_repo(repo).deprecate(name, version)


def promote(
    repo: Union[str, Repo],
    name: str,
    label: str,
    promote_version: str = None,
    promote_ref: str = None,
    name_version: str = None,
):
    """Assign label to specific artifact version"""
    return GitRegistry.from_repo(repo).promote(
        name, label, promote_version, promote_ref, name_version
    )


# def demote(repo: Union[str, Repo], name: str, label: str):
#     """De-promote artifact from given label"""
#     return GitRegistry.from_repo(repo).demote(name, label)


def parse_tag(name: str):
    return parse_name(name)


def find_latest_version(
    repo: Union[str, Repo], name: str, include_deprecated: bool = False
):
    """Return latest version for artifact"""
    return GitRegistry.from_repo(repo).latest(
        name, include_deprecated=include_deprecated
    )


def find_active_label(repo: Union[str, Repo], name: str, label: str):
    """Return version of artifact with specific label active"""
    return GitRegistry.from_repo(repo).which(name, label, raise_if_not_found=False)


def check_ref(repo: Union[str, Repo], ref: str):
    """Find out what have been registered/promoted in the provided ref"""
    reg = GitRegistry.from_repo(repo)
    ref = ref.removeprefix("refs/tags/")
    if ref.startswith("refs/heads/"):
        ref = reg.repo.commit(ref).hexsha
    result = reg.check_ref(ref)
    return {
        action: {name: version.dict() for name, version in found.items()}
        for action, found in result.items()
    }


def show(repo: Union[str, Repo], table: bool = False):
    """Show current registry state"""

    reg = GitRegistry.from_repo(repo)
    envs = list(reg.get_envs(in_use=False))
    models_state = {
        o.name: {
            "version": o.get_latest_version().name if o.get_latest_version() else None,
            "env": {
                name: o.latest_labels[name].version if name in o.latest_labels else None
                for name in envs
            },
        }
        for o in reg.state.artifacts.values()
    }
    if not table:
        return models_state

    result = [
        [name, d["version"]] + [d["env"][name] for name in envs]
        for name, d in models_state.items()
    ]
    headers = ["name", "version"] + [f"env/{e}" for e in envs]
    return result, headers


def audit_registration(
    repo: Union[str, Repo],
    artifact: str = None,
    sort: str = "desc",
    table: bool = False,
):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)

    audit_trail = [
        OrderedDict(
            timestamp=v.creation_date,
            name=o.name,
            version=v.name,
            deprecated=v.deprecated_date,
            commit=v.commit_hexsha[:7],
            author=v.author,
        )
        for o in reg.state.artifacts.values()
        for v in o.versions
    ]
    if artifact:
        audit_trail = [event for event in audit_trail if event["name"] == artifact]
    audit_trail.sort(key=lambda x: x["timestamp"])
    if _is_ascending(sort):
        audit_trail.reverse()
    if not table:
        return audit_trail
    return audit_trail, "keys"


def _is_ascending(sort):
    return sort in {"asc", "Asc", "ascending", "Ascending"}


def audit_promotion(
    repo: Union[str, Repo],
    artifact: str = None,
    sort: str = "desc",
    table: bool = False,
):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)
    audit_trail = [
        OrderedDict(
            timestamp=l.creation_date,
            name=o.name,
            label=l.name,
            version=l.version,
            deprecated=l.deprecated_date,
            commit=l.commit_hexsha[:7],
            author=l.author,
        )
        for o in reg.state.artifacts.values()
        for l in o.labels
    ]
    if artifact:
        audit_trail = [event for event in audit_trail if event["name"] == artifact]
    audit_trail.sort(key=lambda x: x["timestamp"])
    if _is_ascending(sort):
        audit_trail.reverse()
    if not table:
        return audit_trail
    return audit_trail, "keys"


def history(repo: str, artifact: str = None, sort: str = "desc", table: bool = False):
    def add_event(event_list, event_name):
        return [{**event, "event": event_name} for event in event_list]

    reg = GitRegistry.from_repo(repo)
    commits = [
        dict(
            timestamp=datetime.fromtimestamp(reg.repo.commit(commit).committed_date),
            name=name_,
            event="commit",
            commit=commit[:7],
            author=reg.repo.commit(commit).author.name,
        )
        for name_, commit_list in get_index(repo)
        .artifact_centric_representation()
        .items()
        for commit in commit_list
    ]
    registration = audit_registration(repo, table=False)
    promotion = audit_promotion(repo, table=False)
    events_order = {"commit": 0, "registration": 1, "promotion": 2}
    events = sorted(
        add_event(commits, "commit")
        + add_event(registration, "registration")
        + add_event(promotion, "promotion"),
        key=lambda x: (x["timestamp"], events_order[x["event"]]),
    )
    if _is_ascending(sort):
        events.reverse()
    if artifact:
        events = [event for event in events if event["name"] == artifact]
    if not table:
        return events
    keys_order = [
        "timestamp",
        "name",
        "event",
        "version",
        "label",
        "deprecated",
        "commit",
        "author",
    ]
    keys_order = [c for c in keys_order if any(c in event for event in events)]
    events = [
        OrderedDict((key, event.get(key)) for key in keys_order) for event in events
    ]
    return events, "keys"
