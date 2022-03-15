import json
import logging
from functools import wraps

import click
import pandas as pd
from ruamel import yaml
from tabulate import tabulate, tabulate_formats

import gto
from gto.constants import LABEL, NAME, REF, VERSION
from gto.utils import serialize

arg_name = click.argument(NAME)
arg_version = click.argument(VERSION)
arg_label = click.argument(LABEL)
arg_ref = click.argument(REF)
option_repo = click.option("-r", "--repo", default=".", help="Repository to use")
option_format = click.option(
    "--format",
    "-f",
    default="yaml",
    help="Output format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
)
option_format_df = click.option(
    "--format",
    "-f",
    default="dataframe",
    help="Output format",
    type=click.Choice(["dataframe", "json", "yaml"], case_sensitive=False),
)
option_artifact = click.option("--artifact", "-a", default=None, help="Artifact name")
option_sort = click.option(
    "--sort", "-s", default="desc", help="Desc for recent first, Asc for older first"
)
option_format_table = click.option(
    "-ft",
    "--format-table",
    type=click.Choice(tabulate_formats),
    default="fancy_outline",
)

MISSING_VALUE = "-"


@click.group()
def cli():
    """\b
    Great Tool Ops. Turn your Git Repo into Artifact Registry:
    * Index your artifacts and add enrichments
    * Register artifact versions
    * Promote artifacts to environments
    * Act on new versions and promotions in CI
    """
    pd.set_option("expand_frame_repr", False)


def _set_log_level(ctx, param, value):  # pylint: disable=unused-argument
    if value:
        logger = logging.getLogger("gto")
        logger.handlers[0].setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        from gto.config import CONFIG  # pylint: disable=import-outside-toplevel

        click.echo(CONFIG.__repr_str__("\n"))
        click.echo()


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
@option_repo
@arg_name
@click.argument("type")
@click.argument("path")
def add(repo: str, type: str, name: str, path: str):
    """Add an object to the Index"""
    gto.api.add(repo, type, name, path)


@cli.command("rm")
@option_repo
@arg_name
def remove(repo: str, name: str):
    """Remove an object from the Index"""
    gto.api.remove(repo, name)


@gto_command()
@option_repo
@arg_name
@arg_ref
@click.option("--version", "-v", default=None, help="Version to promote")
@click.option(
    "--bump", "-b", default=None, help="The exact part to use when bumping a version"
)
def register(repo: str, name: str, ref: str, version: str, bump: str):
    """Register new object version"""
    registered_version = gto.api.register(
        repo=repo, name=name, ref=ref, version=version, bump=bump
    )
    click.echo(
        f"Registered {registered_version.object} version {registered_version.name}"
    )


@gto_command()
@option_repo
@arg_name
@arg_version
def deprecate(repo: str, name: str, version: str):
    """Unregister object version"""
    gto.api.deprecate(repo, name, version)
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
    result = gto.api.promote(repo, name, label, promote_version, ref, name_version)
    click.echo(f"Promoted {name} version {result['version']} to label {label}")


@gto_command()
@option_repo
@arg_name
@click.option(
    "-iu",
    "--include-deprecated",
    is_flag=True,
    default=False,
    help="Include deprecated versions",
)
def latest(repo: str, name: str, include_deprecated: bool):
    """Return latest version for object"""
    latest_version = gto.api.find_latest_version(
        repo, name, include_deprecated=include_deprecated
    )
    if latest_version:
        click.echo(latest_version.name)
    else:
        click.echo("No versions found")


@gto_command()
@option_repo
@arg_name
@arg_label
def which(repo: str, name: str, label: str):
    """Return version of object with specific label active"""
    version = gto.api.find_active_label(repo, name, label)
    if version:
        click.echo(version.version)
    else:
        click.echo(f"No version of '{name}' with label '{label}' active")


@gto_command()
@option_repo
@arg_name
@arg_label
def demote(repo: str, name: str, label: str):
    """De-promote object from given label"""
    gto.api.demote(repo, name, label)
    click.echo(f"Demoted {name} from label {label}")


@gto_command()
@arg_name
@click.option("--key", default=None, help="Which key to return")
def parse_tag(name: str, key: str):
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    click.echo(parsed)


@gto_command()
@option_repo
@click.argument("ref")
@option_format
def check_ref(repo: str, ref: str, format: str):
    """Find out what have been registered/promoted in the provided ref"""
    result = gto.api.check_ref(repo, ref)
    if format == "yaml":
        click.echo(yaml.dump(result, default_style='"'))
    elif format == "json":
        click.echo(json.dumps(serialize(result)))


@gto_command()
@option_repo
@option_format_df
@option_format_table
def show(repo: str, format: str, format_table: str):
    """Show current registry state"""
    if format == "dataframe":
        status_df = gto.api.show(repo, dataframe=True)
        status_df.reset_index(inplace=True)
        if len(status_df):
            click.echo(
                tabulate(
                    status_df,
                    headers=["/".join([i for i in x if i]) for x in status_df.columns],
                    tablefmt=format_table,
                    showindex=False,
                    missingval=MISSING_VALUE,
                )
            )
        else:
            click.echo("No tracked artifacts detected in the current workspace")
    elif format == "json":
        click.echo(json.dumps(gto.api.show(repo, dataframe=False)))
    elif format == "yaml":
        click.echo(
            yaml.dump(gto.api.show(repo, dataframe=False), default_flow_style=False)
        )


@gto_command()
@option_repo
@click.argument("action")
@option_artifact
@option_sort
@option_format_table
def audit(repo: str, action: str, artifact: str, sort: str, format_table: str):
    """Audit registry state"""

    if action in {"reg", "registration", "register", "all"}:
        click.echo("\n=== Registration audit trail ===")
        audit_trail_df = gto.api.audit_registration(
            repo, artifact, sort, dataframe=True
        )
        audit_trail_df.reset_index(inplace=True)
        click.echo(
            tabulate(
                audit_trail_df,
                headers="keys",
                tablefmt=format_table,
                showindex=False,
                missingval=MISSING_VALUE,
            )
            if len(audit_trail_df)
            else "No registered versions detected in the current workspace"
        )

    if action in {"promote", "promotion", "all"}:
        click.echo("\n=== Promotion audit trail ===")
        promotion_trail_df = gto.api.audit_promotion(
            repo, artifact, sort, dataframe=True
        )
        promotion_trail_df.reset_index(inplace=True)
        click.echo(
            tabulate(
                promotion_trail_df,
                headers="keys",
                tablefmt=format_table,
                showindex=False,
                missingval=MISSING_VALUE,
            )
            if len(promotion_trail_df)
            else "No promotions detected in the current workspace"
        )


@gto_command()
@option_repo
@option_artifact
@option_format_df
@option_format_table
@option_sort
def history(repo: str, artifact: str, format: str, format_table: str, sort: str):
    """Show history of object"""
    if format == "dataframe":
        history_df = gto.api.history(repo, artifact, sort, dataframe=True)
        history_df.reset_index(inplace=True)
        click.echo(
            tabulate(
                history_df,
                headers="keys",
                tablefmt=format_table,
                showindex=False,
                missingval=MISSING_VALUE,
            )
            if len(history_df)
            else "No history found"
        )
    elif format == "json":
        click.echo(json.dumps(gto.api.history(repo, artifact, sort, dataframe=False)))
    elif format == "yaml":
        click.echo(
            yaml.dump(
                gto.api.history(repo, artifact, dataframe=False),
                sort,
                default_flow_style=False,
            )
        )


@gto_command()
@option_repo
@click.option("--in-use", is_flag=True, default=False, help="Show only in-use labels")
def print_envs(repo: str, in_use: bool):
    """Return list of envs in the registry.
    If "in_use", return only those which are in use (skip deprecated).
    If not, return all available: either all allowed or all ever used.
    """
    click.echo(gto.api.get_envs(repo, in_use=in_use))


@gto_command()
@option_repo
@option_format
def print_state(repo: str, format: str):
    """Print current registry state"""
    state = serialize(gto.api.get_state(repo).dict())
    if format == "yaml":
        click.echo(yaml.dump(serialize(state), default_flow_style=False))
    elif format == "json":
        click.echo(json.dumps(state))


@gto_command()
@option_repo
@option_format
def print_index(repo: str, format: str):
    index = gto.api.get_index(repo).object_centric_representation()
    if format == "yaml":
        click.echo(
            yaml.dump(
                dict(index),
                default_flow_style=False,
            )
        )
    elif format == "json":
        click.echo(json.dumps(index))


if __name__ == "__main__":
    cli()
