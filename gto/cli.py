import logging
import sys
from collections import defaultdict
from enum import Enum  # , EnumMeta, _EnumDict
from functools import partial, wraps
from gettext import gettext
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import click
import typer
from click import Abort, ClickException, Command, Context, HelpFormatter
from click.exceptions import Exit
from tabulate import tabulate_formats
from typer import Argument, Option, Typer
from typer.core import TyperCommand, TyperGroup

import gto
from gto.exceptions import GTOException
from gto.ui import EMOJI_FAIL, EMOJI_MLEM, bold, cli_echo, color, echo
from gto.utils import format_echo, make_ready_to_serialize

TABLE = "table"


class ALIAS:
    COMMIT = ["commit", "c"]
    REGISTER = ["register", "r", "reg", "registration", "registrations"]
    PROMOTE = ["promote", "p", "prom", "promotion", "promotions"]


class COMMANDS:
    REGISTRY = "Read the registry"
    REGISTER_PROMOTE = "Register and promote"
    ENRICHMENT = "Manage enrichments"
    CI = "Use in CI"


class GtoFormatter(click.HelpFormatter):
    def write_heading(self, heading: str) -> None:
        super().write_heading(bold(heading))


class GtoCliMixin(Command):
    def __init__(
        self,
        name: Optional[str],
        examples: Optional[str],
        section: str = "other",
        aliases: List[str] = None,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.examples = examples
        self.section = section
        self.aliases = aliases

    def get_help(self, ctx: Context) -> str:
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.
        """
        formatter = GtoFormatter(
            width=ctx.terminal_width, max_width=ctx.max_content_width
        )
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip("\n")

    def format_epilog(self, ctx: Context, formatter: HelpFormatter) -> None:
        super().format_epilog(ctx, formatter)
        if self.examples:
            with formatter.section("Examples"):
                formatter.write(self.examples)


def _extract_examples(
    help_str: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    if help_str is None:
        return None, None
    try:
        examples = help_str.index("Examples:")
    except ValueError:
        return None, help_str
    return help_str[examples + len("Examples:") + 1 :], help_str[:examples]


class GtoCommand(TyperCommand, GtoCliMixin):
    def __init__(
        self,
        name: Optional[str],
        section: str = "other",
        aliases: List[str] = None,
        help: Optional[str] = None,
        **kwargs,
    ):
        examples, help = _extract_examples(help)
        super().__init__(
            name,
            section=section,
            aliases=aliases,
            examples=examples,
            help=help,
            **kwargs,
        )


class GtoGroup(TyperGroup, GtoCliMixin):
    order = [
        COMMANDS.REGISTRY,
        COMMANDS.REGISTER_PROMOTE,
        COMMANDS.ENRICHMENT,
        COMMANDS.CI,
        "other",
    ]

    def __init__(
        self,
        name: Optional[str] = None,
        commands: Optional[Union[Dict[str, Command], Sequence[Command]]] = None,
        section: str = "other",
        aliases: List[str] = None,
        help: str = None,
        **attrs: Any,
    ) -> None:
        examples, help = _extract_examples(help)
        super().__init__(
            name,
            help=help,
            examples=examples,
            aliases=aliases,
            section=section,
            commands=commands,
            **attrs,
        )

    def format_commands(self, ctx: Context, formatter: HelpFormatter) -> None:
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if commands:
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            sections = defaultdict(list)
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                if isinstance(cmd, (GtoCommand, GtoGroup)):
                    section = cmd.section
                    aliases = f" ({','.join(cmd.aliases)})" if cmd.aliases else ""
                else:
                    section = "other"
                    aliases = ""

                sections[section].append((subcommand + aliases, help))

            for section in self.order:
                if sections[section]:
                    with formatter.section(gettext(section)):
                        formatter.write_dl(sections[section])

    def get_command(self, ctx: Context, cmd_name: str) -> Optional[Command]:
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if (
                isinstance(cmd, (GtoCommand, GtoGroup))
                and cmd.aliases
                and cmd_name in cmd.aliases
            ):
                return cmd
        return None


def MlemGroupSection(section):
    return partial(GtoGroup, section=section)


app = Typer(cls=GtoGroup, context_settings={"help_option_names": ["-h", "--help"]})

arg_name = Argument(..., help="Artifact name")
arg_version = Argument(..., help="Artifact version")
arg_stage = Argument(..., help="Stage to promote to")
arg_ref = Argument("HEAD", help="Git reference to use")
option_rev = Option("HEAD", "--rev", help="Repo revision to use", show_default=True)
option_repo = Option(".", "-r", "--repo", help="Repository to use", show_default=True)
option_discover = Option(
    False, "-d", "--discover", is_flag=True, help="Discover non-registered artifacts"
)
option_all_branches = Option(
    False,
    "-a",
    "--all-branches",
    is_flag=True,
    help="Read heads from all branches",
)
option_all_commits = Option(
    False, "-A", "--all-commits", is_flag=True, help="Read all commits"
)


class Format(str, Enum):
    json = "json"
    yaml = "yaml"


class FormatDF(str, Enum):
    json = "json"
    yaml = "yaml"
    table = "table"


option_format = Option(
    Format.yaml,
    "--format",
    "-f",
    help="Output format",
    show_default=True,
)
option_format_df = Option(
    FormatDF.table,
    "--format",
    "-f",
    help="Output format",
    show_default=True,
)


class StrEnum(Enum):  # str,
    def _generate_next_value_(
        name, start, count, last_values
    ):  # pylint: disable=no-self-argument
        return name


FormatTable = StrEnum("FormatTable", tabulate_formats, module=__name__, type=str)  # type: ignore  # pylint: disable=too-many-function-args, unexpected-keyword-arg
option_format_table = Option(
    "fancy_outline",
    "-ft",
    "--format-table",
    show_default=True,
    help="How to format the table",
)
option_name = Option(None, "--name", "-n", help="Artifact name", show_default=True)
option_sort = Option(
    "desc",
    "--sort",
    "-s",
    help="Desc for recent first, Asc for older first",
    show_default=True,
)
option_expected = Option(
    False,
    "-e",
    "--expected",
    is_flag=True,
    help="Return exit code 1 if no result",
    show_default=True,
)
option_path = Option(False, "--path", is_flag=True, help="Show path", show_default=True)
option_ref = Option(False, "--ref", is_flag=True, help="Show ref", show_default=True)
option_json = Option(
    False,
    "--json",
    is_flag=True,
    help="Print output in json format",
    show_default=True,
)
option_table = Option(
    False,
    "--table",
    is_flag=True,
    help="Print output in table format",
    show_default=True,
)


@app.callback("gto", invoke_without_command=True, no_args_is_help=True)
def gto_callback(
    ctx: Context,
    show_version: bool = Option(False, "--version", help="Show version and exit"),
    verbose: bool = Option(False, "--verbose", "-v", help="Print debug messages"),
    traceback: bool = Option(False, "--traceback", "--tb", hidden=True),
):
    """\b
    Git Tag Ops. Turn your Git Repo into Artifact Registry:
    * Register new versions of artifacts marking significant changes to them
    * Promote versions to signal downstream systems to act
    * Attach additional info about your artifact with Enrichments
    * Act on new versions and promotions in CI

    Examples:
        $ gto register nn HEAD  # Register new version
        $ gto promote nn staging --ref HEAD  # Promote version to Stage
        $ gto show  # See the registry state
        $ gto history  # See the history of events
    """
    if ctx.invoked_subcommand is None and show_version:
        with cli_echo():
            echo(f"{EMOJI_MLEM} GTO Version: {gto.__version__}")
    if verbose:
        logger = logging.getLogger("gto")
        logger.handlers[0].setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        from gto.config import (  # pylint: disable=import-outside-toplevel
            CONFIG,
        )

        echo(CONFIG.__repr_str__("\n"))
        echo()
    else:
        sys.tracebacklimit = 0

    ctx.obj = {"traceback": traceback}


def gto_command(*args, section="other", aliases=None, parent=app, **kwargs):
    def decorator(f):
        if len(args) > 0:
            cmd_name = args[0]
        else:
            cmd_name = kwargs.get("name", f.__name__)

        @parent.command(
            *args,
            **kwargs,
            cls=partial(GtoCommand, section=section, aliases=aliases),
        )
        @wraps(f)
        @click.pass_context
        def inner(ctx, *iargs, **ikwargs):
            res = {}
            error = None
            try:
                with cli_echo():
                    res = f(*iargs, **ikwargs) or {}
                res = {f"cmd_{cmd_name}_{k}": v for k, v in res.items()}
            except (ClickException, Exit, Abort) as e:
                error = str(type(e))
                raise
            except GTOException as e:
                error = str(type(e))
                if ctx.obj["traceback"]:
                    raise
                with cli_echo():
                    echo(EMOJI_FAIL + color(str(e), col=typer.colors.RED))
                raise typer.Exit(1)
            except Exception as e:  # pylint: disable=broad-except
                error = str(type(e))
                if ctx.obj["traceback"]:
                    raise
                with cli_echo():
                    echo(
                        (
                            EMOJI_FAIL
                            + color(f"Unexpected error: {str(e)}", col=typer.colors.RED)
                        )
                    )
                    echo(
                        "Please report it here: <https://github.com/iterative/mlem/issues>"
                    )
            finally:
                # TODO: analytics
                error  # pylint: disable=pointless-statement
                # send_cli_call(cmd_name, error_msg=error, **res)

        return inner

    return decorator


@gto_command(section=COMMANDS.ENRICHMENT)
def add(
    repo: str = option_repo,
    type: str = Argument(..., help="TODO"),
    name: str = arg_name,
    path: str = Argument(..., help="TODO"),
    virtual: bool = Option(
        False,
        "--virtual",
        is_flag=True,
        help="Virtual artifact that wasn't committed to Git",
    ),
    tag: List[str] = Option(..., "--tag", help="Tags to add to artifact"),
    description: str = Option("", "-d", "--description", help="Artifact description"),
    update: bool = Option(
        False, "-u", "--update", is_flag=True, help="Update artifact if it exists"
    ),
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


@gto_command("rm", section=COMMANDS.ENRICHMENT)
def remove(repo: str = option_repo, name: str = arg_name):
    """Remove the enrichment for given artifact

    Examples:
         $ gto rm nn
    """
    gto.api.remove(repo, name)


@gto_command(section=COMMANDS.REGISTER_PROMOTE)
def register(
    repo: str = option_repo,
    name: str = arg_name,
    ref: str = arg_ref,
    version: Optional[str] = Option(
        None, "--version", "--ver", help="Version name in SemVer format"
    ),
    bump: Optional[str] = Option(
        None, "--bump", "-b", help="The exact part to increment when bumping a version"
    ),
):
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
    echo(f"Registered {registered_version.artifact} version {registered_version.name}")


@gto_command(section=COMMANDS.REGISTER_PROMOTE)
def promote(
    repo: str = option_repo,
    name: str = arg_name,
    stage: str = arg_stage,
    version: Optional[str] = Option(
        None,
        "--version",
        help="If you provide --ref, this will be used to name new version",
    ),
    ref: Optional[str] = Option(None, "--ref", help="Git reference to promote"),
    simple: bool = Option(
        False,
        "--simple",
        is_flag=True,
        help="Use simple notation, e.g. rf#prod instead of rf#prod-5",
    ),
):
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


@gto_command(section=COMMANDS.REGISTRY)
def latest(
    repo: str = option_repo,
    name: str = arg_name,
    path: bool = option_path,
    ref: bool = option_ref,
):
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


@gto_command(section=COMMANDS.REGISTRY)
def which(
    repo: str = option_repo,
    name: str = arg_name,
    stage: str = arg_stage,
    path: bool = option_path,
    ref: bool = option_ref,
):
    """Return version of artifact with specific stage active

    Examples:
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
def parse_tag(
    name: str = arg_name,
    key: Optional[str] = Option(None, "--key", help="Which key to return"),
    format: Format = option_format,
):
    """Given git tag name created by this tool, parse it and return it's parts

    Examples:
        $ gto parse-tag rf@v1.0.0
        $ gto parse-tag rf#prod
    """
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, format)


@gto_command(section=COMMANDS.CI)
def check_ref(
    repo: str = option_repo,
    ref: str = Argument(..., help="TODO"),
    format: Format = option_format,
):
    """Find out artifact & version registered/promoted with the provided ref

    Examples:
        $ gto check-ref rf@v1.0.0
        $ gto check-ref rf#prod
    """
    result = gto.api.check_ref(repo, ref)
    format_echo(result, format)


@gto_command(section=COMMANDS.REGISTRY)
def show(
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show registry."),
    discover: bool = option_discover,
    all_branches: bool = option_all_branches,
    all_commits: bool = option_all_commits,
    format: FormatDF = option_format_df,
    format_table: FormatTable = option_format_table,  # type: ignore
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
    if format == FormatDF.table:
        format_echo(
            gto.api.show(
                repo,
                name=name,
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
                name=name,
                discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                table=False,
            ),
            format=format,
        )


# Actions = StrEnum("Actions", ALIAS.REGISTER + ALIAS.PROMOTE, type=str)  # type: ignore
# action: List[Actions] = Argument(None),  # type: ignore
# @click.option(
#     "--action",
#     required=False,
#     type=click.Choice(ALIAS.COMMIT + ALIAS.REGISTER + ALIAS.PROMOTE),
#     nargs=-1,
# )


@gto_command(section=COMMANDS.REGISTRY)
def history(
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show all."),
    discover: bool = option_discover,
    all_branches: bool = option_all_branches,
    all_commits: bool = option_all_commits,
    format: FormatDF = option_format_df,
    format_table: FormatTable = option_format_table,  # type: ignore
    sort: str = option_sort,
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


@gto_command(section=COMMANDS.REGISTRY)
def print_stages(
    repo: str = option_repo,
    in_use: bool = Option(
        False,
        "--in-use",
        is_flag=True,
        help="Show only in-use stages",
        show_default=True,
    ),
):
    """Return list of stages in the registry.
    If "in_use", return only those which are in use (among non-deprecated artifacts).
    If not, return all available: either all allowed or all ever used.

    Examples:
        $ gto print-stage
        $ gto print-stage --in-use
    """
    format_echo(gto.api.get_stages(repo, in_use=in_use), "lines")


@gto_command(hidden=True)
def print_state(repo: str = option_repo, format: Format = option_format):
    """Technical cmd: Print current registry state

    Examples:
        $ gto print-state
    """
    state = make_ready_to_serialize(
        gto.api._get_state(repo).dict()  # pylint: disable=protected-access
    )
    format_echo(state, format)


@gto_command(hidden=True)
def print_index(repo: str = option_repo, format: Format = option_format):
    """Technical cmd: Print repo index

    Examples:
        $ gto print-index
    """
    index = gto.api.get_index(repo).artifact_centric_representation()
    format_echo(index, format)


@gto_command(section=COMMANDS.ENRICHMENT)
def describe(
    repo: str = option_repo,
    name: str = arg_name,
    rev: str = option_rev,
):
    """Find enrichments for the artifact

    Examples:
        $ gto describe nn
    """
    infos = gto.api.describe(repo=repo, name=name, rev=rev)
    for info in infos:
        click.echo(info.get_human_readable())


if __name__ == "__main__":
    app()
