import re
from collections import OrderedDict
from typing import List, Optional, Union

from funcy import distinct
from git import Repo

from gto.commit_message_generator import (
    generate_annotate_commit_message,
    generate_remove_commit_message,
)
from gto.constants import (
    ARTIFACT,
    ASSIGNMENTS_PER_VERSION,
    COMMIT,
    NAME,
    STAGE,
    VERSION,
    VERSIONS_PER_STAGE,
    VersionSort,
    mark_artifact_unregistered,
    shortcut_regexp,
)
from gto.exceptions import NoRepo, NotImplementedInGTO, WrongArgs
from gto.ext import EnrichmentInfo
from gto.git_utils import (
    clone_on_remote_repo,
    commit_produced_changes_on_commit,
    push_on_push,
    set_push_on_remote_repo,
)
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


def _is_gto_repo(repo: Union[str, Repo]):
    """Check if repo is a gto repo"""
    try:
        return GitRegistry.from_repo(repo).is_gto_repo()
    except NoRepo:
        return False


def _get_index(repo: Union[str, Repo], file=False):
    """Get index state"""
    if file:
        return FileIndexManager.from_path(
            path=repo if isinstance(repo, str) else repo.working_dir
        )
    return RepoIndexManager.from_repo(repo)


def _get_state(repo: Union[str, Repo]):
    """Show current registry state"""
    return GitRegistry.from_repo(repo).get_state()


@clone_on_remote_repo
def get_stages(repo: Union[str, Repo], allowed: bool = False, used: bool = False):
    return GitRegistry.from_repo(repo).get_stages(allowed=allowed, used=used)


# TODO: make this work the same as CLI version
@set_push_on_remote_repo
@clone_on_remote_repo
@push_on_push
@commit_produced_changes_on_commit(message_generator=generate_annotate_commit_message)
def annotate(
    repo: Union[str, Repo],
    name: str,
    type: Optional[str] = None,
    path: Optional[str] = None,
    must_exist: bool = False,
    labels: List[str] = None,
    description: str = "",
    commit: bool = False,  # pylint: disable=unused-argument
    push: bool = False,  # pylint: disable=unused-argument
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


@set_push_on_remote_repo
@clone_on_remote_repo
@push_on_push
@commit_produced_changes_on_commit(message_generator=generate_remove_commit_message)
def remove(
    repo: Union[str, Repo],
    name: str,
    commit: bool = False,
    push: bool = False,
):  # pylint: disable=unused-argument
    """Remove an artifact from the Index"""
    return init_index_manager(path=repo).remove(name)


@set_push_on_remote_repo
@clone_on_remote_repo
def register(
    repo: Union[str, Repo],
    name: str,
    ref: str,
    version: str = None,
    message: str = None,
    simple: bool = None,
    force: bool = False,
    bump_major: bool = False,
    bump_minor: bool = False,
    bump_patch: bool = False,
    push: bool = False,
    stdout: bool = False,
    author: Optional[str] = None,
    author_email: Optional[str] = None,
):
    """Register new artifact version"""
    return GitRegistry.from_repo(repo).register(
        name=name,
        ref=ref,
        version=version,
        message=message,
        simple=simple if simple is not None else True,
        force=force,
        bump_major=bump_major,
        bump_minor=bump_minor,
        bump_patch=bump_patch,
        push=push,
        stdout=stdout,
        author=author,
        author_email=author_email,
    )


@set_push_on_remote_repo
@clone_on_remote_repo
def assign(
    repo: Union[str, Repo],
    name: str,
    stage: str,
    version: Optional[str] = None,
    ref: Optional[str] = None,
    name_version: Optional[str] = None,
    message: Optional[str] = None,
    simple: bool = False,
    force: bool = False,
    push: bool = False,
    skip_registration: bool = False,
    stdout: bool = False,
    author: Optional[str] = None,
    author_email: Optional[str] = None,
):
    """Assign stage to specific artifact version"""
    return GitRegistry.from_repo(repo).assign(
        name=name,
        stage=stage,
        version=version,
        ref=ref,
        name_version=name_version,
        message=message,
        simple=simple,
        force=force,
        push=push,
        skip_registration=skip_registration,
        stdout=stdout,
        author=author,
        author_email=author_email,
    )


@set_push_on_remote_repo
@clone_on_remote_repo
def unassign(
    repo: Union[str, Repo],
    name: str,
    ref: str = None,
    version: str = None,
    stage: str = None,
    message: str = None,
    stdout: bool = False,
    simple: Optional[bool] = None,
    force: bool = False,
    delete: bool = False,
    push: bool = False,
    author: Optional[str] = None,
    author_email: Optional[str] = None,
):
    return GitRegistry.from_repo(repo).unassign(
        name=name,
        stage=stage,
        ref=ref,
        version=version,
        message=message,
        stdout=stdout,
        simple=simple if simple is not None else False,
        force=force,
        delete=delete,
        push=push,
        author=author,
        author_email=author_email,
    )


@set_push_on_remote_repo
@clone_on_remote_repo
def deregister(
    repo: Union[str, Repo],
    name: str,
    ref: str = None,
    version: str = None,
    message: str = None,
    stdout: bool = False,
    simple: Optional[bool] = None,
    force: bool = False,
    delete: bool = False,
    push: bool = False,
    author: Optional[str] = None,
    author_email: Optional[str] = None,
):
    return GitRegistry.from_repo(repo).deregister(
        name=name,
        ref=ref,
        version=version,
        message=message,
        stdout=stdout,
        simple=simple if simple is not None else True,
        force=force,
        delete=delete,
        push=push,
        author=author,
        author_email=author_email,
    )


@set_push_on_remote_repo
@clone_on_remote_repo
def deprecate(
    repo: Union[str, Repo],
    name: str,
    message: str = None,
    stdout: bool = False,
    simple: Optional[bool] = None,
    force: bool = False,
    delete: bool = False,
    push: bool = False,
    author: Optional[str] = None,
    author_email: Optional[str] = None,
):
    return GitRegistry.from_repo(repo).deprecate(
        name=name,
        message=message,
        stdout=stdout,
        simple=simple if simple is not None else True,
        force=force,
        delete=delete,
        push=push,
        author=author,
        author_email=author_email,
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
    assignments_per_version=ASSIGNMENTS_PER_VERSION,
    versions_per_stage=VERSIONS_PER_STAGE,
    registered_only: bool = False,
):
    """Return version of artifact with specific stage active"""
    return GitRegistry.from_repo(repo).which(
        name,
        stage,
        raise_if_not_found=False,
        assignments_per_version=assignments_per_version,
        versions_per_stage=versions_per_stage,
        registered_only=registered_only,
    )


@clone_on_remote_repo
def check_ref(repo: Union[str, Repo], ref: str):
    """Find out what have been registered/assigned in the provided ref"""
    reg = GitRegistry.from_repo(repo)
    return reg.check_ref(ref)


@clone_on_remote_repo
def show(
    repo: Union[str, Repo],
    name: Optional[str] = None,
    all_branches=False,
    all_commits=False,
    truncate_hexsha=False,
    registered_only=False,
    assignments_per_version=ASSIGNMENTS_PER_VERSION,
    versions_per_stage=VERSIONS_PER_STAGE,
    sort=VersionSort.Timestamp,
    table: bool = False,
):
    return (
        _show_versions(
            repo,
            name=name,
            all_branches=all_branches,
            all_commits=all_commits,
            registered_only=registered_only,
            assignments_per_version=assignments_per_version,
            versions_per_stage=versions_per_stage,
            sort=sort,
            table=table,
            truncate_hexsha=truncate_hexsha,
        )
        if name
        else _show_registry(
            repo,
            all_branches=all_branches,
            all_commits=all_commits,
            registered_only=registered_only,
            assignments_per_version=assignments_per_version,
            versions_per_stage=versions_per_stage,
            sort=sort,
            table=table,
            truncate_hexsha=truncate_hexsha,
        )
    )


def _show_registry(
    repo: Union[str, Repo],
    all_branches=False,
    all_commits=False,
    registered_only=False,
    assignments_per_version: int = None,
    versions_per_stage: int = None,
    sort: VersionSort = None,
    table: bool = False,
    truncate_hexsha: bool = False,
):
    """Show current registry state"""

    def format_hexsha(hexsha):
        return hexsha[:7] if truncate_hexsha else hexsha

    reg = GitRegistry.from_repo(repo)
    stages = list(reg.get_stages())
    models_state = {
        o.artifact: {
            "version": format_hexsha(o.get_latest_version(registered_only=True).version)
            if o.get_latest_version(registered_only=True)
            else None,
            "stage": {
                name: ", ".join(
                    [
                        format_hexsha(s.version)
                        for s in o.get_vstages(
                            registered_only=registered_only,
                            assignments_per_version=assignments_per_version,
                            versions_per_stage=versions_per_stage,
                            sort=sort,
                        ).get(name, [])
                    ]
                )
                or None
                for name in stages
            },
            "registered": o.is_registered,
        }
        for o in reg.get_artifacts(
            all_branches=all_branches,
            all_commits=all_commits,
        ).values()
    }
    if not table:
        return models_state

    return [
        OrderedDict(
            zip(
                ["name", "latest"] + [f"#{e}" for e in stages],
                [
                    name if d["registered"] else mark_artifact_unregistered(name),
                    d["version"],
                ]
                + [d["stage"][name] for name in stages],
            ),
        )
        for name, d in models_state.items()
    ], "keys"


def _show_versions(  # pylint: disable=too-many-locals
    repo: Union[str, Repo],
    name: str,
    raw: bool = False,
    all_branches=False,
    all_commits=False,
    registered_only=False,
    assignments_per_version: int = None,
    versions_per_stage: int = None,
    sort: VersionSort = None,
    table: bool = False,
    truncate_hexsha: bool = False,
):
    """List versions of artifact"""

    def format_hexsha(hexsha):
        return hexsha[:7] if truncate_hexsha else hexsha

    match = re.search(shortcut_regexp, name)
    if match:
        name = match["artifact"]

    reg = GitRegistry.from_repo(repo)
    if raw:
        return reg.find_artifact(name).versions

    artifact = reg.find_artifact(
        name,
        all_branches=all_branches,
        all_commits=all_commits,
    )
    stages = artifact.get_vstages(
        registered_only=registered_only,
        assignments_per_version=assignments_per_version,
        versions_per_stage=versions_per_stage,
        sort=sort,
    )
    versions = []
    for v in artifact.get_versions(
        include_non_explicit=not registered_only, include_discovered=True
    ):
        v = v.dict_state()
        v["stages"] = [
            vstage.dict_state()
            for vstages in stages.values()
            for vstage in vstages
            if vstage.version == v["version"]
        ]
        versions.append(v)

    if match and match["greatest"]:
        versions = versions[:1]
    if match and match["stage"]:
        versions = [
            v for v in versions for a in v["stages"] if match["stage"] in a["stage"]
        ]

    if not table:
        return versions

    first_keys = ["artifact", "version", "stage"]
    versions_ = []
    for v in versions:
        v["artifact"] = (
            v["artifact"]
            if artifact.is_registered
            else mark_artifact_unregistered(v["artifact"])
        )
        v["version"] = format_hexsha(v["version"])
        v["stage"] = ", ".join(
            distinct(  # TODO: remove? no longer necessary
                s["stage"] for s in v["stages"]
            )
        )
        v["commit_hexsha"] = format_hexsha(v["commit_hexsha"])
        if len(v["registrations"]) > 1:
            raise NotImplementedInGTO(
                "Multiple registrations are not supported currently. How you got in here?"
            )
        for key in list(v.keys()):
            if key not in first_keys + ["created_at", "ref"]:
                del v[key]
        v = OrderedDict(
            [(key, v[key]) for key in first_keys]
            + [(key, v[key]) for key in v if key not in first_keys]
        )
        versions_.append(v)
    return versions_, "keys"


@clone_on_remote_repo
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


@clone_on_remote_repo
def history(
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

    events = [
        OrderedDict(
            timestamp=e.created_at,
            artifact=e.artifact,
            event=type(e).__name__.lower(),
            priority=e.priority,
            version=format_hexsha(e.version) if hasattr(e, "version") else None,
            stage=getattr(e, "stage", None),
            commit=format_hexsha(e.commit_hexsha),
            author=e.author,
            author_email=e.author_email,
            message=e.message,
            ref=format_hexsha(e.ref) if e.ref == e.commit_hexsha else e.ref,
        )
        for o in artifacts.values()
        for e in o.get_events()
    ]

    events = sorted(
        events,
        key=lambda x: (x["timestamp"], x["priority"]),
    )
    if not ascending:
        events.reverse()
    if artifact:
        events = [event for event in events if event["artifact"] == artifact]
    if not table:
        return events
    keys_order = [
        "timestamp",
        ARTIFACT,
        "event",
        VERSION,
        STAGE,
        COMMIT,
        "ref",
    ]
    keys_order = [c for c in keys_order if any(c in event for event in events)]
    events = [
        OrderedDict((key, event.get(key)) for key in keys_order) for event in events
    ]
    return events, "keys"
