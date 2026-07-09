import logging
from collections import defaultdict
from functools import partial, wraps
from gettext import gettext
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import click
from click import Abort, ClickException, Command, Context, HelpFormatter
from click.exceptions import Exit

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


class GtoFormatter(click.HelpFormatter):
    def write_heading(self, heading: str) -> None:
        super().write_heading(bold(heading))


class GtoArgument(click.Argument):
    """click.Argument with a help text, shown in the "Arguments" help section."""

    def __init__(self, *args, help: Optional[str] = None, **kwargs):
        self.help = help
        super().__init__(*args, **kwargs)


def gto_argument(*param_decls: str, **attrs: Any):
    attrs.setdefault("cls", GtoArgument)
    return click.argument(*param_decls, **attrs)


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

    def get_help(self, ctx: Context) -> str:
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.
        """
        formatter = GtoFormatter(
            width=ctx.terminal_width, max_width=ctx.max_content_width
        )
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip("\n")

    def format_options(self, ctx: Context, formatter: HelpFormatter) -> None:
        arguments = [
            (param.metavar or (param.name or "").upper(), param.help or "")
            for param in self.get_params(ctx)
            if isinstance(param, GtoArgument)
        ]
        if arguments:
            with formatter.section(gettext("Arguments")):
                formatter.write_dl(arguments)
        super().format_options(ctx, formatter)

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


class GtoCommand(GtoCliMixin, Command):
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


class GtoGroup(GtoCliMixin, click.Group):
    order = [
        CommandGroups.querying,
        CommandGroups.modifying,
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

    def list_commands(self, ctx: Context) -> List[str]:
        # keep the definition order instead of click's alphabetical sort
        return list(self.commands)

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


# General click arguments and options
arg_name = gto_argument("name", help="Artifact name")
option_stage = click.option("--stage", required=True, help="Stage to assign")
option_delete = click.option(
    "-d",
    "--delete",
    is_flag=True,
    help="Delete the git tag(s) instead of creating the new one",
)

# click options to control git-related operations
option_repo = click.option(
    "-r",
    "--repo",
    default=".",
    help="Local or remote repository",
    show_default=True,
)
option_message = click.option(
    "--message", "-m", help="Message to annotate the Git tag with"
)
option_force = click.option(
    "--force",
    is_flag=True,
    help="Create the Git tag even if it already exists and is in effect",
)


def callback_simple(  # pylint: disable=inconsistent-return-statements
    ctx: Context,
    param: click.Parameter,  # pylint: disable=unused-argument
    value: str,
):
    if ctx.resilient_parsing:
        return
    allowed_values = ["auto", "true", "false"]
    if value not in allowed_values:
        raise click.BadParameter(f"Only one of {allowed_values} is allowed")
    return {"auto": None, "true": True, "false": False}[value]


option_simple = click.option(
    "--simple",
    default="auto",
    help="Use simple notation, e.g. `rf#prod` instead of `rf#prod-5`"
    " [supported values: auto, true, false]",
    callback=callback_simple,
)


# click options to control and filter the output
def callback_sort(  # pylint: disable=inconsistent-return-statements
    ctx: Context,
    param: click.Parameter,  # pylint: disable=unused-argument
    value: str,
):
    if ctx.resilient_parsing:
        return
    allowed_values = ["timestamp", "semver"]
    if value not in allowed_values:
        raise click.BadParameter(f"Only one of {allowed_values} is allowed")
    return VersionSort.Timestamp if value == "timestamp" else VersionSort.SemVer


option_registered_only = click.option(
    "--ro",
    "--registered-only",
    "registered_only",
    is_flag=True,
    help="Show only registered versions",
)
option_deprecated = click.option(
    "-d",
    "--deprecated",
    is_flag=True,
    help="Include deprecated in output",
)
option_sort = click.option(
    "--sort",
    default="timestamp",
    help="Order assignments by timestamp or semver",
    callback=callback_sort,
)
option_assignments_per_version = click.option(
    "--av",
    "--assignments-per-version",
    "assignments_per_version",
    default=ASSIGNMENTS_PER_VERSION,
    help="Show N last stages for each version. -1 for all",
)
option_versions_per_stage = click.option(
    "--vs",
    "--versions-per-stage",
    "versions_per_stage",
    default=VERSIONS_PER_STAGE,
    help="Show N last versions for each stage. -1 for all. Applied after 'assignments-per-version'",
)

# click options to format the output
option_ascending = click.option(
    "--ascending",
    "--asc",
    "ascending",
    is_flag=True,
    help="Show new first",
    show_default=True,
)
option_show_name = click.option(
    "--name", "show_name", is_flag=True, help="Show artifact name"
)
option_show_version = click.option(
    "--version", "show_version", is_flag=True, help="Output artifact version"
)
option_show_event = click.option(
    "--event", "show_event", is_flag=True, help="Show event"
)
option_show_stage = click.option(
    "--stage", "show_stage", is_flag=True, help="Show artifact stage"
)
option_show_ref = click.option(
    "--ref", "show_ref", is_flag=True, help="Show ref", show_default=True
)
option_json = click.option(
    "--json",
    is_flag=True,
    help="Print output in json format",
    show_default=True,
)
option_plain = click.option(
    "--plain",
    is_flag=True,
    help="Print table in grep-able format",
    show_default=True,
)
option_push_tag = click.option(
    "--push",
    is_flag=True,
    help="Push created git tag to `origin` (ignored if `repo` option is a remote URL)",
)


@click.group(
    name="gto",
    cls=GtoGroup,
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--version", "show_version", is_flag=True, help="Show version and exit")
@click.option("--verbose", "-v", is_flag=True, help="Print debug messages")
@click.option("--traceback", "--tb", "traceback", is_flag=True, hidden=True)
@click.pass_context
def app(ctx: Context, show_version: bool, verbose: bool, traceback: bool):
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
                    echo(EMOJI_FAIL + color(str(e), col="red"))
                raise Exit(1) from e
            except Exception as e:  # pylint: disable=broad-except
                error = str(type(e))
                if ctx.obj["traceback"]:
                    raise
                with stderr_echo():
                    echo(EMOJI_FAIL + color(f"Unexpected error: {str(e)}", col="red"))
                    echo(
                        "Please report it here running with '--traceback' flag: <https://github.com/iterative/gto/issues>"
                    )
                raise Exit(1) from e
            finally:
                # TODO: analytics
                error  # pylint: disable=pointless-statement  # noqa: B018
                # send_cli_call(cmd_name, error_msg=error, **res)

        return inner

    return decorator


@gto_command(section=CommandGroups.modifying)
@option_repo
@arg_name
@gto_argument("ref", default="HEAD", help="Git reference to use for registration")
@click.option("--version", "--ver", help="Version name in SemVer format")
@option_message
@option_simple
@option_force
@click.option("--bump-major", is_flag=True, help="Bump major version")
@click.option("--bump-minor", is_flag=True, help="Bump minor version")
@click.option("--bump-patch", is_flag=True, help="Bump patch version")
@option_push_tag
def register(
    repo: str,
    name: str,
    ref: str,
    version: Optional[str],
    message: Optional[str],
    simple: Optional[bool],
    force: bool,
    bump_major: bool,
    bump_minor: bool,
    bump_patch: bool,
    push: bool,
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
        simple=simple,
        force=force,
        bump_major=bump_major,
        bump_minor=bump_minor,
        bump_patch=bump_patch,
        push=push,
        stdout=True,
    )


@gto_command(section=CommandGroups.modifying, aliases=["promote"])
@option_repo
@arg_name
@gto_argument("ref", required=False, help="Git reference to use")
@click.option(
    "--version",
    help="If you provide REF, this will be used to name new version",
)
@option_stage
@option_message
@option_simple
@option_force
@option_push_tag
@click.option(
    "--sr",
    "--skip-registration",
    "skip_registration",
    is_flag=True,
    help="Don't register a version at specified commit",
)
def assign(
    repo: str,
    name: str,
    ref: Optional[str],
    version: Optional[str],
    stage: str,
    message: Optional[str],
    simple: Optional[bool],
    force: bool,
    push: bool,
    skip_registration: bool,
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
        simple=simple,
        force=force,
        push=push,
        skip_registration=skip_registration,
        stdout=True,
    )


@gto_command(section=CommandGroups.modifying)
@option_repo
@arg_name
@gto_argument("version", required=False, help="Artifact version")
@gto_argument("stage", required=False, help="Stage to unassign")
@click.option("--ref", help="Git reference to use (for model deprecation)")
@option_message
@option_simple
@option_force
@option_delete
@option_push_tag
def deprecate(
    repo: str,
    name: str,
    version: Optional[str],
    stage: Optional[str],
    ref: Optional[str],
    message: Optional[str],
    simple: Optional[bool],
    force: bool,
    delete: bool,
    push: bool,
):
    """Deprecate artifact, deregister a version, or unassign a stage."""
    if stage:
        gto.api.unassign(
            repo=repo,
            name=name,
            version=version,
            stage=stage,
            message=message,
            simple=simple,
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
            simple=simple,
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
            simple=simple,
            force=force,
            delete=delete,
            push=push,
            stdout=True,
        )


@gto_command(hidden=True)
@arg_name
@click.option("--key", help="Which key to return")
def parse_tag(
    name: str,
    key: Optional[str],
):
    """Given git tag name created by this tool, parse it and return it's
    parts."""
    parsed = gto.api.parse_tag(name)
    if key:
        parsed = parsed[key]
    format_echo(parsed, "json")


@gto_command(section=CommandGroups.querying)
@option_repo
@gto_argument("ref", help="Git reference to analyze")
@option_json
@option_show_name
@option_show_version
@option_show_event
@option_show_stage
def check_ref(
    repo: str,
    ref: str,
    json: bool,
    show_name: bool,
    show_version: bool,
    show_event: bool,
    show_stage: bool,
):
    """Find out the artifact version registered/assigned with ref."""
    assert (
        sum(bool(i) for i in (json, show_event, show_name, show_version, show_stage))
        <= 1
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
    elif show_name:
        format_echo(found_event.artifact, "line")
    elif show_version:
        if hasattr(found_event, "version"):
            format_echo(found_event.version, "line")
    elif show_stage:
        if hasattr(found_event, "stage"):
            format_echo(found_event.stage, "line")
    elif show_event:
        format_echo(found_event.event, "line")
    else:
        echo(f"{EMOJI_OK} {found_event}")


@gto_command(section=CommandGroups.querying)
@option_repo
@gto_argument(
    "name", required=False, help="Artifact name to show. If empty, show registry"
)
@option_json
@option_plain
@option_show_name
@option_show_version
@option_show_stage
@option_show_ref
@option_registered_only
@option_deprecated
@option_assignments_per_version
@option_versions_per_stage
@option_sort
def show(  # pylint: disable=too-many-locals
    repo: str,
    name: Optional[str],
    json: bool,
    plain: bool,
    show_name: bool,
    show_version: bool,
    show_stage: bool,
    show_ref: bool,
    registered_only: bool,
    deprecated: bool,
    assignments_per_version: int,
    versions_per_stage: int,
    sort: VersionSort,
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
            if not output[0]:
                return
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
@option_repo
@gto_argument("name", required=False, help="Artifact name to show. If empty, show all.")
@option_json
@option_plain
@option_ascending
def history(
    repo: str,
    name: Optional[str],
    json: bool,
    plain: bool,
    ascending: bool,
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
@option_repo
@click.option(
    "--allowed",
    is_flag=True,
    help="Show allowed stages from config",
    show_default=True,
)
@click.option(
    "--used",
    is_flag=True,
    help="Show stages that were ever used (from all git tags)",
    show_default=True,
)
@option_json
def stages(
    repo: str,
    allowed: bool,
    used: bool,
    json: bool,
):
    """Print list of stages used in the registry."""
    result = gto.api.get_stages(repo, allowed=allowed, used=used)
    if json:
        format_echo(result, "json")
    else:
        format_echo(result, "lines")


@gto_command(hidden=True)
@option_repo
def print_state(repo: str):
    """Technical cmd: Print current registry state."""
    state = make_ready_to_serialize(
        gto.api._get_state(repo).model_dump()  # pylint: disable=protected-access
    )
    format_echo(state, "json")


@gto_command(section=CommandGroups.querying)
@option_repo
def doctor(
    repo: str,
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
    app()  # pylint: disable=no-value-for-parameter
