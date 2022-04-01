from collections import OrderedDict
from datetime import datetime
from typing import List, Union

from git import Repo

from gto.constants import NAME, STAGE, VERSION
from gto.index import FileIndexManager, RepoIndexManager, init_index_manager
from gto.registry import GitRegistry
from gto.tag import parse_name


def get_index(repo: Union[str, Repo], file=False):
    """Get index state"""
    if file:
        return FileIndexManager.from_path(
            path=repo if isinstance(repo, str) else repo.working_dir
        )
    return RepoIndexManager.from_repo(repo)


def _get_state(repo: Union[str, Repo]):
    """Show current registry state"""
    return GitRegistry.from_repo(repo).state


def get_stages(repo: Union[str, Repo], in_use: bool = False):
    return GitRegistry.from_repo(repo).get_stages(in_use=in_use)


def ls(repo: Union[str, Repo], ref: str = None, type: str = None):
    """List artifacts of given type"""
    if ref:
        index = RepoIndexManager.from_repo(repo).get_commit_index(ref)
    else:
        index = FileIndexManager.from_path(repo).get_index()
    artifacts = index.dict()["state"]
    if type:
        artifacts = {
            name: artifact
            for name, artifact in artifacts.items()
            if artifact["type"] == type
        }
    return list(artifacts.values())


def add(
    repo: Union[str, Repo],
    type: str,
    name: str,
    path: str,
    virtual: bool = False,
    tags: List[str] = None,
    description: str = "",
):
    """Add an artifact to the Index"""
    return init_index_manager(path=repo).add(
        type, name, path, virtual, tags=tags, description=description
    )


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


def promote(
    repo: Union[str, Repo],
    name: str,
    stage: str,
    promote_version: str = None,
    promote_ref: str = None,
    name_version: str = None,
):
    """Assign stage to specific artifact version"""
    return GitRegistry.from_repo(repo).promote(
        name, stage, promote_version, promote_ref, name_version
    )


def parse_tag(name: str):
    return parse_name(name)


def find_latest_version(
    repo: Union[str, Repo],
    name: str,
):
    """Return latest version for artifact"""
    return GitRegistry.from_repo(repo).latest(name)


def find_promotion(repo: Union[str, Repo], name: str, stage: str):
    """Return version of artifact with specific stage active"""
    return GitRegistry.from_repo(repo).which(name, stage, raise_if_not_found=False)


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


def show(repo: Union[str, Repo], object: str = "registry", table: bool = False):
    if object == "registry":
        return _show_registry(repo, table=table)
    return _show_versions(repo, name=object, table=table)


def _show_registry(repo: Union[str, Repo], table: bool = False):
    """Show current registry state"""

    reg = GitRegistry.from_repo(repo)
    stages = list(reg.get_stages(in_use=False))
    models_state = {
        o.name: {
            "version": o.get_latest_version().name if o.get_latest_version() else None,
            "stage": {
                name: o.promoted[name].version if name in o.promoted else None
                for name in stages
            },
        }
        for o in reg.state.artifacts.values()
    }
    if not table:
        return models_state

    result = [
        [name, d["version"]] + [d["stage"][name] for name in stages]
        for name, d in models_state.items()
    ]
    headers = ["name", "version"] + [f"stage/{e}" for e in stages]
    return result, headers


def _show_versions(
    repo: Union[str, Repo], name: str, raw: bool = False, table: bool = False
):
    """List versions of artifact"""
    reg = GitRegistry.from_repo(repo)
    if raw:
        return reg.state.find_artifact(name).versions
    versions = [v.dict_status() for v in reg.state.find_artifact(name).versions]
    if not table:
        return versions

    first_keys = ["artifact", "name", "stage"]
    versions_ = []
    for v in versions:
        v["artifact"] = v["artifact"]["name"]
        v["stage"] = v["stage"]["stage"]
        v = OrderedDict(
            [(key, v[key]) for key in first_keys]
            + [(key, v[key]) for key in v if key not in first_keys]
        )
        v["commit_hexsha"] = v["commit_hexsha"][:7]
        versions_.append(v)
    return versions_, "keys"


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
            version=l.version,
            stage=l.stage,
            commit=l.commit_hexsha[:7],
            author=l.author,
        )
        for o in reg.state.artifacts.values()
        for l in o.stages
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
        for name_, commit_list in reg.index.artifact_centric_representation().items()
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
        NAME,
        "event",
        VERSION,
        STAGE,
        "commit",
        "author",
    ]
    keys_order = [c for c in keys_order if any(c in event for event in events)]
    events = [
        OrderedDict((key, event.get(key)) for key in keys_order) for event in events
    ]
    return events, "keys"
