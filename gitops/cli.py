import warnings

import click
import numpy as np
import pandas as pd
from IPython.display import display
from ruamel import yaml

from . import init_registry
from .constants import LABEL, NAME, REF, VERSION
from .utils import serialize

arg_name = click.argument(NAME)
arg_version = click.argument(VERSION)
arg_label = click.argument(LABEL)
arg_ref = click.argument(REF)
option_repo = click.option("-r", "--repo", default=".", help="Repository to use")


@click.group()
def cli():
    """Early prototype for registering/label assignment for tags-based approach"""


@cli.command()
@arg_name
@click.argument("type")
@click.argument("path")
@option_repo
def add(name: str, type: str, path: str, repo: str):
    """Add an object to the Index, e.g.
    $ gitops index name model path
    """
    init_registry(repo=repo).index.add(name, type, path)


@cli.command()
@option_repo
@arg_name
@arg_version
@arg_ref
def register(repo: str, name: str, version: str, ref: str):
    """Register new object version"""
    init_registry(repo=repo).register(name, version, ref)
    click.echo(f"Registered {name} version {version}")


@cli.command()
@option_repo
@arg_name
@arg_version
def unregister(repo: str, name: str, version: str):
    """Unregister object version"""
    init_registry(repo=repo).unregister(name, version)
    click.echo(f"Unregistered {name} version {version}")


@cli.command()
@option_repo
@arg_name
@arg_label
@click.option(
    "--version",
    default=None,
    help="If you provide --commit, this will be used to name new version",
)
@click.option("--ref", default=None)
def promote(repo: str, name: str, label: str, version: str, ref: str):
    """Assign label to specific object version"""
    if ref is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    result = init_registry(repo=repo).promote(
        name, label, promote_version, ref, name_version
    )
    click.echo(f"Promoted {name} version {result['version']} to label {label}")


@cli.command()
@option_repo
@arg_name
def latest(repo: str, name: str):
    """Return latest version for object"""
    click.echo(init_registry(repo=repo).latest(name))


@cli.command()
@option_repo
@arg_name
@arg_label
def which(repo: str, name: str, label: str):
    """Return version of object with specific label active"""
    if version := init_registry(repo=repo).which(name, label, raise_if_not_found=False):
        click.echo(version)
    else:
        click.echo(f"No version of '{name}' with label '{label}' active")


@cli.command()
@option_repo
@arg_name
@arg_label
def demote(repo: str, name: str, label: str):
    """De-promote object from given label"""
    init_registry(repo=repo).demote(name, label)
    click.echo(f"Demoted {name} from label {label}")


@cli.command()
@click.argument("name")
@click.option("--key", default=None, help="Which key to return")
def parse_tag(name: str, key: str):
    from .tag import parse_name  # pylint: disable=import-outside-toplevel

    parsed = parse_name(name)
    if key:
        parsed = parsed[key]
    click.echo(parsed)
    return parsed


@cli.command()
@click.argument("ref")
def check_ref(ref: str):
    """Find out what have been registered/promoted in the provided ref"""
    reg = init_registry(".")
    if ref.startswith("refs/tags/"):
        ref = ref[len("refs/tags/") :]
    if ref.startswith("refs/heads/"):
        ref = reg.repo.commit(ref).hexsha
    result = reg.check_ref(ref)
    try:
        result_ = {
            action: {name: version.dict() for name, version in found.items()}
            for action, found in result.items()
        }
    except:  # pylint: disable=bare-except
        # this should be removed, here only for debugging purposes
        result_ = {
            action: {
                name: [v.dict() for v in version] for name, version in found.items()
            }
            for action, found in result.items()
        }
    click.echo(yaml.dump(result_, default_style='"'))
    return result


@cli.command()
@option_repo
def show(repo: str):
    """Show current registry state"""

    reg = init_registry(repo=repo)
    models_state = {
        o.name: dict(
            [
                (("version", "latest"), o.latest_version),
            ]
            + [
                (
                    ("version", l),
                    o.latest_labels[l].version
                    if o.latest_labels[l] is not None
                    else np.nan,
                )
                for l in o.unique_labels
            ]
        )
        for o in reg.state.objects.values()
    }
    click.echo("\n=== Active version and labels ===")
    display(pd.DataFrame.from_records(models_state).T)

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
    click.echo("\n=== Promotion audit trail ===")
    display(
        pd.DataFrame(label_assignment_audit_trail)
        .sort_values("creation_date", ascending=False)
        .set_index(["creation_date", "name"])
    )

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
    click.echo("\n=== Registration audit trail ===")
    display(
        pd.DataFrame(model_registration_audit_trail)
        .sort_values("creation_date", ascending=False)
        .set_index(["creation_date", "name"])
    )


@cli.command()
@option_repo
def print_state(repo: str):
    reg = init_registry(repo=repo)
    click.echo(yaml.dump(serialize(reg.state.dict())))


@cli.command()
@option_repo
def print_index(repo: str):
    import git  # pylint: disable=import-outside-toplevel

    from .index import RepoIndexManager  # pylint: disable=import-outside-toplevel

    click.echo(
        yaml.dump(
            dict(RepoIndexManager(repo=git.Repo(repo)).object_centric_representation()),
            default_flow_style=False,
        )
    )


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    pd.set_option("display.max_colwidth", 100)

    cli()
