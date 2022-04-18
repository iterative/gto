from collections import OrderedDict
from datetime import datetime
from typing import List, Optional, Union

from git import Repo

from gto.constants import NAME, STAGE, VERSION
from gto.exceptions import WrongArgs
from gto.ext import EnrichmentInfo
from gto.index import (
    EnrichmentManager,
    FileIndexManager,
    RepoIndexManager,
    init_index_manager,
)
from gto.registry import GitRegistry
from gto.tag import NAME_REFERENCE
from gto.tag import parse_name as parse_tag_name
from gto.tag import parse_name_reference


def get_index(repo: Union[str, Repo], file=False):
    """Get index state"""
    if file:
        return FileIndexManager.from_path(
            path=repo if isinstance(repo, str) else repo.working_dir
        )
    return RepoIndexManager.from_repo(repo)


def _get_state(repo: Union[str, Repo]):
    """Show current registry state"""
    return GitRegistry.from_repo(repo).get_state()


def get_stages(repo: Union[str, Repo], in_use: bool = False):
    return GitRegistry.from_repo(repo).get_stages(in_use=in_use)


# TODO: make this work the same as CLI version
def annotate(
    repo: Union[str, Repo],
    name: str,
    type: Optional[str] = None,
    path: Optional[str] = None,
    must_exist: bool = False,
    labels: List[str] = None,
    description: str = "",
    # update: bool = False,
):
    """Add an artifact to the Index"""
    return init_index_manager(path=repo).add(
        name,
        type=type,
        path=path,
        must_exist=must_exist,
        labels=labels,
        description=description,
        update=True,
    )


def remove(repo: Union[str, Repo], name: str):
    """Remove an artifact from the Index"""
    return init_index_manager(path=repo).remove(name)


def register(
    repo: Union[str, Repo],
    name: str,
    ref: str,
    version: str = None,
    bump_major: bool = False,
    bump_minor: bool = False,
    bump_patch: bool = False,
    stdout: bool = False,
):
    """Register new artifact version"""
    return GitRegistry.from_repo(repo).register(
        name=name,
        ref=ref,
        version=version,
        bump_major=bump_major,
        bump_minor=bump_minor,
        bump_patch=bump_patch,
        stdout=stdout,
    )


def promote(
    repo: Union[str, Repo],
    name: str,
    stage: str,
    promote_version: str = None,
    promote_ref: str = None,
    name_version: str = None,
    simple: bool = False,
    force: bool = False,
    skip_registration: bool = False,
    stdout: bool = False,
):
    """Assign stage to specific artifact version"""
    return GitRegistry.from_repo(repo).promote(
        name,
        stage,
        promote_version,
        promote_ref,
        name_version,
        simple=simple,
        force=force,
        skip_registration=skip_registration,
        stdout=stdout,
    )


def parse_tag(name: str):
    return parse_tag_name(name)


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
    if ref.startswith("refs/tags/"):
        ref = ref[len("refs/tags/") :]
    if ref.startswith("refs/heads/"):
        ref = reg.repo.commit(ref).hexsha
    result = reg.check_ref(ref)
    return {
        action: {name: version.dict() for name, version in found.items()}
        for action, found in result.items()
    }


def show(
    repo: Union[str, Repo],
    name: Optional[str] = None,
    # discover: bool = False,
    table: bool = False,
    all_branches=False,
    all_commits=False,
):
    return (
        _show_versions(
            repo,
            name=name,
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
            table=table,
        )
        if name
        else _show_registry(
            repo,
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
            table=table,
        )
    )


def _show_registry(
    repo: Union[str, Repo],
    # discover: bool = False,
    all_branches=False,
    all_commits=False,
    table: bool = False,
):
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
        for o in reg.get_artifacts(
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
        ).values()
    }
    if not table:
        return models_state

    result = [
        [name, d["version"]] + [d["stage"][name] for name in stages]
        for name, d in models_state.items()
    ]
    headers = ["name", "latest version"] + [f"stage/{e}" for e in stages]
    return result, headers


def _show_versions(
    repo: Union[str, Repo],
    name: str,
    raw: bool = False,
    # discover: bool = False,
    all_branches=False,
    all_commits=False,
    table: bool = False,
):
    """List versions of artifact"""
    reg = GitRegistry.from_repo(repo)
    if raw:
        return reg.find_artifact(name).versions
    versions = [
        v.dict_status()
        for v in reg.find_artifact(
            name,
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
        ).get_versions(include_discovered=True)
    ]
    if not table:
        return versions

    first_keys = ["artifact", "name", "stage"]
    versions_ = []
    for v in versions:
        if v["stage"]:
            v["stage"] = v["stage"]["stage"]
        v = OrderedDict(
            [(key, v[key]) for key in first_keys]
            + [(key, v[key]) for key in v if key not in first_keys]
        )
        v["commit_hexsha"] = v["commit_hexsha"][:7]
        v["enrichments"] = [e["source"] for e in v["enrichments"]]
        versions_.append(v)
    return versions_, "keys"


def _is_ascending(sort):
    return sort in {"asc", "Asc", "ascending", "Ascending"}


def describe(
    repo: Union[str, Repo], name: str, rev: str = None
) -> List[EnrichmentInfo]:
    """Find enrichments for the artifact"""
    ref_type, parsed = parse_name_reference(name)
    if ref_type == NAME_REFERENCE.NAME:
        return EnrichmentManager.from_repo(repo).describe(name=name, rev=rev)
    if ref_type == NAME_REFERENCE.TAG:
        if rev:
            raise WrongArgs("Should not specify revision if you pass git tag")
        return EnrichmentManager.from_repo(repo).describe(name=parsed[NAME], rev=name)
    raise NotImplementedError


def history(
    repo: Union[str, Repo],
    artifact: str = None,
    # discover: bool = False,
    # action: str = None,
    all_branches=False,
    all_commits=False,
    sort: str = "desc",
    table: bool = False,
):
    # TODO: rework this.
    # 1. commits should be gathered only --discover is supplied
    # 2. we shouldn't use audit_something functions
    # 3. commits should be got from EnrichmentManager, probably

    reg = GitRegistry.from_repo(repo)
    artifacts = reg.get_artifacts(
        # discover=discover,
        all_branches=all_branches,
        all_commits=all_commits,
    )

    commits = [
        OrderedDict(
            timestamp=datetime.fromtimestamp(
                reg.repo.commit(v.commit_hexsha).committed_date
            ),
            name=o.name,
            event="commit",  # "commit [discovered]" if v.discovered else "commit",
            commit=v.commit_hexsha[:7],
            author=reg.repo.commit(v.commit_hexsha).author.name,
        )
        for o in artifacts.values()
        for v in o.get_versions(include_discovered=True)
    ]

    registration = [
        OrderedDict(
            timestamp=v.creation_date,
            name=o.name,
            event="registration",
            version=v.name,
            commit=v.commit_hexsha[:7],
            author=v.author,
            # enrichments=[e.source for e in v.enrichments],
        )
        for o in artifacts.values()
        for v in o.get_versions()
    ]

    promotion = [
        OrderedDict(
            timestamp=l.creation_date,
            name=o.name,
            event="promotion",
            version=l.version,
            stage=l.stage,
            commit=l.commit_hexsha[:7],
            author=l.author,
        )
        for o in artifacts.values()
        for l in o.stages
    ]

    events_order = {
        "commit": 0,
        # "commit [discovered]": 1,
        "registration": 2,
        "promotion": 3,
    }
    events = sorted(
        commits + registration + promotion,
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
        # "enrichments",
        "commit",
        "author",
    ]
    keys_order = [c for c in keys_order if any(c in event for event in events)]
    events = [
        OrderedDict((key, event.get(key)) for key in keys_order) for event in events
    ]
    return events, "keys"
