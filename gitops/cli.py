import warnings

import click
import git
import numpy as np
import pandas as pd
from IPython.display import display

from . import init_registry


@click.group()
def cli():
    """Early prototype for registering/label assignment for tags-based approach"""
    pass


@cli.command()
@click.argument("model")
@click.argument("version")
def register(model, version):
    """Register new model version"""
    init_registry().register(model, version)
    click.echo(f"Registered model {model} version {version}")


@cli.command()
@click.argument("model")
@click.argument("version")
def unregister(model, version):
    """Unregister model version"""
    init_registry().unregister(model, version)
    click.echo(f"Unregistered model {model} version {version}")


@cli.command()
@click.argument("model")
@click.argument("label")
@click.option(
    "--version",
    default=None,
    help="If you provide --commit, this will be used to name new version",
)
@click.option(
    "--commit",
    default=None,
)
def promote(model, label, version, commit):
    """Assign label to specific model version"""
    if commit is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    result = init_registry().promote(model, label, promote_version, commit, name_version)
    click.echo(f"Promoted model {model} version {result['version']} to label {label}")


@cli.command()
@click.argument("model")
def latest(model):
    """Return latest version for model"""
    model = [m for m in init_registry().models if m.name == model][0]
    click.echo(model.latest_version)


@cli.command()
@click.argument("model")
@click.argument("label")
def which(model, label):
    """Return version of model with specific label active"""
    version = init_registry().which(model, label, raise_if_not_found=False)
    if version:
        click.echo(version)
    else:
        click.echo(f"No version of model '{model}' with label '{label}' active")


@cli.command()
@click.argument("model")
@click.argument("label")
def demote(model, label):
    """De-promote model from given label"""
    init_registry().demote(model, label)
    click.echo(f"Demoted model {model} from label {label}")


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
        for m in reg.models
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
        for m in reg.models
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
        for m in reg.models
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
