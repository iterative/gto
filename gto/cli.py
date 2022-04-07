import logging
import sys
from collections import defaultdict
from enum import Enum, EnumMeta, _EnumDict
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
from gto.constants import NAME, PATH, REF, STAGE, TYPE, VERSION
from gto.exceptions import GTOException, NotFound
from gto.ui import EMOJI_FAIL, EMOJI_MLEM, bold, cli_echo, color, echo
from gto.utils import format_echo, make_ready_to_serialize

TABLE = "table"


class ALIAS:
    REGISTER = ["register", "reg", "registration", "registrations"]
    PROMOTE = ["promote", "prom", "promotion", "promotions"]


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
    order = ["common", "object", "runtime", "section1", "section2", "other"]

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
        if len(commands) > 0:
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
                    with formatter.section(gettext(f"{section} commands".capitalize())):
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

arg_name = Argument(..., help="")
arg_version = Argument(..., help="")
arg_stage = Argument(..., help="")
arg_ref = Argument(..., help="")
option_repo = Option(".", "-r", "--repo", help="Repository to use", show_default=True)


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


class StrEnum(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


FormatTable = StrEnum("FormatTable", tabulate_formats, module=__name__, type=str)  # type: ignore
option_format_table = Option(
    "fancy_outline",
    "-ft",
    "--format-table",
    show_default=True,
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


@app.callback("gto", invoke_without_command=True, no_args_is_help=True)
def gto_callback(
    ctx: Context,
    show_version: bool = Option(False, "--version", help="Show version and exit"),
    verbose: bool = Option(False, "--verbose", "-v", help="Print debug messages"),
    traceback: bool = Option(False, "--traceback", "--tb", hidden=True),
):
    """\b
    Great Tool Ops. Turn your Git Repo into Artifact Registry:
    * Index files in repo as artifacts to make them visible for others
    * Register new versions of artifacts marking significant changes to them
    * Promote versions to signal downstream systems to act
    * Act on new versions and promotions in CI

    Examples:
        TODO
    """
    if ctx.invoked_subcommand is None and show_version:
        with cli_echo():
            echo(EMOJI_MLEM + f"GTO Version: {gto.__version__}")
    if verbose:
        logger = logging.getLogger("gto")
        logger.handlers[0].setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        from gto.config import CONFIG  # pylint: disable=import-outside-toplevel

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
                # error = str(type(e))
                raise
            except GTOException as e:
                # error = str(type(e))
                if ctx.obj["traceback"]:
                    raise
                with cli_echo():
                    echo(EMOJI_FAIL + color(str(e), col=typer.colors.RED))
                raise typer.Exit(1)
            except Exception as e:  # pylint: disable=broad-except
                # error = str(type(e))
                if ctx.obj["traceback"]:
                    raise
                with cli_echo():
                    echo(
                        EMOJI_FAIL
                        + color("Unexpected error: " + str(e), col=typer.colors.RED)
                    )
                    echo(
                        "Please report it here: <https://github.com/iterative/mlem/issues>"
                    )
            finally:
                """TODO: analytics"""
                # send_cli_call(cmd_name, error_msg=error, **res)

        return inner

    return decorator


@gto_command(section="section1")
def ls(
    repo: str = Argument(".", help="TODO"),
    rev: Optional[str] = Option(..., "--rev", help="Repo revision", show_default=True),
    type: Optional[str] = Option(
        ..., "--type", help="Artifact type to list", show_default=True
    ),
    json: bool = Option(
        False,
        "--json",
        is_flag=True,
        help="Print output in json format",
        show_default=True,
    ),
    table: bool = Option(
        False,
        "--table",
        is_flag=True,
        help="Print output in table format",
        show_default=True,
    ),
    format_table: FormatTable = option_format_table,  # type: ignore
):
    """\b
    List all artifacts in the repository
    """
    assert not (json and table), "Only one of --json and --table can be used"
    if json:
        echo(format_echo(gto.api.ls(repo, rev, type), "json"))
    elif table:
        echo(
            format_echo(
                [gto.api.ls(repo, rev, type), "keys"],
                "table",
                format_table,
                if_empty="No artifacts found",
            )
        )
    else:
        echo(
            format_echo(
                [artifact["name"] for artifact in gto.api.ls(repo, rev, type)], "lines"
            )
        )


@gto_command(section="section2")
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
):
    """Register new artifact (add it to the Index)

    Examples:
        TODO"""
    gto.api.add(repo, type, name, path, virtual, tags=tag, description=description)


@gto_command("rm")
def remove(repo: str = option_repo, name: str = arg_name):
    """Deregister the artifact (remove it from the Index)
    Examples:
        TODO"""
    gto.api.remove(repo, name)


@gto_command()
def register(
    repo: str = option_repo,
    name: str = arg_name,
    ref: str = arg_ref,
    version: Optional[str] = Option(
        None, "--version", "--ver", help="Version to promote"
    ),
    bump: Optional[str] = Option(
        None, "--bump", "-b", help="The exact part to use when bumping a version"
    ),
):
    """Tag the object with a version (git tags)

    Examples:
        TODO"""
    registered_version = gto.api.register(
        repo=repo, name=name, ref=ref, version=version, bump=bump
    )
    echo(f"Registered {registered_version.artifact} version {registered_version.name}")


@gto_command()
def promote(
    repo: str = option_repo,
    name: str = arg_name,
    stage: str = arg_stage,
    version: Optional[str] = Option(
        None,
        "--version",
        help="If you provide --ref, this will be used to name new version",
    ),
    ref: Optional[str] = Option(None, "--ref"),
):
    """Assign stage to specific artifact version"""
    if ref is not None:
        name_version = version
        promote_version = None
    else:
        name_version = None
        promote_version = version
    promotion = gto.api.promote(repo, name, stage, promote_version, ref, name_version)
    click.echo(f"Promoted {name} version {promotion.version} to stage {stage}")


@gto_command()
def latest(
    repo: str = option_repo,
    name: str = arg_name,
    path: bool = option_path,
    ref: bool = option_ref,
    expected: bool = option_expected,
):
    """Return latest version of artifact"""
    assert not (path and ref), "--path and --ref are mutually exclusive"
    latest_version = gto.api.find_latest_version(repo, name)
    if latest_version:
        if path:
            click.echo(latest_version.artifact.path)
        elif ref:
            click.echo(latest_version.commit_hexsha)
        else:
            click.echo(latest_version.name)
    elif expected:
        raise NotFound("No version found")
    else:
        click.echo("No versions found")


@gto_command()
def which(
    repo: str = option_repo,
    name: str = arg_name,
    stage: str = arg_stage,
    path: bool = option_path,
    ref: bool = option_ref,
    expected: bool = option_expected,
):
    """Return version of artifact with specific stage active"""
    assert not (path and ref), "--path and --ref are mutually exclusive"
    version = gto.api.find_promotion(repo, name, stage)
    if version:
        if path:
            click.echo(version.artifact.path)
        elif ref:
            click.echo(version.commit_hexsha)
        else:
            click.echo(version.version)
    elif expected:
        raise NotFound("Nothing is promoted to this stage right now")
    else:
        click.echo(f"No version of '{name}' with stage '{stage}' active")


@gto_command(hidden=True)
def parse_tag(
    name: str = arg_name,
    key: Optional[str] = Option(None, "--key", help="Which key to return"),
    format: Format = option_format,
):
    """Given git tag name created by this tool, parse it and return it's parts"""
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, format)


@gto_command()
def check_ref(
    repo: str = option_repo,
    ref: str = Argument(..., help="TODO"),
    format: Format = option_format,
):
    """Find out artifact & version registered/promoted with the provided ref"""
    result = gto.api.check_ref(repo, ref)
    format_echo(result, format)


@gto_command()
def show(
    repo: str = option_repo,
    object: str = Argument("registry"),
    format: FormatDF = option_format_df,
    format_table: FormatTable = option_format_table,  # type: ignore
):
    """Show current registry state or specific artifact"""
    # TODO: make proper name resolving?
    # e.g. querying artifact named "registry" with artifact/registry
    if format == FormatDF.table:
        format_echo(
            gto.api.show(repo, object=object, table=True),
            format=format,
            format_table=format_table,
            if_empty="Nothing found in the current workspace",
        )
    else:
        format_echo(gto.api.show(repo, object=object, table=False), format=format)


@gto_command(hidden=True)
def show_registry(
    repo: str = option_repo,
    format: FormatDF = option_format_df,
    format_table: FormatTable = option_format_table,  # type: ignore
):
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
def show_versions(
    repo: str = option_repo,
    name: str = Argument(...),
    json: bool = Option(
        False,
        "--json",
        is_flag=True,
        help="Print output in json format",
        show_default=True,
    ),
    table: bool = Option(
        False,
        "--table",
        is_flag=True,
        help="Print output in table format",
        show_default=True,
    ),
    format_table: FormatTable = option_format_table,  # type: ignore
):
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


Actions = StrEnum("Actions", ALIAS.REGISTER + ALIAS.PROMOTE, type=str)  # type: ignore


@gto_command()
def audit(
    repo: str = option_repo,
    action: List[Actions] = Argument(None),  # type: ignore
    name: str = arg_name,
    sort: str = option_sort,
    format_table: FormatTable = option_format_table,  # type: ignore
):
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
def history(
    repo: str = option_repo,
    name: str = arg_name,
    format: FormatDF = option_format_df,
    format_table: FormatTable = option_format_table,  # type: ignore
    sort: str = option_sort,
):
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
    """
    click.echo(gto.api.get_stages(repo, in_use=in_use))


@gto_command(hidden=True)
def print_state(repo: str = option_repo, format: Format = option_format):
    """Technical cmd: Print current registry state"""
    state = make_ready_to_serialize(
        gto.api._get_state(repo).dict()  # pylint: disable=protected-access
    )
    format_echo(state, format)


@gto_command(hidden=True)
def print_index(repo: str = option_repo, format: Format = option_format):
    """Technical cmd: Print repo index"""
    index = gto.api.get_index(repo).artifact_centric_representation()
    format_echo(index, format)


if __name__ == "__main__":
    app()
