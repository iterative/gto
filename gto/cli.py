import logging
from collections import defaultdict
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
from gto.exceptions import GTOException, WrongArgs
from gto.ui import EMOJI_FAIL, EMOJI_GTO, EMOJI_OK, bold, cli_echo, color, echo
from gto.utils import format_echo, make_ready_to_serialize


class CommandGroups:
    querying = "Read the registry"
    modifying = "Modify artifacts"
    enriching = "Manage artifact enrichments"


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
        CommandGroups.querying,
        CommandGroups.modifying,
        CommandGroups.enriching,
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


def GTOGroupSection(section):
    return partial(GtoGroup, section=section)


app = Typer(
    cls=GtoGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
)

arg_name = Argument(..., help="Artifact name")
arg_version = Argument(..., help="Artifact version")
arg_stage = Argument(..., help="Stage to promote to")

option_rev = Option(None, "--rev", help="Repo revision to use", show_default=True)
option_repo = Option(".", "-r", "--repo", help="Repository to use", show_default=True)
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
option_all = Option(False, "--all", "-a", help="Return all versions sorted")
option_name = Option(None, "--name", "-n", help="Artifact name", show_default=True)
option_ascending = Option(
    False,
    "--ascending",
    "--asc",
    help="Show new first",
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
option_type_bool = Option(
    False, "--type", is_flag=True, help="Show type", show_default=True
)
option_path_bool = Option(
    False, "--path", is_flag=True, help="Show path", show_default=True
)
option_ref_bool = Option(
    False, "--ref", is_flag=True, help="Show ref", show_default=True
)
option_description_bool = Option(
    False, "--description", is_flag=True, help="Show description", show_default=True
)
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
option_registered_only = Option(
    False,
    "--registered-only",
    "--ro",
    is_flag=True,
    help="Show only registered versions",
)


@app.callback("gto", invoke_without_command=True, no_args_is_help=True)
def gto_callback(
    ctx: Context,
    show_version: bool = Option(False, "--version", help="Show version and exit"),
    verbose: bool = Option(False, "--verbose", "-v", help="Print debug messages"),
    traceback: bool = Option(False, "--traceback", "--tb", hidden=True),
):
    """\b
    Git Tag Ops. Turn your Git repository into an Artifact Registry:
    * Register new versions of artifacts marking releases/significant changes
    * Promote versions to ordered, named stages to track their lifecycles
    * GitOps: signal CI/CD automation or downstream systems to act upon these actions
    * Maintain and query artifact metadata / additional info with Enrichments machinery
    """
    if ctx.invoked_subcommand is None and show_version:
        with cli_echo():
            echo(f"{EMOJI_GTO} GTO Version: {gto.__version__}")
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
                raise typer.Exit(1) from e
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
                raise typer.Exit(1) from e
            finally:
                # TODO: analytics
                error  # pylint: disable=pointless-statement
                # send_cli_call(cmd_name, error_msg=error, **res)

        return inner

    return decorator


@gto_command(section=CommandGroups.enriching)
def annotate(
    repo: str = option_repo,
    name: str = arg_name,
    type: str = Option(None, help="Artifact type"),
    path: str = Option(None, help="Artifact path"),
    must_exist: bool = Option(
        False,
        "-e",
        "--must-exist",
        is_flag=True,
        help="Verify artifact is committed to Git",
    ),
    label: List[str] = Option(None, "--label", help="Labels to add to artifact"),
    description: str = Option("", "-d", "--description", help="Artifact description"),
    # update: bool = Option(
    #     False, "-u", "--update", is_flag=True, help="Update artifact if it exists"
    # ),
):
    """Update artifact metadata annotations

    Examples:
       $ gto enrich nn --type model --path models/neural_network.h5
    """
    gto.api.annotate(
        repo,
        name,
        type=type,
        path=path,
        must_exist=must_exist,
        labels=label,
        description=description,
        # update=update,
    )


@gto_command(section=CommandGroups.enriching)
def remove(repo: str = option_repo, name: str = arg_name):
    """Remove the enrichment for given artifact

    Examples:
         $ gto remove nn
    """
    gto.api.remove(repo, name)


@gto_command(section=CommandGroups.modifying)
def register(
    repo: str = option_repo,
    name: str = arg_name,
    ref: str = Argument("HEAD", help="Git reference to use for registration"),
    version: Optional[str] = Option(
        None, "--version", "--ver", help="Version name in SemVer format"
    ),
    message: Optional[str] = Option(
        None, "--message", "-m", help="Message to annotate git tag with"
    ),
    bump_major: bool = Option(
        False, "--bump-major", is_flag=True, help="Bump major version"
    ),
    bump_minor: bool = Option(
        False, "--bump-minor", is_flag=True, help="Bump minor version"
    ),
    bump_patch: bool = Option(
        False, "--bump-patch", is_flag=True, help="Bump patch version"
    ),
):
    """Create an artifact version to signify an important, published or released iteration

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
        message=message,
        bump_major=bump_major,
        bump_minor=bump_minor,
        bump_patch=bump_patch,
        stdout=True,
    )


@gto_command(section=CommandGroups.modifying)
def promote(
    repo: str = option_repo,
    name: str = arg_name,
    stage: str = arg_stage,
    ref: Optional[str] = Argument(None, help="Git reference to promote"),
    version: Optional[str] = Option(
        None,
        "--version",
        help="If you provide REF, this will be used to name new version",
    ),
    message: Optional[str] = Option(
        None, "--message", "-m", help="Message to annotate git tag with"
    ),
    simple: bool = Option(
        False,
        "--simple",
        is_flag=True,
        help="Use simple notation, e.g. rf#prod instead of rf#prod-5",
    ),
    force: bool = Option(
        False, help="Promote even if version is already in required Stage"
    ),
    skip_registration: bool = Option(
        False,
        "--sr",
        "--skip-registration",
        is_flag=True,
        help="Don't register a version at specified commit",
    ),
):
    """Move an artifact version to a specific stage

    Examples:
        Promote "nn" to "prod" at specific ref:
        $ gto promote nn prod abcd123

        Promote specific version:
        $ gto promote nn prod --version v1.0.0

        Promote at specific ref and name version explicitly:
        $ gto promote nn prod abcd123 --version v1.0.0

        Promote without increment
        $ gto promote nn prod --ref HEAD --simple
    """
    if ref is not None:
        name_version = version
        promote_version = None
    elif version is not None:
        name_version = None
        promote_version = version
    else:
        ref = "HEAD"
        name_version = None
        promote_version = None
    gto.api.promote(
        repo,
        name,
        stage,
        promote_version,
        ref,
        name_version,
        message=message,
        simple=simple,
        force=force,
        skip_registration=skip_registration,
        stdout=True,
    )


@gto_command(section=CommandGroups.querying)
def latest(
    repo: str = option_repo,
    name: str = arg_name,
    ref: bool = option_ref_bool,
):
    """Find the latest version of artifact

    Examples:
        $ gto latest nn
    """
    latest_version = gto.api.find_latest_version(repo, name)
    if latest_version:
        if ref:
            echo(latest_version.tag or latest_version.commit_hexsha)
        else:
            echo(latest_version.name)


@gto_command(section=CommandGroups.querying)
def which(
    repo: str = option_repo,
    name: str = arg_name,
    stage: str = arg_stage,
    ref: bool = option_ref_bool,
    all: bool = option_all,
    registered_only: bool = option_registered_only,
    ascending: bool = option_ascending,
):
    """Find the latest artifact version in a given stage

    Examples:
        $ gto which nn prod

        Print git tag that did the promotion:
        $ gto which nn prod --ref
    """
    version = gto.api.find_versions_in_stage(
        repo, name, stage, all=all, registered_only=registered_only
    )
    if version:
        if all:
            if ascending:
                version.reverse()
            format_echo([v.version for v in version], "lines")
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


@gto_command(section=CommandGroups.querying)
def check_ref(
    repo: str = option_repo,
    ref: str = Argument(..., help="Git reference to analyze"),
    json: bool = Option(False, "--json", is_flag=True, help="Output in JSON format"),
):
    """Find out the artifact version registered/promoted with ref

    Examples:
        $ gto check-ref rf@v1.0.0
        $ gto check-ref rf#prod
    """
    result = gto.api.check_ref(repo, ref)
    if json:
        format_echo(result, "json")
    else:
        if result["version"]:
            v = list(result["version"].values())[0]
            echo(
                f"""{EMOJI_OK} Version "{v["name"]}" of artifact "{v["artifact"]}" was registered"""
            )
        if result["stage"]:
            s = list(result["stage"].values())[0]
            echo(
                f"""{EMOJI_OK} Version "{s["version"]}" of artifact "{s["artifact"]}" was promoted to "{s["stage"]}" stage"""
            )


@gto_command(section=CommandGroups.querying)
def show(
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show registry"),
    all_branches: bool = option_all_branches,
    all_commits: bool = option_all_commits,
    json: bool = option_json,
    plain: bool = option_plain,
    name_only: bool = option_name_only,
    registered_only: bool = option_registered_only,
):
    """Show the registry state

    Examples:
        Show the registry:
        $ gto show

        Show versions of specific artifact in registry:
        $ gto show nn

        Use --all-branches and --all-commits to read more than just HEAD:
        $ gto show --all-branches
        $ gto show nn --all-commits
    """
    assert (
        sum(bool(i) for i in (json, plain, name_only)) <= 1
    ), "Only one output format allowed"
    if name_only or json:
        output = gto.api.show(
            repo,
            name=name,
            all_branches=all_branches,
            all_commits=all_commits,
            registered_only=registered_only,
            table=False,
        )
        if name_only:
            format_echo([v["name"] for v in output], "lines")
        else:
            format_echo(output, "json")
    else:
        format_echo(
            gto.api.show(
                repo,
                name=name,
                all_branches=all_branches,
                all_commits=all_commits,
                registered_only=registered_only,
                table=True,
                truncate_hexsha=True,
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


@gto_command(section=CommandGroups.querying)
def history(
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show all."),
    all_branches: bool = option_all_branches,
    all_commits: bool = option_all_commits,
    json: bool = option_json,
    plain: bool = option_plain,
    ascending: bool = option_ascending,
):
    """Show a journal of registry operations

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
                all_branches=all_branches,
                all_commits=all_commits,
                ascending=ascending,
                table=False,
            ),
            format="json",
        )
    else:
        format_echo(
            gto.api.history(
                repo,
                name,
                all_branches=all_branches,
                all_commits=all_commits,
                ascending=ascending,
                table=True,
                truncate_hexsha=True,
            ),
            format="table",
            format_table="plain" if plain else "fancy_outline",
            if_empty="Nothing found in the current workspace",
        )


@gto_command(section=CommandGroups.querying)
def stages(
    repo: str = option_repo,
    allowed: bool = Option(
        False,
        "--allowed",
        is_flag=True,
        help="Show allowed stages from config",
        show_default=True,
    ),
):
    """Print list of stages used in the registry

    Examples:
        $ gto stages
        $ gto stages --allowed
    """
    format_echo(gto.api.get_stages(repo, allowed=allowed), "lines")


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


@gto_command(section=CommandGroups.enriching)
def describe(
    repo: str = option_repo,
    name: str = arg_name,
    rev: str = option_rev,
    type: Optional[bool] = option_type_bool,
    path: Optional[bool] = option_path_bool,
    description: Optional[bool] = option_description_bool,
):
    """Display enrichments for an artifact

    Examples:
        $ gto describe nn --rev HEAD
        $ gto describe nn@v0.0.1
    """
    assert (
        sum(bool(i) for i in (type, path, description)) <= 1
    ), "Can output one key only"
    infos = gto.api.describe(repo=repo, name=name, rev=rev)
    if not infos:
        return
    d = infos[0].get_object().dict(exclude_defaults=True)
    if type:
        if "type" not in d:
            raise WrongArgs("No type in enrichment")
        echo(d["type"])
    elif path:
        if "path" not in d:
            raise WrongArgs("No path in enrichment")
        echo(d["path"])
    elif description:
        if "description" not in d:
            raise WrongArgs("No description in enrichment")
        echo(d["description"])
    else:
        format_echo(d, "json")


if __name__ == "__main__":
    app()
