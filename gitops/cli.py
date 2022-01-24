import warnings

import click
import numpy as np
import pandas as pd
from IPython.display import display

from . import init_registry

arg_category = click.argument("category")
arg_object = click.argument("object")
arg_version = click.argument("version")
arg_label = click.argument("label")
option_repo = click.option("-r", "--repo", default=".", help="Repository to use")


@click.group()
def cli():
    """Early prototype for registering/label assignment for tags-based approach"""


@cli.command()
@option_repo
@arg_category
@arg_object
@arg_version
def register(repo: str, category: str, object: str, version: str):
    """Register new object version"""
    init_registry(repo=repo).register(category, object, version)
    click.echo(f"Registered {category} {object} version {version}")


@cli.command()
@option_repo
@arg_category
@arg_object
@arg_version
def unregister(repo: str, category: str, object: str, version: str):
    """Unregister object version"""
    init_registry(repo=repo).unregister(category, object, version)
    click.echo(f"Unregistered {category} {object} version {version}")


@cli.command()
@option_repo
@arg_category
@arg_object
@arg_label
@click.option(
    "--version",
    default=None,
    help="If you provide --commit, this will be used to name new version",
)
@click.option("--commit", default=None)
def promote(
    repo: str, category: str, object: str, label: str, version: str, commit: str
):
    """Assign label to specific object version"""
    if commit is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    result = init_registry(repo=repo).promote(
        category, object, label, promote_version, commit, name_version
    )
    click.echo(
        f"Promoted {category} {object} version {result['version']} to label {label}"
    )


@cli.command()
@option_repo
@arg_category
@arg_object
def latest(repo: str, category: str, object: str):
    """Return latest version for object"""
    click.echo(init_registry(repo=repo).latest(category, object))


@cli.command()
@option_repo
@arg_category
@arg_object
@arg_label
def which(repo: str, category: str, object: str, label: str):
    """Return version of object with specific label active"""
    version = init_registry(repo=repo).which(
        category, object, label, raise_if_not_found=False
    )
    if version:
        click.echo(version)
    else:
        click.echo(f"No version of {category} '{object}' with label '{label}' active")


@cli.command()
@option_repo
@arg_category
@arg_object
@arg_label
def demote(repo: str, category: str, object: str, label: str):
    """De-promote object from given label"""
    init_registry(repo=repo).demote(category, object, label)
    click.echo(f"Demoted {category} {object} from label {label}")


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
        for o in reg.state.objects
    }
    print("\n=== Current labels (MLflow dashboard) ===")
    display(pd.DataFrame.from_records(models_state).T)

    label_assignment_audit_trail = [
        {
            "category": o.category,
            "object": o.name,
            "label": l.name,
            "version": l.version,
            "creation_date": l.creation_date,
            "author": l.author,
            "commit_hexsha": l.commit_hexsha,
            "unregistered_date": l.unregistered_date,
        }
        for o in reg.state.objects
        for l in o.labels
    ]
    print("\n=== Label assignment audit trail ===")
    display(
        pd.DataFrame(label_assignment_audit_trail).sort_values(
            "creation_date", ascending=False
        )
    )

    model_registration_audit_trail = [
        {
            "model": o.name,
            "version": v.name,
            "creation_date": v.creation_date,
            "author": v.author,
            "commit_hexsha": v.commit_hexsha,
            "unregistered_date": v.unregistered_date,
        }
        for o in reg.state.objects
        for v in o.versions
    ]
    print("\n=== Model registration audit trail ===")
    display(
        pd.DataFrame(model_registration_audit_trail).sort_values(
            "creation_date", ascending=False
        )
    )


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    pd.set_option("display.max_colwidth", 100)

    cli()
