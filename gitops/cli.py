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


@click.group()
def cli():
    """Early prototype for registering/label assignment for tags-based approach"""
    pass


@cli.command()
@arg_category
@arg_object
@arg_version
def register(category, object, version):
    """Register new object version"""
    init_registry().register(category, object, version)
    click.echo(f"Registered {category} {object} version {version}")


@cli.command()
@arg_category
@arg_object
@arg_version
def unregister(category, object, version):
    """Unregister object version"""
    init_registry().unregister(category, object, version)
    click.echo(f"Unregistered {category} {object} version {version}")


@cli.command()
@arg_category
@arg_object
@arg_label
@click.option(
    "--version",
    default=None,
    help="If you provide --commit, this will be used to name new version",
)
@click.option("--commit", default=None)
def promote(category, object, label, version, commit):
    """Assign label to specific object version"""
    if commit is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    result = init_registry().promote(
        category, object, label, promote_version, commit, name_version
    )
    click.echo(
        f"Promoted {category} {object} version {result['version']} to label {label}"
    )


@cli.command()
@arg_category
@arg_object
def latest(category, object):
    """Return latest version for object"""
    obj = [
        m
        for m in init_registry().objects
        if m.name == object and m.category == category
    ][0]
    click.echo(obj.latest_version)


@cli.command()
@arg_category
@arg_object
@arg_label
def which(category, object, label):
    """Return version of object with specific label active"""
    version = init_registry().which(category, object, label, raise_if_not_found=False)
    if version:
        click.echo(version)
    else:
        click.echo(f"No version of {category} '{object}' with label '{label}' active")


@cli.command()
@arg_category
@arg_object
@arg_label
def demote(category, object, label):
    """De-promote object from given label"""
    init_registry().demote(category, object, label)
    click.echo(f"Demoted {category} {object} from label {label}")


@cli.command()
def show():
    """Show current registry state"""

    reg = init_registry()
    models_state = {
        m.name: dict(
            [
                ("version", m.latest_version),
            ]
            + [
                (
                    ("version", l),
                    m.latest_labels[l].version
                    if m.latest_labels[l] is not None
                    else np.nan,
                )
                for l in m.unique_labels
            ]
        )
        for m in reg.objects
    }
    print("\n=== Current labels (MLflow dashboard) ===")
    display(pd.DataFrame.from_records(models_state).T)

    label_assignment_audit_trail = [
        {
            "model": m.name,
            "label": l.name,
            "version": l.version,
            "creation_date": l.creation_date,
            "author": l.author,
            "commit_hexsha": l.commit_hexsha,
            "tag_name": l.tag_name,
            "unregistered_date": l.unregistered_date,
        }
        for m in reg.objects
        for l in m.labels
    ]
    print("\n=== Label assignment audit trail ===")
    display(
        pd.DataFrame(label_assignment_audit_trail).sort_values(
            "creation_date", ascending=False
        )
    )

    model_registration_audit_trail = [
        {
            "model": m.name,
            "version": v.name,
            "creation_date": v.creation_date,
            "author": v.author,
            "commit_hexsha": v.commit_hexsha,
            "tag_name": v.tag_name,
            "unregistered_date": v.unregistered_date,
        }
        for m in reg.objects
        for v in m.versions
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
