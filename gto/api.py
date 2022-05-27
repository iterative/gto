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


def get_stages(repo: Union[str, Repo], allowed: bool = False):
    return GitRegistry.from_repo(repo).get_stages(allowed=allowed)


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
    message: str = None,
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
        message=message,
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
    message: str = None,
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
        message=message,
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
    all: bool = False,
    registered: bool = True,
):
    """Return latest version for artifact"""
    return GitRegistry.from_repo(repo).latest(name, all=all, registered=registered)


def find_versions_in_stage(
    repo: Union[str, Repo],
    name: str,
    stage: str,
    all: bool = False,
    registered_only: bool = False,
):
    """Return version of artifact with specific stage active"""
    return GitRegistry.from_repo(repo).which(
        name, stage, raise_if_not_found=False, all=all, registered_only=registered_only
    )


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
    table: bool = False,
    all_branches=False,
    all_commits=False,
    truncate_hexsha=False,
    registered_only=False,
):
    return (
        _show_versions(
            repo,
            name=name,
            all_branches=all_branches,
            all_commits=all_commits,
            registered_only=registered_only,
            table=table,
            truncate_hexsha=truncate_hexsha,
        )
        if name
        else _show_registry(
            repo,
            all_branches=all_branches,
            all_commits=all_commits,
            registered_only=registered_only,
            table=table,
            truncate_hexsha=truncate_hexsha,
        )
    )


def _show_registry(
    repo: Union[str, Repo],
    all_branches=False,
    all_commits=False,
    registered_only=False,
    table: bool = False,
    truncate_hexsha: bool = False,  # pylint: disable=unused-argument
):
    """Show current registry state"""

    def format_hexsha(hexsha):
        return hexsha[:7] if truncate_hexsha else hexsha

    reg = GitRegistry.from_repo(repo)
    stages = list(reg.get_stages())
    models_state = {
        o.name: {
            "version": format_hexsha(o.get_latest_version(registered_only=True).name)
            if o.get_latest_version(registered_only=True)
            else None,
            "stage": {
                name: format_hexsha(
                    o.get_promotions(registered_only=registered_only)[name].version
                )
                if name in o.get_promotions(registered_only=registered_only)
                else None
                for name in stages
            },
        }
        for o in reg.get_artifacts(
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
    headers = ["name", "latest"] + [f"#{e}" for e in stages]
    return result, headers


def _show_versions(
    repo: Union[str, Repo],
    name: str,
    raw: bool = False,
    all_branches=False,
    all_commits=False,
    registered_only=False,
    table: bool = False,
    truncate_hexsha: bool = False,
):
    """List versions of artifact"""

    def format_hexsha(hexsha):
        return hexsha[:7] if truncate_hexsha else hexsha

    reg = GitRegistry.from_repo(repo)
    if raw:
        return reg.find_artifact(name).versions
    versions = [
        v.dict_status()
        for v in reg.find_artifact(
            name,
            all_branches=all_branches,
            all_commits=all_commits,
        ).get_versions(
            include_non_explicit=not registered_only, include_discovered=True
        )
    ]
    if not table:
        return versions

    first_keys = ["artifact", "version", "stage"]
    versions_ = []
    for v in versions:
        v["version"] = format_hexsha(v["name"])
        if v["stage"]:
            v["stage"] = v["stage"]["stage"]
        v["commit_hexsha"] = format_hexsha(v["commit_hexsha"])
        v["ref"] = v["tag"] or v["commit_hexsha"]
        for key in (
            "enrichments",
            "discovered",
            "tag",
            "commit_hexsha",
            "name",
            "message",
            "author_email",
        ):
            v.pop(key)
        # v["enrichments"] = [e["source"] for e in v["enrichments"]]
        v = OrderedDict(
            [(key, v[key]) for key in first_keys]
            + [(key, v[key]) for key in v if key not in first_keys]
        )
        versions_.append(v)
    return versions_, "keys"


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


def history(  # pylint: disable=too-many-locals
    repo: Union[str, Repo],
    artifact: str = None,
    # action: str = None,
    all_branches=False,
    all_commits=False,
    ascending: bool = False,
    table: bool = False,
    truncate_hexsha: bool = False,
):

    reg = GitRegistry.from_repo(repo)
    artifacts = reg.get_artifacts(
        all_branches=all_branches,
        all_commits=all_commits,
    )

    def format_hexsha(hexsha):
        return hexsha[:7] if truncate_hexsha else hexsha

    commits = [
        OrderedDict(
            timestamp=datetime.fromtimestamp(
                reg.repo.commit(v.commit_hexsha).committed_date
            ),
            artifact=o.name,
            event="commit",
            commit=format_hexsha(v.commit_hexsha),
            author=reg.repo.commit(v.commit_hexsha).author.name,
            author_email=reg.repo.commit(v.commit_hexsha).author.email,
            message=reg.repo.commit(v.commit_hexsha).message,
        )
        for o in artifacts.values()
        for v in o.get_versions(include_non_explicit=True, include_discovered=True)
    ]

    registration = [
        OrderedDict(
            timestamp=v.created_at,
            artifact=o.name,
            event="registration",
            version=format_hexsha(v.name),
            commit=format_hexsha(v.commit_hexsha),
            author=v.author,
            author_email=v.author_email,
            message=v.message,
            # enrichments=[e.source for e in v.enrichments],
        )
        for o in artifacts.values()
        for v in o.get_versions()
    ]

    promotion = [
        OrderedDict(
            timestamp=l.created_at,
            artifact=o.name,
            event="promotion",
            version=format_hexsha(l.version),
            stage=l.stage,
            commit=format_hexsha(l.commit_hexsha),
            author=l.author,
            author_email=l.author_email,
            message=l.message,
        )
        for o in artifacts.values()
        for l in o.stages
    ]

    events_order = {
        "commit": 1,
        "registration": 2,
        "promotion": 3,
    }
    events = sorted(
        commits + registration + promotion,
        key=lambda x: (x["timestamp"], events_order[x["event"]]),
    )
    if not ascending:
        events.reverse()
    if artifact:
        events = [event for event in events if event["artifact"] == artifact]
    if not table:
        return events
    keys_order = [
        "timestamp",
        "artifact",
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
