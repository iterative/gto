import logging
import warnings
from functools import wraps

import click
import numpy as np
import pandas as pd
from IPython.display import display
from ruamel import yaml

from gto.constants import LABEL, NAME, REF, VERSION
from gto.index import FileIndexManager, RepoIndexManager
from gto.registry import GitRegistry
from gto.utils import serialize

arg_name = click.argument(NAME)
arg_version = click.argument(VERSION)
arg_label = click.argument(LABEL)
arg_ref = click.argument(REF)
option_repo = click.option("-r", "--repo", default=".", help="Repository to use")


@click.group()
def cli():
    """\b
    Great Tool Ops. Turn your Git Repo into Artifact Registry:
    * Index your artifacts and add enrichments
    * Register artifact versions
    * Promote artifacts to environments
    * Act on new versions and promotions in CI
    """


def _set_log_level(ctx, param, value):  # pylint: disable=unused-argument
    if value:
        logger = logging.getLogger("gto")
        logger.handlers[0].setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        from gto.config import CONFIG  # pylint: disable=import-outside-toplevel

        click.echo(CONFIG)


verbose_option = click.option(
    "-v",
    "--verbose",
    callback=_set_log_level,
    expose_value=False,
    is_eager=True,
    is_flag=True,
)


@wraps(cli.command)
def gto_command(*args, **kwargs):
    def decorator(func):
        return cli.command(*args, **kwargs)(verbose_option(func))

    return decorator


@gto_command()
@arg_name
@click.argument("type")
@click.argument("path")
@option_repo
def add(name: str, type: str, path: str, repo: str):
    """Add an object to the Index"""
    FileIndexManager(path=repo).add(name, type, path)


@cli.command("rm")
@arg_name
@option_repo
def remove(name: str, repo: str):
    """Remove an object from the Index"""
    FileIndexManager(path=repo).remove(name)


@gto_command()
@option_repo
@arg_name
@arg_version
@arg_ref
def register(repo: str, name: str, version: str, ref: str):
    """Register new object version"""
    GitRegistry.from_repo(repo).register(name, version, ref)
    click.echo(f"Registered {name} version {version}")


@gto_command()
@option_repo
@arg_name
@arg_version
def unregister(repo: str, name: str, version: str):
    """Unregister object version"""
    GitRegistry.from_repo(repo).unregister(name, version)
    click.echo(f"Unregistered {name} version {version}")


@gto_command()
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
    result = GitRegistry.from_repo(repo).promote(
        name, label, promote_version, ref, name_version
    )
    click.echo(f"Promoted {name} version {result['version']} to label {label}")


@gto_command()
@option_repo
@arg_name
def latest(repo: str, name: str):
    """Return latest version for object"""
    click.echo(GitRegistry.from_repo(repo).latest(name))


@gto_command()
@option_repo
@arg_name
@arg_label
def which(repo: str, name: str, label: str):
    """Return version of object with specific label active"""
    version = GitRegistry.from_repo(repo).which(name, label, raise_if_not_found=False)
    if version:
        click.echo(version)
    else:
        click.echo(f"No version of '{name}' with label '{label}' active")


@gto_command()
@option_repo
@arg_name
@arg_label
def demote(repo: str, name: str, label: str):
    """De-promote object from given label"""
    GitRegistry.from_repo(repo).demote(name, label)
    click.echo(f"Demoted {name} from label {label}")


@gto_command()
@click.argument("name")
@click.option("--key", default=None, help="Which key to return")
def parse_tag(name: str, key: str):
    from .tag import parse_name  # pylint: disable=import-outside-toplevel

    parsed = parse_name(name)
    if key:
        parsed = parsed[key]
    click.echo(parsed)
    return parsed


@gto_command()
@click.argument("ref")
def check_ref(ref: str):
    """Find out what have been registered/promoted in the provided ref"""
    reg = GitRegistry.from_repo(".")
    ref = ref.removeprefix("refs/tags/")
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


@gto_command()
@option_repo
def show(repo: str):
    """Show current registry state"""

    reg = GitRegistry.from_repo(repo)
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
    # click.echo("\n=== Active version and labels ===")
    display(pd.DataFrame.from_records(models_state).T)


@gto_command()
@click.argument("action")
@option_repo
def audit(action: str, repo: str):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)

    if action in {"reg", "registration", "register", "all"}:
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

    if action in {"promote", "promotion", "all"}:
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


@gto_command()
@option_repo
def print_state(repo: str):
    reg = GitRegistry.from_repo(repo)
    click.echo(yaml.dump(serialize(reg.state.dict())))


@gto_command()
@option_repo
def print_index(repo: str):
    click.echo(
        yaml.dump(
            dict(RepoIndexManager.from_path(repo).object_centric_representation()),
            default_flow_style=False,
        )
    )


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    pd.set_option("display.max_colwidth", 100)

    cli()
