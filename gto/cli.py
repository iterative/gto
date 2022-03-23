import logging
import sys
from functools import wraps
from typing import Sequence

import click
from tabulate import tabulate_formats

import gto
from gto.constants import LABEL, NAME, PATH, REF, TYPE, VERSION
from gto.utils import format_echo, serialize

TABLE = "table"


class ALIAS:
    REGISTER = ["register", "reg", "registration", "registrations"]
    PROMOTE = ["promote", "prom", "promotion", "promotions"]


arg_name = click.argument(NAME)
arg_version = click.argument(VERSION)
arg_label = click.argument(LABEL)
arg_ref = click.argument(REF)
option_repo = click.option(
    "-r", "--repo", default=".", help="Repository to use", show_default=True
)
option_format = click.option(
    "--format",
    "-f",
    default="yaml",
    help="Output format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    show_default=True,
)
option_format_df = click.option(
    "--format",
    "-f",
    default=TABLE,
    help="Output format",
    type=click.Choice([TABLE, "json", "yaml"], case_sensitive=False),
    show_default=True,
)
option_name = click.option(
    "--name", "-n", default=None, help="Artifact name", show_default=True
)
option_sort = click.option(
    "--sort",
    "-s",
    default="desc",
    help="Desc for recent first, Asc for older first",
    show_default=True,
)
option_format_table = click.option(
    "-ft",
    "--format-table",
    type=click.Choice(tabulate_formats),
    default="fancy_outline",
    show_default=True,
)


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
    if value or gto.CONFIG.DEBUG:
        logger = logging.getLogger("gto")
        logger.handlers[0].setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        from gto.config import CONFIG  # pylint: disable=import-outside-toplevel

        click.echo(CONFIG.__repr_str__("\n"))
        click.echo()
    else:
        sys.tracebacklimit = 0


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
@click.argument(TYPE)
@arg_name
@click.argument(PATH)
@click.option(
    "--virtual",
    is_flag=True,
    default=False,
    help="Virtual artifact that wasn't committed to Git",
)
def add(repo: str, type: str, name: str, path: str, virtual: bool):
    """Register new artifact (add it to the Index)"""
    gto.api.add(repo, type, name, path, virtual)


@cli.command("rm")
@option_repo
@arg_name
def remove(repo: str, name: str):
    """Deregister the artifact (remove it from the Index)"""
    gto.api.remove(repo, name)


@gto_command()
@option_repo
@arg_name
@arg_ref
@click.option("--version", "--ver", default=None, help="Version to promote")
@click.option(
    "--bump", "-b", default=None, help="The exact part to use when bumping a version"
)
def register(repo: str, name: str, ref: str, version: str, bump: str):
    """Tag the object with a version (git tags)"""
    registered_version = gto.api.register(
        repo=repo, name=name, ref=ref, version=version, bump=bump
    )
    click.echo(
        f"Registered {registered_version.artifact} version {registered_version.name}"
    )


@gto_command()
@option_repo
@arg_name
@arg_version
def deprecate(repo: str, name: str, version: str):
    """Deprecate artifact version"""
    gto.api.deprecate(repo, name, version)
    click.echo(f"Deprecated {name} version {version}")


@gto_command()
@option_repo
@arg_name
@arg_label
@click.option(
    "--version",
    default=None,
    help="If you provide --ref, this will be used to name new version",
)
@click.option("--ref", default=None)
def promote(repo: str, name: str, label: str, version: str, ref: str):
    """Assign label to specific artifact version"""
    if ref is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    label_ = gto.api.promote(repo, name, label, promote_version, ref, name_version)
    click.echo(f"Promoted {name} version {label_.version} to label {label}")


# @gto_command()
# @option_repo
# @arg_name
# @arg_label
# def demote(repo: str, name: str, label: str):
#     """De-promote artifact from given label"""
#     gto.api.demote(repo, name, label)
#     click.echo(f"Demoted {name} from label {label}")


@gto_command()
@option_repo
@arg_name
@click.option(
    "-d",
    "--deprecated",
    is_flag=True,
    default=False,
    help="Include deprecated versions",
    show_default=True,
)
def latest(repo: str, name: str, include_deprecated: bool):
    """Return latest version of artifact"""
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
    """Return version of artifact with specific label active"""
    version = gto.api.find_active_label(repo, name, label)
    if version:
        click.echo(version.version)
    else:
        click.echo(f"No version of '{name}' with label '{label}' active")


@gto_command(hidden=True)
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
    """Find out artifact & version registered/promoted with the provided ref"""
    result = gto.api.check_ref(repo, ref)
    format_echo(result, format)


@gto_command()
@option_repo
@option_format_df
@option_format_table
def show(repo: str, format: str, format_table: str):
    """Show current registry state"""
    if format == TABLE:
        format_echo(
            gto.api.show(repo, table=True),
            format=format,
            format_table=format_table,
            if_empty="No tracked artifacts detected in the current workspace",
        )
    else:
        format_echo(gto.api.show(repo, table=False), format=format)


@gto_command()
@option_repo
@click.argument(
    "action",
    required=False,
    type=click.Choice(ALIAS.REGISTER + ALIAS.PROMOTE),
    nargs=-1,
)
@option_name
@option_sort
@option_format_table
def audit(repo: str, action: Sequence[str], name: str, sort: str, format_table: str):
    """Shows a journal of actions made in registry"""
    if not action:
        action = ALIAS.REGISTER[:1] + ALIAS.PROMOTE[:1]
    if any(a in ALIAS.REGISTER for a in action):
        click.echo("\n=== Registration audit trail ===")
        format_echo(
            gto.api.audit_registration(repo, name, sort, table=True),
            format=TABLE,
            format_table=format_table,
            if_empty="No registered versions detected in the current workspace",
        )

    if any(a in ALIAS.PROMOTE for a in action):
        click.echo("\n=== Promotion audit trail ===")
        format_echo(
            gto.api.audit_promotion(repo, name, sort, table=True),
            format=TABLE,
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
    """Show history of artifact"""
    if format == TABLE:
        format_echo(
            gto.api.history(repo, name, sort, table=True),
            format=format,
            format_table=format_table,
            if_empty="No history found",
        )
    else:
        format_echo(gto.api.history(repo, name, sort, table=False), format=format)


@gto_command()
@option_repo
@click.option(
    "--in-use",
    is_flag=True,
    default=False,
    help="Show only in-use labels",
    show_default=True,
)
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
    """Technical cmd: Print current registry state"""
    state = serialize(
        gto.api._get_state(repo).dict()  # pylint: disable=protected-access
    )
    format_echo(state, format)


@gto_command(hidden=True)
@option_repo
@option_format
def print_index(repo: str, format: str):
    """Technical cmd: Print repo index"""
    index = gto.api.get_index(repo).artifact_centric_representation()
    format_echo(index, format)


if __name__ == "__main__":
    cli()
