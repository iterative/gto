import logging
import sys
from functools import wraps

import click
from tabulate import tabulate_formats

import gto
from gto.constants import NAME, PATH, REF, STAGE, TYPE, VERSION
from gto.utils import format_echo, make_ready_to_serialize

TABLE = "table"


class ALIAS:
    COMMIT = ["commit", "c"]
    REGISTER = ["register", "r", "reg", "registration", "registrations"]
    PROMOTE = ["promote", "p", "prom", "promotion", "promotions"]


arg_name = click.argument(NAME)
arg_version = click.argument(VERSION)
arg_stage = click.argument(STAGE)
arg_ref = click.argument(REF, default=None)
option_repo = click.option(
    "-r", "--repo", default=".", help="Repository to use", show_default=True
)
option_rev = click.option(
    "--rev", default=None, help="Repo revision", show_default=True
)
option_discover = click.option(
    "-d",
    "--discover",
    is_flag=True,
    default=False,
    help="Discover non-registered objects",
)
option_all_branches = click.option(
    "-a",
    "--all-branches",
    is_flag=True,
    default=False,
    help="Read heads from all branches",
)
option_all_commits = click.option(
    "-A", "--all-commits", is_flag=True, default=False, help="Read all commits"
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
option_format_table = click.option(
    "-ft",
    "--format-table",
    type=click.Choice(tabulate_formats),
    default="fancy_outline",
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
option_expected = click.option(
    "-e",
    "--expected",
    is_flag=True,
    default=False,
    help="Return exit code 1 if no result",
    show_default=True,
)
option_path = click.option(
    "--path", is_flag=True, default=False, help="Show path", show_default=True
)
option_ref = click.option(
    "--ref", is_flag=True, default=False, help="Show ref", show_default=True
)


@click.group()
def cli():
    """\b
    Git Tag Ops. Turn your Git Repo into Artifact Registry:
    * Register new versions of artifacts marking significant changes to them
    * Promote versions to signal downstream systems to act
    * Attach additional info about your artifact with Enrichments
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
@click.argument("repo", default=".")
@option_rev
@click.option("--type", default=None, help="Artifact type to list", show_default=True)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help="Print output in json format",
    show_default=True,
)
@click.option(
    "--table",
    is_flag=True,
    default=False,
    help="Print output in table format",
    show_default=True,
)
@option_format_table
def ls(repo, rev, type, json, table, format_table):
    """\b
    List all artifacts in the repository
    """
    assert not (json and table), "Only one of --json and --table can be used"
    if json:
        click.echo(format_echo(gto.api.ls(repo, rev, type), "json"))
    elif table:
        click.echo(
            format_echo(
                [gto.api.ls(repo, rev, type), "keys"],
                "table",
                format_table,
                if_empty="No artifacts found",
            )
        )
    else:
        click.echo(
            format_echo(
                [artifact["name"] for artifact in gto.api.ls(repo, rev, type)], "lines"
            )
        )


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
@click.option("--tag", multiple=True, default=[], help="Tags to add to artifact")
@click.option("-d", "--description", default="", help="Artifact description")
@click.option(
    "-u", "--update", is_flag=True, default=False, help="Update artifact if it exists"
)
def add(
    repo: str, type: str, name: str, path: str, virtual: bool, tag, description, update
):
    """Add the enrichment for the artifact

    Examples:
       Add new enrichment:
       $ gto add model nn models/neural_network.h5

       Update existing enrichment:
       $ gto add model nn models/neural_network.h5 --update
    """
    gto.api.add(
        repo,
        type,
        name,
        path,
        virtual,
        tags=tag,
        description=description,
        update=update,
    )


@cli.command("rm")
@option_repo
@arg_name
def remove(repo: str, name: str):
    """Remove the enrichment for given artifact

    Examples:
         $ gto rm nn
    """
    gto.api.remove(repo, name)


@gto_command()
@option_repo
@arg_name
@arg_ref
@click.option("--version", "--ver", default=None, help="Version name in SemVer format")
@click.option(
    "--bump", "-b", default=None, help="The exact part to use when bumping a version"
)
def register(repo: str, name: str, ref: str, version: str, bump: str):
    """Create git tag that marks the important artifact version

    Examples:
        Register new version at HEAD:
        $ gto register nn

        Register new version at a specific ref:
        $ gto register nn abc1234

        Assign version name explicitly:
        $ gto register nn --version v1.0.0

        Choose a part to bump version by:
        $ gto register nn --bump minor
    """
    registered_version = gto.api.register(
        repo=repo, name=name, ref=ref or "HEAD", version=version, bump=bump
    )
    click.echo(
        f"Registered {registered_version.artifact} version {registered_version.name}"
    )


@gto_command()
@option_repo
@arg_name
@arg_stage
@click.option(
    "--version",
    default=None,
    help="If you provide --ref, this will be used to name new version",
)
@click.option("--ref", default=None)
@click.option(
    "--simple",
    is_flag=True,
    default=False,
    help="Use simple notation: rf#prod instead of rf#prod-5",
)
def promote(repo, name, stage, version, ref, simple):
    """Assign stage to specific artifact version

    Examples:
        Promote HEAD:
        $ gto promote nn prod --ref HEAD

        Promote specific version:
        $ gto promote nn prod --version v1.0.0

        Promote without increment
        $ gto promote nn prod --ref HEAD --simple
    """
    if ref is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    promotion = gto.api.promote(
        repo, name, stage, promote_version, ref, name_version, simple=simple
    )
    click.echo(f"Promoted {name} version {promotion.version} to stage {stage}")


@gto_command()
@option_repo
@arg_name
@option_path
@option_ref
def latest(repo: str, name: str, path: bool, ref: bool):
    """Return latest version of artifact

    Examples:
        $ gto latest nn
    """
    assert not (path and ref), "--path and --ref are mutually exclusive"
    latest_version = gto.api.find_latest_version(repo, name)
    if latest_version:
        if path:
            click.echo(latest_version.artifact.path)
        elif ref:
            click.echo(latest_version.commit_hexsha)
        else:
            click.echo(latest_version.name)


@gto_command()
@option_repo
@arg_name
@arg_stage
@option_path
@option_ref
def which(repo: str, name: str, stage: str, path: bool, ref: bool):
    """Return version of artifact with specific stage active

    Exampels:
        $ gto which nn prod

        Print path to artifact:
        $ gto which nn prod --path

        Print commit hexsha:
        $ gto which nn prod --ref
    """
    assert not (path and ref), "--path and --ref are mutually exclusive"
    version = gto.api.find_promotion(repo, name, stage)
    if version:
        if path:
            click.echo(version.artifact.path)
        elif ref:
            click.echo(version.commit_hexsha)
        else:
            click.echo(version.version)


@gto_command(hidden=True)
@arg_name
@click.option("--key", default=None, help="Which key to return")
@option_format
def parse_tag(name: str, key: str, format: str):
    """Given git tag name created by this tool, parse it and return it's parts

    Examples:
        $ gto parse-tag rf@v1.0.0
        $ gto parse-tag rf#prod
    """
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, format)


@gto_command()
@option_repo
@click.argument("ref")
@option_format
def check_ref(repo: str, ref: str, format: str):
    """Find out artifact & version registered/promoted with the provided ref

    Examples:
        $ gto check-ref rf@v1.0.0
        $ gto check-ref rf#prod
    """
    result = gto.api.check_ref(repo, ref)
    format_echo(result, format)


@gto_command()
@option_repo
@click.argument("object", default="registry")
@option_discover
@option_all_branches
@option_all_commits
@option_format_df
@option_format_table
def show(
    repo: str,
    object: str,
    discover: bool,
    all_branches,
    all_commits,
    format: str,
    format_table: str,
):
    """Show current registry state or specific artifact

    Examples:
        Show the registry:
        $ gto show

        Discover non-registered artifacts that have enrichments:
        $ gto show --discover

        Show versions of specific artifact in registry:
        $ gto show nn

        Discover potential versions (i.e. commits with enrichments):
        $ gto show nn --discover

        Use --all-branches and --all-commits to read more than just HEAD:
        $ gto show --all-branches
        $ gto show nn --all-commits
    """
    # TODO: make proper name resolving?
    # e.g. querying artifact named "registry" with artifact/registry
    if format == TABLE:
        format_echo(
            gto.api.show(
                repo,
                object=object,
                discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                table=True,
            ),
            format=format,
            format_table=format_table,
            if_empty="Nothing found in the current workspace",
        )
    else:
        format_echo(
            gto.api.show(
                repo,
                object=object,
                discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                table=False,
            ),
            format=format,
        )


@gto_command(hidden=True)
@option_repo
@option_format_df
@option_format_table
def show_registry(repo: str, format: str, format_table: str):
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


@gto_command(hidden=True)
@option_repo
@click.argument("name")
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help="Print output in json format",
    show_default=True,
)
@click.option(
    "--table",
    is_flag=True,
    default=False,
    help="Print output in table format",
    show_default=True,
)
@option_format_table
def show_versions(repo, name, json, table, format_table):
    """\b
    List all artifact versions in the repository
    """
    # TODO: add sort?
    assert not (json and table), "Only one of --json and --table can be used"
    versions = gto.api._show_versions(repo, name)  # pylint: disable=protected-access
    if json:
        click.echo(format_echo(versions, "json"))
    elif table:
        click.echo(
            format_echo(
                versions,
                "table",
                format_table,
                if_empty="No versions found",
            )
        )
    else:
        click.echo(format_echo([v["name"] for v in versions], "lines"))


@gto_command()
@option_repo
@click.argument("name", required=False, default=None)
@option_discover
@option_all_branches
@option_all_commits
# @click.option(
#     "--action",
#     required=False,
#     type=click.Choice(ALIAS.COMMIT + ALIAS.REGISTER + ALIAS.PROMOTE),
#     nargs=-1,
# )
@option_format_df
@option_format_table
@option_sort
def history(
    repo: str,
    name: str,
    discover,
    all_branches,
    all_commits,
    format: str,
    format_table: str,
    sort: str,
):
    """Show history of artifact

    Examples:
        $ gto history nn

        Discover enrichment for artifact (check only HEAD by default):
        $ gto history nn --discover

        Use --all-branches and --all-commits to read more than just HEAD:
        $ gto history nn --discover --all-commits
    """
    if format == TABLE:
        format_echo(
            gto.api.history(
                repo,
                name,
                discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                sort=sort,
                table=True,
            ),
            format=format,
            format_table=format_table,
            if_empty="No history found",
        )
    else:
        format_echo(
            gto.api.history(
                repo,
                name,
                discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                sort=sort,
                table=False,
            ),
            format=format,
        )


@gto_command()
@option_repo
@click.option(
    "--in-use",
    is_flag=True,
    default=False,
    help="Show only in-use stages",
    show_default=True,
)
def print_stages(repo: str, in_use: bool):
    """Return list of stages in the registry.
    If "in_use", return only those which are in use (among non-deprecated artifacts).
    If not, return all available: either all allowed or all ever used.
    """
    format_echo(gto.api.get_stages(repo, in_use=in_use), "lines")


@gto_command(hidden=True)
@option_repo
@option_format
def print_state(repo: str, format: str):
    """Technical cmd: Print current registry state"""
    state = make_ready_to_serialize(
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


@gto_command()
@option_repo
@arg_name
@option_rev
def describe(repo, name: str, rev):
    """Find enrichments for the artifact

    Examples:
        $ gto describe nn
    """
    infos = gto.api.describe(repo=repo, name=name, rev=rev)
    for info in infos:
        click.echo(info.get_human_readable())


if __name__ == "__main__":
    cli()
