import logging
from collections import defaultdict
from enum import Enum  # , EnumMeta, _EnumDict
from functools import partial, wraps
from gettext import gettext
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import click
import typer
from click import Abort, ClickException, Command, Context, HelpFormatter
from click.exceptions import Exit
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

    # def collect_usage_pieces(self, ctx: Context) -> List[str]:
    #     return [p.lower() for p in super().collect_usage_pieces(ctx)]

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
option_rev = Option("HEAD", "--rev", help="Repo revision to use", show_default=True)
option_repo = Option(".", "-r", "--repo", help="Repository to use", show_default=True)
# option_discover = Option(
#     False, "-d", "--discover", is_flag=True, help="Discover non-registered artifacts"
# )
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
option_plain = Option(
    False,
    "--plain",
    is_flag=True,
    help="Print table in grep-able format",
    show_default=True,
)
option_name_only = Option(
    False,
    "--name-only",
    is_flag=True,
    help="Print names only",
    show_default=True,
)
option_table = Option(
    False,
    "--table",
    is_flag=True,
    help="Print output in table format",
    show_default=True,
)
option_type = Option(None, "--type", help="Artifact type")
option_path = Option(None, "--path", help="Artifact path")
option_virtual = Option(
    False,
    "--virtual",
    is_flag=True,
    help="Virtual artifact that wasn't committed to Git",
)
option_tag = Option(None, "--tag", help="Tags to add to artifact")
option_description = Option("", "-d", "--description", help="Artifact description")


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
                        "Please report it here: <https://github.com/iterative/gto/issues>"
                    )
            finally:
                # TODO: analytics
                error  # pylint: disable=pointless-statement
                # send_cli_call(cmd_name, error_msg=error, **res)

        return inner

    return decorator


@gto_command(section=COMMANDS.REGISTER_PROMOTE)
def register(
    repo: str = option_repo,
    name: str = arg_name,
    ref: str = Argument("HEAD", help="Git reference to use for registration"),
    version: Optional[str] = Option(
        None, "--version", "--ver", help="Version name in SemVer format"
    ),
    bump: Optional[str] = Option(
        None, "--bump", "-b", help="The exact part to increment when bumping a version"
    ),
    inherit_from: Optional[str] = Option(
        None,
        "--inherit",
        help="Inherit artifact details from another version. Default - latest version.",
    ),
    type: Optional[str] = option_type,
    path: Optional[str] = option_path,
    virtual: bool = option_virtual,
    tag: List[str] = option_tag,
    description: str = option_description,
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
    gto.api.register(
        repo=repo,
        name=name,
        ref=ref or "HEAD",
        version=version,
        bump=bump,
        stdout=True,
        type=type,
        path=path,
        virtual=virtual,
        tags=tag,
        description=description,
        inherit_from=inherit_from,
    )


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
    inherit_from: Optional[str] = Option(
        None, "--inherit", help="Inherit artifact details from another version"
    ),
    type: Optional[str] = option_type,
    path: Optional[str] = option_path,
    virtual: bool = option_virtual,
    tag: List[str] = option_tag,
    description: str = option_description,
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
    gto.api.promote(
        repo,
        name,
        stage,
        promote_version,
        ref,
        name_version,
        simple=simple,
        stdout=True,
        type=type,
        path=path,
        virtual=virtual,
        tags=tag,
        description=description,
        inherit_from=inherit_from,
    )


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
            echo(latest_version.artifact.path)
        elif ref:
            echo(latest_version.tag or latest_version.commit_hexsha)
        else:
            echo(latest_version.name)


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
            echo(version.artifact.path)
        elif ref:
            echo(version.tag or version.commit_hexsha)
        else:
            echo(version.version)


@gto_command(hidden=True)
def parse_tag(
    name: str = arg_name,
    key: Optional[str] = Option(None, "--key", help="Which key to return"),
):
    """Given git tag name created by this tool, parse it and return it's parts

    Examples:
        $ gto parse-tag rf@v1.0.0
        $ gto parse-tag rf#prod
    """
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, "json")


@gto_command(section=COMMANDS.CI)
def check_ref(
    repo: str = option_repo,
    ref: str = Argument(..., help="Git reference to analyze"),
):
    """Find out artifact & version registered/promoted with the provided ref

    Examples:
        $ gto check-ref rf@v1.0.0
        $ gto check-ref rf#prod
    """
    result = gto.api.check_ref(repo, ref)
    format_echo(result, "json")


@gto_command(section=COMMANDS.REGISTRY)
def show(
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show registry."),
    # discover: bool = option_discover,
    all_branches: bool = option_all_branches,
    all_commits: bool = option_all_commits,
    json: bool = option_json,
    plain: bool = option_plain,
    name_only: bool = option_name_only,
):
    """Show current registry state or specific artifact

    Examples:
        Show the registry:
        $ gto show

        Show versions of specific artifact in registry:
        $ gto show nn

        Use --all-branches and --all-commits to read more than just HEAD:
        $ gto show --all-branches
        $ gto show nn --all-commits
    """
    # TODO: make proper name resolving?
    # e.g. querying artifact named "registry" with artifact/registry
    assert (
        sum(bool(i) for i in (json, plain, name_only)) <= 1
    ), "Only one output format allowed"
    if name_only or json:
        output = gto.api.show(
            repo,
            name=name,
            # discover=discover,
            all_branches=all_branches,
            all_commits=all_commits,
            table=False,
        )
        if name_only:
            format_echo(output, "lines")
        else:
            format_echo(output, "json")
    else:
        format_echo(
            gto.api.show(
                repo,
                name=name,
                # discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                table=True,
            ),
            format="table",
            format_table="plain" if plain else "fancy_outline",
            if_empty="Nothing found in the current workspace",
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
    # discover: bool = option_discover,
    all_branches: bool = option_all_branches,
    all_commits: bool = option_all_commits,
    json: bool = option_json,
    plain: bool = option_plain,
    sort: str = option_sort,
):
    """Show history of artifact

    Examples:
        $ gto history nn

        Use --all-branches and --all-commits to read more than just HEAD:
        $ gto history nn --all-commits
    """
    assert sum(bool(i) for i in (json, plain)) <= 1, "Only one output format allowed"
    if json:
        format_echo(
            gto.api.history(
                repo,
                name,
                # discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                sort=sort,
                table=False,
            ),
            format="json",
        )
    else:
        format_echo(
            gto.api.history(
                repo,
                name,
                # discover=discover,
                all_branches=all_branches,
                all_commits=all_commits,
                sort=sort,
                table=True,
            ),
            format="table",
            format_table="plain" if plain else "fancy_outline",
            if_empty="No history found",
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
def print_state(repo: str = option_repo):
    """Technical cmd: Print current registry state

    Examples:
        $ gto print-state
    """
    state = make_ready_to_serialize(
        gto.api._get_state(repo).dict()  # pylint: disable=protected-access
    )
    format_echo(state, "json")


@gto_command(hidden=True)
def print_index(repo: str = option_repo):
    """Technical cmd: Print repo index

    Examples:
        $ gto print-index
    """
    index = gto.api.get_index(repo).artifact_centric_representation()
    format_echo(index, "json")


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
        echo(info.get_human_readable())


if __name__ == "__main__":
    app()
