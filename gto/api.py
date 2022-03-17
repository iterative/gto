from datetime import datetime
from typing import Union

import pandas as pd
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


def add(
    repo: Union[str, Repo], type: str, name: str, path: str, external: bool = False
):
    """Add an artifact to the Index"""
    return init_index_manager(path=repo).add(type, name, path, external)


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


def demote(repo: Union[str, Repo], name: str, label: str):
    """De-promote artifact from given label"""
    return GitRegistry.from_repo(repo).demote(name, label)


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


def show(repo: Union[str, Repo], dataframe: bool = False):
    """Show current registry state"""

    reg = GitRegistry.from_repo(repo)
    models_state = {
        o.name: {
            "version": o.get_latest_version().name if o.get_latest_version() else None,
            "env": {
                name: o.latest_labels[name].version if name in o.latest_labels else None
                for name in reg.get_envs(in_use=False)
            },
        }
        for o in reg.state.artifacts.values()
    }
    if dataframe:
        result = {
            ("", "latest"): {name: d["version"] for name, d in models_state.items()}
        }
        for name, details in models_state.items():
            for env, ver in details["env"].items():
                result[("env", env)] = {
                    **result.get(("env", env), {}),
                    **{name: ver},
                }
        result_df = pd.DataFrame(result)
        result_df.index.name = "name"
        result_df.columns = pd.MultiIndex.from_tuples(result_df.columns)
        return result_df
    return models_state


def audit_registration(
    repo: Union[str, Repo],
    artifact: str = None,
    sort: str = "desc",
    dataframe: bool = False,
):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)

    audit_trail = [
        {
            "name": o.name,
            "version": v.name,
            "timestamp": v.creation_date,
            "author": v.author,
            "commit": v.commit_hexsha,
            "deprecated": v.deprecated_date,
        }
        for o in reg.state.artifacts.values()
        for v in o.versions
    ]
    if artifact:
        audit_trail = [event for event in audit_trail if event["name"] == artifact]
    if not dataframe:
        return audit_trail

    df = pd.DataFrame(audit_trail)
    if len(df):
        df.sort_values("timestamp", ascending=_is_ascending(sort), inplace=True)
        df.set_index(["timestamp", "name"], inplace=True)
        df = df[["version", "deprecated", "commit", "author"]]
        df["commit"] = df["commit"].str[:7]
    return df


def _is_ascending(sort):
    return sort in {"asc", "Asc", "ascending", "Ascending"}


def audit_promotion(
    repo: Union[str, Repo],
    artifact: str = None,
    sort: str = "desc",
    dataframe: bool = False,
):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)
    audit_trail = [
        {
            "name": o.name,
            "label": l.name,
            "version": l.version,
            "timestamp": l.creation_date,
            "author": l.author,
            "commit": l.commit_hexsha,
            "deprecated": l.deprecated_date,
        }
        for o in reg.state.artifacts.values()
        for l in o.labels
    ]
    if artifact:
        audit_trail = [event for event in audit_trail if event["name"] == artifact]
    if not dataframe:
        return audit_trail

    df = pd.DataFrame(audit_trail)
    if len(df):
        df.sort_values("timestamp", ascending=_is_ascending(sort), inplace=True)
        df.set_index(["timestamp", "name"], inplace=True)
        df = df[["label", "version", "deprecated", "commit", "author"]]
        df["commit"] = df["commit"].str[:7]
    return df


def history(
    repo: str, artifact: str = None, sort: str = "desc", dataframe: bool = False
):
    def add_event(event_list, event_name):
        return [{**event, "event": event_name} for event in event_list]

    reg = GitRegistry.from_repo(repo)
    commits = [
        {
            "name": name_,
            "commit": commit,
            "timestamp": datetime.fromtimestamp(reg.repo.commit(commit).committed_date),
            "author": reg.repo.commit(commit).author.name,
        }
        for name_, commit_list in get_index(repo)
        .artifact_centric_representation()
        .items()
        for commit in commit_list
    ]
    registration = audit_registration(repo, dataframe=False)
    promotion = audit_promotion(repo, dataframe=False)
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
    if not dataframe:
        return events
    df = pd.DataFrame(events)
    if len(df):
        # df.sort_values("timestamp", ascending=is_ascending(sort), inplace=True)
        df.set_index(["timestamp", "name"], inplace=True)
        cols_order = ["event", "version", "label", "deprecated", "commit", "author"]
        df = df[[c for c in cols_order if c in df]]
        df["commit"] = df["commit"].str[:7]
    return df
