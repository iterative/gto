import warnings

import click
import git
import numpy as np
import pandas as pd
from IPython.display import display

from .registry import Registry


@click.group()
def cli():
    """Early prototype for registering/label assignment for tags-based approach"""
    pass


@cli.command()
@click.argument("model")
@click.argument("version")
def register(model, version):
    """Register new model version"""
    Registry().register(model, version)
    click.echo(f"Registered model {model} version {version}")


@cli.command()
@click.argument("model")
@click.argument("version")
def unregister(model, version):
    """Unregister model version"""
    Registry().unregister(model, version)
    click.echo(f"Unregistered model {model} version {version}")


@cli.command()
@click.argument("model")
@click.argument("version")
@click.argument("label")
@click.option(
    "--name-version",
    default=None,
    help="If you specify hexsha instead of version, then model will be registered first with this name.\n"
    "If you won't provide name, we'll try to bump it automatically.",
)
def promote(model, version, label, name_version):
    """Assign label to specific model version"""
    result = Registry().promote(model, version, label, name_version)
    click.echo(f"Promoted model {model} version {result['version']} to label {label}")


@cli.command()
@click.argument("model")
def latest(model):
    """Return latest version for model"""
    model = [m for m in Registry().models if m.name == model][0]
    click.echo(model.latest_version)


@cli.command()
@click.argument("model")
@click.argument("label")
def which(model, label):
    """Return version of model with specific label active"""
    version = Registry().which(model, label, raise_if_not_found=False)
    if version:
        click.echo(version)
    else:
        click.echo(f"No version of model '{model}' with label '{label}' active")


@cli.command()
@click.argument("model")
@click.argument("label")
def demote(model, label):
    """De-promote model from given label"""
    Registry().demote(model, label)
    click.echo(f"Demoted model {model} from label {label}")


@cli.command()
def show():
    """Show current registry state"""

    reg = Registry()
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
