import logging
from functools import wraps

import click
import pandas as pd
from tabulate import tabulate_formats

import gto
from gto.constants import LABEL, NAME, REF, VERSION
from gto.utils import format_echo, serialize

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
option_name = click.option("--name", "-n", default=None, help="Artifact name")
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
@option_format
def parse_tag(name: str, key: str, format: str):
    """Given git tag name created by this tool, parse it and return it's parts"""
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, format)


@gto_command()
@option_repo
@click.argument("ref")
@option_format
def check_ref(repo: str, ref: str, format: str):
    """Find out what have been registered/promoted in the provided ref"""
    result = gto.api.check_ref(repo, ref)
    format_echo(result, format)


@gto_command()
@option_repo
@option_format_df
@option_format_table
def show(repo: str, format: str, format_table: str):
    """Show current registry state"""
    if format == "dataframe":
        format_echo(
            gto.api.show(repo, dataframe=True),
            format=format,
            format_table=format_table,
            if_empty="No tracked artifacts detected in the current workspace",
        )
    else:
        format_echo(gto.api.show(repo, dataframe=False), format=format)


class ALIASES:
    REGISTER = ["reg", "registration", "registrations", "register"]
    PROMOTE = ["prom", "promote", "promotion", "promotions"]


@gto_command()
@option_repo
@click.option(
    "-a",
    "--action",
    default=["register", "promote"],
    multiple=True,
    help="What actions to audit",
    type=click.Choice(ALIASES.REGISTER + ALIASES.PROMOTE),
)
@option_name
@option_sort
@option_format_table
def audit(repo: str, action: str, name: str, sort: str, format_table: str):
    """Audit registry state"""

    if any(a in ALIASES.REGISTER for a in action):
        click.echo("\n=== Registration audit trail ===")
        format_echo(
            gto.api.audit_registration(repo, name, sort, dataframe=True),
            format="dataframe",
            format_table=format_table,
            if_empty="No registered versions detected in the current workspace",
        )

    if any(a in ALIASES.PROMOTE for a in action):
        click.echo("\n=== Promotion audit trail ===")
        format_echo(
            gto.api.audit_promotion(repo, name, sort, dataframe=True),
            format="dataframe",
            format_table=format_table,
            if_empty="No promotions detected in the current workspace",
        )


@gto_command()
@option_repo
@option_name
@option_format_df
@option_format_table
@option_sort
def history(repo: str, name: str, format: str, format_table: str, sort: str):
    """Show history of object"""
    if format == "dataframe":
        format_echo(
            gto.api.history(repo, name, sort, dataframe=True),
            format=format,
            format_table=format_table,
            if_empty="No history found",
        )
    else:
        format_echo(gto.api.history(repo, name, sort, dataframe=False), format=format)


@gto_command()
@option_repo
@click.option("--in-use", is_flag=True, default=False, help="Show only in-use labels")
def print_envs(repo: str, in_use: bool):
    """Return list of envs in the registry.
    If "in_use", return only those which are in use (skip deprecated).
    If not, return all available: either all allowed or all ever used.
    """
    click.echo(gto.api.get_envs(repo, in_use=in_use))


@gto_command(hidden=True)
@option_repo
@option_format
def print_state(repo: str, format: str):
    """Print current registry state"""
    state = serialize(gto.api.get_state(repo).dict())
    format_echo(state, format)


@gto_command(hidden=True)
@option_repo
@option_format
def print_index(repo: str, format: str):
    index = gto.api.get_index(repo).object_centric_representation()
    format_echo(index, format)


if __name__ == "__main__":
    cli()
