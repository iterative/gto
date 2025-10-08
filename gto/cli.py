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
from gto.constants import (
    ASSIGNMENTS_PER_VERSION,
    VERSIONS_PER_STAGE,
    VersionSort,
)
from gto.exceptions import (
    GTOException,
    NotImplementedInGTO,
    WrongArgs,
    WrongConfig,
)
from gto.ui import (
    EMOJI_FAIL,
    EMOJI_GTO,
    EMOJI_OK,
    bold,
    cli_echo,
    color,
    echo,
    stderr_echo,
)
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
        aliases: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
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


class GtoCommand(GtoCliMixin, TyperCommand):
    def __init__(
        self,
        name: Optional[str],
        section: str = "other",
        aliases: Optional[List[str]] = None,
        help: Optional[str] = None,
        **kwargs,
    ):
        examples, help = _extract_examples(help)
        super().__init__(
            name=name,
            section=section,
            aliases=aliases,
            examples=examples,
            help=help,
            **kwargs,
        )


class GtoGroup(GtoCliMixin, TyperGroup):
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
        aliases: Optional[List[str]] = None,
        help: Optional[str] = None,
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

    # The typer overrides this with some trick dependent on environment,
    # use click method for taking affect of Self.format_commands
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        # pylint: disable=bad-super-call
        super(TyperGroup, self).format_help(ctx, formatter)

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

# General Typer arguments and options
arg_name = Argument(..., help="Artifact name")
arg_version = Argument(..., help="Artifact version")
arg_stage = Argument(..., help="Stage to assign")
option_version = Option(None, "--version", help="Version to register")
option_stage = Option(..., "--stage", help="Stage to assign")
option_to_version = Option(
    None, "--to-version", help="Version to use for stage assignment"
)
option_delete = Option(
    False,
    "-d",
    "--delete",
    is_flag=True,
    help="Delete the git tag(s) instead of creating the new one",
)

# Typer options to control git-related operations
option_rev = Option(None, "--rev", help="Repo revision to use", show_default=True)
option_repo = Option(
    ".",
    "-r",
    "--repo",
    help="Local or remote repository",
    show_default=True,
)
option_message = Option(
    None, "--message", "-m", help="Message to annotate the Git tag with"
)
option_force = Option(
    False,
    "--force",
    is_flag=True,
    help="Create the Git tag even if it already exists and is in effect",
)


def callback_simple(  # pylint: disable=inconsistent-return-statements
    ctx: typer.Context,
    param: typer.CallbackParam,  # pylint: disable=unused-argument
    value: str,
):
    if ctx.resilient_parsing:
        return
    allowed_values = ["auto", "true", "false"]
    if value not in allowed_values:
        raise typer.BadParameter(f"Only one of {allowed_values} is allowed")
    return {"auto": None, "true": True, "false": False}[value]


option_simple = Option(
    "auto",
    "--simple",
    help="Use simple notation, e.g. `rf#prod` instead of `rf#prod-5`"
    " [supported values: auto, true, false]",
    callback=callback_simple,
)


# Typer options to control and filter the output
def callback_sort(  # pylint: disable=inconsistent-return-statements
    ctx: typer.Context,
    param: typer.CallbackParam,  # pylint: disable=unused-argument
    value: str,
):
    if ctx.resilient_parsing:
        return
    allowed_values = ["timestamp", "semver"]
    if value not in allowed_values:
        raise typer.BadParameter(f"Only one of {allowed_values} is allowed")
    return VersionSort.Timestamp if value == "timestamp" else VersionSort.SemVer


option_all = Option(False, "--all", "-a", help="Return all versions sorted")
option_registered_only = Option(
    False,
    "--ro",
    "--registered-only",
    is_flag=True,
    help="Show only registered versions",
)
option_deprecated = Option(
    False,
    "-d",
    "--deprecated",
    is_flag=True,
    help="Include deprecated in output",
)
option_expected = Option(
    False,
    "-e",
    "--expected",
    is_flag=True,
    help="Return exit code 1 if no result",
    show_default=True,
)
option_sort = Option(
    "timestamp",
    "--sort",
    help="Order assignments by timestamp or semver",
    callback=callback_sort,
)
option_assignments_per_version = Option(
    ASSIGNMENTS_PER_VERSION,
    "--av",
    "--assignments-per-version",
    help="Show N last stages for each version. -1 for all",
)
option_versions_per_stage = Option(
    VERSIONS_PER_STAGE,
    "--vs",
    "--versions-per-stage",
    help="Show N last versions for each stage. -1 for all. Applied after 'assignments-per-version'",
)

# Typer options to format the output
option_ascending = Option(
    False,
    "--ascending",
    "--asc",
    help="Show new first",
    show_default=True,
)
option_show_name = Option(False, "--name", is_flag=True, help="Show artifact name")
option_show_version = Option(
    False, "--version", is_flag=True, help="Output artifact version"
)
option_show_event = Option(False, "--event", is_flag=True, help="Show event")
option_show_stage = Option(False, "--stage", is_flag=True, help="Show artifact stage")
option_show_type = Option(
    False, "--type", is_flag=True, help="Show type", show_default=True
)
option_show_path = Option(
    False, "--path", is_flag=True, help="Show path", show_default=True
)
option_show_ref = Option(
    False, "--ref", is_flag=True, help="Show ref", show_default=True
)
option_show_description = Option(
    False, "--description", is_flag=True, help="Show description", show_default=True
)
option_show_custom = Option(
    False, "--custom", is_flag=True, help="Show custom metadata", show_default=True
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
option_table = Option(
    False,
    "--table",
    is_flag=True,
    help="Print output in table format",
    show_default=True,
)
option_push_tag = Option(
    False,
    "--push",
    is_flag=True,
    help="Push created git tag to `origin` (ignored if `repo` option is a remote URL)",
)
option_commit = Option(
    False,
    "--commit",
    is_flag=True,
    help="Automatically commit changes due to this command (experimental)",
)
option_push_commit = Option(
    False,
    "--push",
    is_flag=True,
    help="Push created commit automatically (experimental) - will set commit=True",
)
option_branch = Option(
    None, "-b", "--branch", help="Branch to commit to. Only for remote repos."
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def gto_callback(
    ctx: Context,
    show_version: bool = Option(False, "--version", help="Show version and exit"),
    verbose: bool = Option(False, "--verbose", "-v", help="Print debug messages"),
    traceback: bool = Option(False, "--traceback", "--tb", hidden=True),
):
    """\b
    Git Tag Ops. Turn your Git repository into an Artifact Registry:
    * Registry: Track new artifacts and their versions for releases and significant
    changes.
    * Lifecycle Management: Create actionable stages for versions marking status of
    artifact or it's readiness to be consumed by a specific environment.
    * GitOps: Signal CI/CD automation or other downstream systems to act upon these
    new versions and lifecycle updates.
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
                with stderr_echo():
                    echo(EMOJI_FAIL + color(str(e), col=typer.colors.RED))
                raise typer.Exit(1) from e
            except Exception as e:  # pylint: disable=broad-except
                error = str(type(e))
                if ctx.obj["traceback"]:
                    raise
                with stderr_echo():
                    echo(
                        (
                            EMOJI_FAIL
                            + color(f"Unexpected error: {str(e)}", col=typer.colors.RED)
                        )
                    )
                    echo(
                        "Please report it here running with '--traceback' flag: <https://github.com/iterative/gto/issues>"
                    )
                raise typer.Exit(1) from e
            finally:
                # TODO: analytics
                error  # pylint: disable=pointless-statement  # noqa: B018
                # send_cli_call(cmd_name, error_msg=error, **res)

        return inner

    return decorator


@gto_command(section=CommandGroups.modifying)
def register(
    repo: str = option_repo,
    name: str = arg_name,
    ref: str = Argument("HEAD", help="Git reference to use for registration"),
    version: Optional[str] = Option(
        None, "--version", "--ver", help="Version name in SemVer format"
    ),
    message: Optional[str] = option_message,
    simple: str = option_simple,
    force: bool = option_force,
    bump_major: bool = Option(
        False, "--bump-major", is_flag=True, help="Bump major version"
    ),
    bump_minor: bool = Option(
        False, "--bump-minor", is_flag=True, help="Bump minor version"
    ),
    bump_patch: bool = Option(
        False, "--bump-patch", is_flag=True, help="Bump patch version"
    ),
    push: bool = option_push_tag,
):
    """Create an artifact version to signify an important, published
    or released iteration.
    """
    gto.api.register(
        repo=repo,
        name=name,
        ref=ref or "HEAD",
        version=version,
        message=message,
        simple=simple,  # type: ignore
        force=force,
        bump_major=bump_major,
        bump_minor=bump_minor,
        bump_patch=bump_patch,
        push=push,
        stdout=True,
    )


@gto_command(section=CommandGroups.modifying, aliases=["promote"])
def assign(
    repo: str = option_repo,
    name: str = arg_name,
    ref: Optional[str] = Argument(None, help="Git reference to use"),
    version: Optional[str] = Option(
        None,
        "--version",
        help="If you provide REF, this will be used to name new version",
    ),
    stage: str = option_stage,
    message: Optional[str] = option_message,
    simple: str = option_simple,
    force: bool = option_force,
    push: bool = option_push_tag,
    skip_registration: bool = Option(
        False,
        "--sr",
        "--skip-registration",
        is_flag=True,
        help="Don't register a version at specified commit",
    ),
):
    """Assign stage to specific artifact version."""
    if ref is not None:
        name_version = version
        version = None
    elif version is not None:
        name_version = None
    else:
        ref = "HEAD"
        name_version = None
        version = None
    gto.api.assign(
        repo,
        name,
        stage,
        version,
        ref,
        name_version,
        message=message,
        simple=simple,  # type: ignore
        force=force,
        push=push,
        skip_registration=skip_registration,
        stdout=True,
    )


@gto_command(section=CommandGroups.modifying)
def deprecate(
    repo: str = option_repo,
    name: str = arg_name,
    version: str = Argument(None, help="Artifact version"),
    stage: str = Argument(None, help="Stage to unassign"),
    ref: Optional[str] = Option(
        None, "--ref", help="Git reference to use (for model deprecation)"
    ),
    message: Optional[str] = option_message,
    simple: str = option_simple,
    force: bool = option_force,
    delete: bool = option_delete,
    push: bool = option_push_tag,
):
    """Deprecate artifact, deregister a version, or unassign a stage."""
    if stage:
        gto.api.unassign(
            repo=repo,
            name=name,
            version=version,
            stage=stage,
            message=message,
            simple=simple,  # type: ignore
            force=force,
            delete=delete,
            push=push,
            stdout=True,
        )
    elif version:
        gto.api.deregister(
            repo=repo,
            name=name,
            version=version,
            message=message,
            simple=simple,  # type: ignore
            force=force,
            delete=delete,
            push=push,
            stdout=True,
        )
    else:
        gto.api.deprecate(
            repo=repo,
            name=name,
            ref=ref,
            message=message,
            simple=simple,  # type: ignore
            force=force,
            delete=delete,
            push=push,
            stdout=True,
        )


@gto_command(hidden=True)
def parse_tag(
    name: str = arg_name,
    key: Optional[str] = Option(None, "--key", help="Which key to return"),
):
    """Given git tag name created by this tool, parse it and return it's
    parts."""
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, "json")


@gto_command(section=CommandGroups.querying)
def check_ref(
    repo: str = option_repo,
    ref: str = Argument(..., help="Git reference to analyze"),
    json: bool = option_json,
    name: bool = option_show_name,
    version: bool = option_show_version,
    event: bool = option_show_event,
    stage: bool = option_show_stage,
):
    """Find out the artifact version registered/assigned with ref."""
    assert (
        sum(bool(i) for i in (json, event, name, version, stage)) <= 1
    ), "Only one output formatting flags is allowed"
    result = gto.api.check_ref(repo, ref)
    if len(result) > 1:
        raise NotImplementedInGTO(
            "Checking refs that created 1+ events is not supported"
        )
    if len(result) == 0:
        return
    found_event = result[0]
    if json:
        format_echo(found_event.dict_state(exclude={"priority", "addition"}), "json")
    elif name:
        format_echo(found_event.artifact, "line")
    elif version:
        if hasattr(found_event, "version"):
            format_echo(found_event.version, "line")
    elif stage:
        if hasattr(found_event, "stage"):
            format_echo(found_event.stage, "line")
    elif event:
        format_echo(found_event.event, "line")
    else:
        echo(f"{EMOJI_OK} {found_event}")


@gto_command(section=CommandGroups.querying)
def show(  # pylint: disable=too-many-locals
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show registry"),
    json: bool = option_json,
    plain: bool = option_plain,
    show_name: bool = option_show_name,
    show_version: bool = option_show_version,
    show_stage: bool = option_show_stage,
    show_ref: bool = option_show_ref,
    registered_only: bool = option_registered_only,
    deprecated: bool = option_deprecated,
    assignments_per_version: int = option_assignments_per_version,
    versions_per_stage: int = option_versions_per_stage,
    sort: str = option_sort,
):
    """Show the registry state, highest version, or what's assigned in stage."""
    show_options = [show_name, show_version, show_stage, show_ref]
    assert (
        sum(bool(i) for i in [json, plain] + show_options) <= 1
    ), "Only one output format allowed"
    if json:
        output = gto.api.show(
            repo,
            name=name,
            registered_only=registered_only,
            deprecated=deprecated,
            assignments_per_version=assignments_per_version,
            versions_per_stage=versions_per_stage,
            sort=sort,
            table=False,
        )
        format_echo(output, "json")
    else:
        output = gto.api.show(
            repo,
            name=name,
            registered_only=registered_only,
            deprecated=deprecated,
            assignments_per_version=assignments_per_version,
            versions_per_stage=versions_per_stage,
            sort=sort,
            table=True,
            truncate_hexsha=True,
        )
        arg = None
        arg = "name" if show_name else arg
        arg = "version" if show_version else arg
        arg = "stage" if show_stage else arg
        arg = "ref" if show_ref else arg
        if arg:
            if arg not in output[0][0]:
                raise WrongArgs(f"Cannot apply --{arg}")
            format_echo(
                [v[arg] if isinstance(v, dict) else v for v in output[0]], "lines"
            )
        else:
            format_echo(
                output,
                format="table",
                format_table="plain" if plain else "fancy_outline",
                if_empty="Nothing found in the current workspace",
            )


@gto_command(section=CommandGroups.querying)
def history(
    repo: str = option_repo,
    name: str = Argument(None, help="Artifact name to show. If empty, show all."),
    json: bool = option_json,
    plain: bool = option_plain,
    ascending: bool = option_ascending,
):
    """Show a journal of registry operations."""
    assert sum(bool(i) for i in (json, plain)) <= 1, "Only one output format allowed"
    if json:
        format_echo(
            gto.api.history(
                repo,
                name,
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
    used: bool = Option(
        False,
        "--used",
        is_flag=True,
        help="Show stages that were ever used (from all git tags)",
        show_default=True,
    ),
    json: bool = option_json,
):
    """Print list of stages used in the registry."""
    result = gto.api.get_stages(repo, allowed=allowed, used=used)
    if json:
        format_echo(result, "json")
    else:
        format_echo(result, "lines")


@gto_command(hidden=True)
def print_state(repo: str = option_repo):
    """Technical cmd: Print current registry state."""
    state = make_ready_to_serialize(
        gto.api._get_state(repo).model_dump()  # pylint: disable=protected-access
    )
    format_echo(state, "json")


@gto_command(section=CommandGroups.querying)
def doctor(
    repo: str = option_repo,
):
    """Display GTO version and check the registry for problems."""
    with cli_echo():
        echo(f"{EMOJI_GTO} GTO Version: {gto.__version__}")
        echo("---------------------------------")
        try:
            from gto.config import (  # pylint: disable=import-outside-toplevel
                CONFIG,
            )

            echo(CONFIG.__repr_str__("\n"))
        except WrongConfig:
            echo(f"{EMOJI_FAIL} Fail to parse config")
        echo("---------------------------------")

    gto.api._get_state(repo).model_dump()  # pylint: disable=protected-access
    with cli_echo():
        echo(f"{EMOJI_OK} No issues found")


if __name__ == "__main__":
    app()
