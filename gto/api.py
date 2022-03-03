from typing import Union

import pandas as pd
from git import Repo

from gto.index import FileIndexManager, RepoIndexManager
from gto.registry import GitRegistry
from gto.tag import parse_name


def get_index(repo: Union[str, Repo], file=False):
    """Get index state"""
    if file:
        return FileIndexManager(
            path=repo if isinstance(repo, str) else repo.working_dir
        )
    return RepoIndexManager.from_repo(repo)


def get_state(repo: Union[str, Repo]):
    """Show current registry state"""
    return GitRegistry.from_repo(repo).state


def add(repo: Union[str, Repo], name: str, type: str, path: str):
    """Add an object to the Index"""
    return FileIndexManager(path=repo).add(name, type, path)


def remove(repo: Union[str, Repo], name: str):
    """Remove an object from the Index"""
    return FileIndexManager(path=repo).remove(name)


def register(
    repo: Union[str, Repo], name: str, ref: str, version: str = None, bump: str = None
):
    """Register new object version"""
    return GitRegistry.from_repo(repo).register(
        name=name, ref=ref, version=version, bump=bump
    )


def unregister(repo: Union[str, Repo], name: str, version: str):
    """Unregister object version"""
    return GitRegistry.from_repo(repo).unregister(name, version)


def promote(
    repo: Union[str, Repo],
    name: str,
    label: str,
    promote_version: str = None,
    promote_ref: str = None,
    name_version: str = None,
):
    """Assign label to specific object version"""
    return GitRegistry.from_repo(repo).promote(
        name, label, promote_version, promote_ref, name_version
    )


def demote(repo: Union[str, Repo], name: str, label: str):
    """De-promote object from given label"""
    return GitRegistry.from_repo(repo).demote(name, label)


def parse_tag(name: str):
    return parse_name(name)


def find_latest_version(repo: Union[str, Repo], name: str):
    """Return latest version for object"""
    return GitRegistry.from_repo(repo).latest(name)


def find_active_label(repo: Union[str, Repo], name: str, label: str):
    """Return version of object with specific label active"""
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
            "version": o.latest_version.name if o.latest_version else None,
            "environment": {
                l: o.latest_labels[l].version
                if o.latest_labels[l] is not None
                else None
                for l in o.unique_labels
            },
        }
        for o in reg.state.objects.values()
    }
    if dataframe:
        result = {
            ("", "latest"): {name: d["version"] for name, d in models_state.items()}
        }
        for name, details in models_state.items():
            for env, ver in details["environment"].items():
                result[("environment", env)] = {
                    **result.get(("environment", env), {}),
                    **{name: ver},
                }
        result_df = pd.DataFrame(result)
        result_df.columns = pd.MultiIndex.from_tuples(result_df.columns)
        return result_df
    return models_state


def audit_registration(repo: Union[str, Repo], dataframe: bool = False):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)

    model_registration_audit_trail = [
        {
            "name": o.name,
            "version": v.name,
            "creation_date": v.creation_date,
            "author": v.author,
            "commit_hexsha": v.commit_hexsha,
            "unregistered_date": v.unregistered_date,
        }
        for o in reg.state.objects.values()
        for v in o.versions
    ]
    if dataframe:
        return (
            pd.DataFrame(model_registration_audit_trail)
            .sort_values("creation_date", ascending=False)
            .set_index(["creation_date", "name"])
        )
    return model_registration_audit_trail


def audit_promotion(repo: Union[str, Repo], dataframe: bool = False):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)
    label_assignment_audit_trail = [
        {
            "name": o.name,
            "label": l.name,
            "version": l.version,
            "creation_date": l.creation_date,
            "author": l.author,
            "commit_hexsha": l.commit_hexsha,
            "unregistered_date": l.unregistered_date,
        }
        for o in reg.state.objects.values()
        for l in o.labels
    ]
    if dataframe:
        return (
            pd.DataFrame(label_assignment_audit_trail)
            .sort_values("creation_date", ascending=False)
            .set_index(["creation_date", "name"])
        )
    return label_assignment_audit_trail
