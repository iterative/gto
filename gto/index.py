import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import (
    IO,
    Any,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from ruamel.yaml import YAMLError
from scmrepo.exceptions import SCMError
from scmrepo.git import Git
from scmrepo.git.objects import GitCommit

from gto.base import BaseManager, BaseRegistryState
from gto.base import Commit as EnrichmentEvent
from gto.commit_message_generator import (
    generate_annotate_commit_message,
    generate_remove_commit_message,
)
from gto.config import (
    CONFIG_FILE_NAME,
    RegistryConfig,
    assert_name_is_valid,
    read_registry_config,
    yaml,
)
from gto.constants import Action
from gto.exceptions import (
    ArtifactExists,
    ArtifactNotFound,
    NoFile,
    PathIsUsed,
    WrongArgs,
    WrongArtifactsYaml,
)
from gto.ext import EnrichmentInfo, EnrichmentReader
from gto.git_utils import RemoteRepoMixin
from gto.ui import echo

logger = logging.getLogger("gto")


class Artifact(BaseModel):
    type: Optional[str] = None
    path: Optional[str] = None
    virtual: bool = True
    labels: List[str] = []  # TODO: allow key:value labels
    description: str = ""
    custom: Any = None


State = Dict[str, Artifact]
state_adapter = TypeAdapter(State)


def not_frozen(func):
    @wraps(func)
    def inner(self: "Index", *args, **kwargs):
        if self.frozen:
            raise ValueError(f"Cannot {func.__name__}: {self.__class__} is frozen")
        return func(self, *args, **kwargs)

    return inner


def find_repeated_path(
    path: Union[str, Path], paths: Iterable[Union[str, Path]]
) -> Optional[Path]:
    """Return the path from "paths" that conflicts with "path":
    is equal to it or is a subpath (in both directions).
    """
    path = Path(path).resolve()
    for p in paths:
        if p:
            p = Path(p).resolve()
            if p == path or p in path.parents or path in p.parents:
                return p
    return None


def check_if_path_exists(
    path: Union[str, Path], scm: Optional[Git] = None, ref: Optional[str] = None
):
    """Check if path was committed to repo
    or it just exists in case the repo is not provided.
    """
    if scm is None:
        return Path(path).exists()
    try:
        fs = scm.get_fs(ref)  # type: ignore[arg-type]
        return fs.exists(str(path))
    except SCMError:
        return False


class Index(BaseModel):
    state: State = {}  # TODO should not be populated until load() is called
    frozen: bool = False

    @field_validator("state")
    @classmethod
    def state_is_valid(cls, v):  # pylint: disable=no-self-argument, no-self-use
        for name, artifact in v.items():
            assert_name_is_valid(name)
            if artifact.type:
                assert_name_is_valid(artifact.type)
            for label in artifact.labels:
                assert_name_is_valid(label)
        return v

    def __contains__(self, item):
        return item in self.state

    @classmethod
    def read(cls, path_or_file: Union[str, IO], frozen: bool = False):
        index = cls(frozen=frozen)
        index.state = index.read_state(path_or_file)
        return index

    @staticmethod
    def read_state(path_or_file: Union[str, IO]):
        def read_yaml(stream: IO):
            try:
                return yaml.load(stream)
            except YAMLError as e:
                raise WrongArtifactsYaml() from e

        # read contents of the yaml
        if isinstance(path_or_file, str):
            try:
                with open(path_or_file, "r", encoding="utf8") as file:
                    contents = read_yaml(file)
            except FileNotFoundError as e:
                raise NoFile("artifacts.yaml") from e
        else:
            contents = read_yaml(path_or_file)
        # check yaml contents is a valid State

        try:
            state = state_adapter.validate_python(contents)
        except ValidationError as e:
            raise WrongArtifactsYaml() from e
        # validate that specific names conform to the naming convention
        for key in state:
            assert_name_is_valid(key)
        return state

    def write_state(self, path_or_file: Union[str, IO]):
        if isinstance(path_or_file, str):
            with open(path_or_file, "w", encoding="utf8") as file:
                state = self.model_dump(exclude_defaults=True).get("state", {})
                yaml.dump(state, file)

    @not_frozen
    def add(
        self,
        name,
        type,
        path,
        must_exist,
        allow_same_path,
        labels,
        description,
        custom,
        update,
    ) -> Artifact:
        if name in self and not update:
            raise ArtifactExists(name)
        if (
            path
            and not allow_same_path
            and find_repeated_path(
                path, [a.path for n, a in self.state.items() if n != name]
            )
            is not None
        ):
            raise PathIsUsed(type=type, name=name, path=path)
        if update and name in self.state:
            self.state[name].type = type or self.state[name].type
            self.state[name].path = path or self.state[name].path
            if must_exist:
                self.state[name].virtual = False
            elif path:
                self.state[name].virtual = True
            self.state[name].labels = sorted(set(self.state[name].labels).union(labels))
            self.state[name].description = description or self.state[name].description
            self.state[name].custom = custom or self.state[name].custom
        else:
            self.state[name] = Artifact(
                type=type,
                path=path,
                virtual=not must_exist,
                labels=labels,
                description=description,
                custom=custom,
            )
        self.state_is_valid(self.state)  # type: ignore[call-arg]
        return self.state[name]

    @not_frozen
    def remove(self, name):
        if name not in self:
            raise ArtifactNotFound(name)
        del self.state[name]


class BaseIndexManager(BaseModel, ABC):
    current: Optional[Index] = None
    config: RegistryConfig

    @abstractmethod
    def get_index(self) -> Index:
        raise NotImplementedError

    @abstractmethod
    def update(self):
        raise NotImplementedError

    @abstractmethod
    def get_history(self) -> Dict[str, Index]:
        raise NotImplementedError

    def add(
        self,
        name,
        type,
        path,
        must_exist,
        allow_same_path,
        labels,
        description,
        custom,
        update,
        stdout=False,
    ):
        for arg in [name] + list(labels or []):
            assert_name_is_valid(arg)
        if type:
            self.config.assert_type(type)
        if must_exist:
            if not path:
                raise WrongArgs("`path` is required when `must_exist` is set to True")
            if not check_if_path_exists(
                path, self.scm if hasattr(self, "scm") else None
            ):
                raise NoFile(path)
        index = self.get_index()
        index.add(
            name,
            type=type,
            path=path,
            must_exist=must_exist,
            allow_same_path=allow_same_path,
            labels=labels or [],
            description=description,
            custom=custom,
            update=update,
        )
        self.update()
        if stdout:
            echo("Updated `artifacts.yaml`")

    def remove(self, name, stdout=False):
        index = self.get_index()
        index.remove(name)
        self.update()
        if stdout:
            echo("Updated `artifacts.yaml`")


class FileIndexManager(BaseIndexManager):
    path: str = ""

    @classmethod
    def from_path(cls, path: str, config: Optional[RegistryConfig] = None):
        if config is None:
            config = read_registry_config(os.path.join(path, CONFIG_FILE_NAME))
        return cls(path=path, config=config)  # type: ignore[call-arg]

    def index_path(self):
        return str(Path(self.path) / self.config.INDEX)

    def get_index(self) -> Index:
        if os.path.exists(self.index_path()):
            self.current = Index.read(self.index_path())
        if not self.current:
            self.current = Index()
        return self.current

    def update(self):
        if self.current is not None:
            self.current.write_state(self.index_path())

    def get_history(self) -> Dict[str, Index]:
        raise NotImplementedError("Not a git repo: history is not available")

    def get_commit_index(self, **kwargs) -> Index:
        raise NotImplementedError("Not a git repo: using revision is not available")

    def artifact_centric_representation(self):
        raise NotImplementedError("Not a git repo")


ArtifactCommits = Dict[str, Artifact]
ArtifactsCommits = Dict[str, ArtifactCommits]


class RepoIndexManager(FileIndexManager, RemoteRepoMixin):
    scm: Git
    cloned: bool

    def __init__(self, scm: Git, cloned: bool, config):
        super().__init__(scm=scm, cloned=cloned, config=config, current=None)  # type: ignore[call-arg]

    @classmethod
    @contextmanager
    def from_scm(
        cls,
        scm: Git,
        cloned: bool = False,
        config: Optional[RegistryConfig] = None,
    ):
        if config is None:
            config = read_registry_config(os.path.join(scm.root_dir, CONFIG_FILE_NAME))
        yield cls(scm=scm, cloned=cloned, config=config)

    def add(
        self,
        name,
        type,
        path,
        must_exist,
        allow_same_path,
        labels,
        description,
        custom,
        update,
        stdout=False,
        commit=False,
        commit_message=None,
        push=False,
    ):
        return self._call_commit_push(
            super().add,
            commit=commit,
            commit_message=commit_message
            or generate_annotate_commit_message(name=name, type=type, path=path),
            push=push or self.cloned,
            stdout=stdout,
            name=name,
            type=type,
            path=path,
            must_exist=must_exist,
            allow_same_path=allow_same_path,
            labels=labels,
            description=description,
            custom=custom,
            update=update,
        )

    def remove(
        self,
        name,
        stdout=False,
        commit=False,
        commit_message=None,
        push=False,
    ):
        return self._call_commit_push(
            super().remove,
            commit=commit,
            commit_message=commit_message or generate_remove_commit_message(name=name),
            push=push,
            stdout=stdout,
            name=name,
        )

    def index_path(self):
        # TODO: config should be loaded from repo too
        return os.path.join(self.scm.root_dir, self.config.INDEX)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_commit_index(  # type: ignore # pylint: disable=arguments-differ
        self,
        rev: Union[str, GitCommit],
        allow_to_not_exist: bool = True,
        ignore_corrupted: bool = False,
    ) -> Optional[Index]:
        rev = rev.hexsha if isinstance(rev, GitCommit) else self.scm.resolve_rev(rev)
        return self._get_commit_index(
            rev,
            allow_to_not_exist=allow_to_not_exist,
            ignore_corrupted=ignore_corrupted,
        )

    def _get_commit_index(  # type: ignore # pylint: disable=arguments-differ
        self,
        rev: str,
        allow_to_not_exist: bool = True,
        ignore_corrupted: bool = False,
    ) -> Optional[Index]:
        fs = self.scm.get_fs(rev)
        try:
            with fs.open(self.config.INDEX) as f:
                try:
                    return Index.read(f, frozen=True)
                except WrongArtifactsYaml as e:
                    logger.warning("Corrupted artifacts.yaml file in commit %s", rev)
                    if ignore_corrupted:
                        return None
                    raise e
        except FileNotFoundError:
            if allow_to_not_exist:
                return None
        raise ValueError(f"No Index exists at {rev}")

    def get_history(self) -> Dict[str, Index]:
        revs = {
            rev
            for branch in self.scm.iter_refs("refs/heads/")
            for rev in self.scm.branch_revs(branch)
        }
        history = {}
        for rev in revs:
            try:
                index = self._get_commit_index(rev)
                if index is not None:
                    history[rev] = index
            except ValueError:
                pass
        return history

    def artifact_centric_representation(self) -> ArtifactsCommits:
        representation = defaultdict(dict)  # type: ArtifactsCommits
        for commit, index in self.get_history().items():
            for art in index.state:
                representation[art][commit] = index.state[art]
        return representation

    def check_existence(self, name, commit):
        return name in self.get_commit_index(commit)

    def assert_existence(self, name, commit):
        if not self.check_existence(name, commit):
            raise ArtifactNotFound(name)


class EnrichmentManager(BaseManager, RemoteRepoMixin):
    actions: FrozenSet[Action] = frozenset()

    @classmethod
    @contextmanager
    def from_scm(
        cls,
        scm: Git,
        cloned: Optional[bool] = False,
        config: Optional[RegistryConfig] = None,
    ):
        if config is None:
            config = read_registry_config(os.path.join(scm.root_dir, CONFIG_FILE_NAME))
        yield cls(scm=scm, config=config)

    def describe(self, name: str, rev: Optional[str] = None) -> List[EnrichmentInfo]:
        enrichments = self.config.enrichments_
        res = []
        gto_enrichment = enrichments.pop("gto")
        gto_info = gto_enrichment.describe(self.scm, name, rev)
        if gto_info:
            res.append(gto_info)
            path = gto_info.get_path()  # type: ignore
            for enrichment in enrichments.values():
                enrichment_data = enrichment.describe(self.scm, path, rev)
                if enrichment_data is not None:
                    res.append(enrichment_data)
        return res

    def get_commits(self, all_branches=False, all_commits=False) -> Iterator[GitCommit]:
        revs: Set[str] = set()
        if all_commits or all_branches:
            branches = list(self.scm.iter_refs("refs/heads/"))
            if all_commits:
                revs.update(
                    rev for branch in branches for rev in self.scm.branch_revs(branch)
                )
            elif all_branches:
                revs.update(self.scm.resolve_rev(branch) for branch in branches)
        else:
            try:
                revs.add(self.scm.get_rev())
            except SCMError:
                pass  # empty git repo
        yield from (self.scm.resolve_commit(rev) for rev in revs)

    def update_state(
        self,
        state: BaseRegistryState,
        all_branches=False,
        all_commits=False,
    ) -> BaseRegistryState:
        # processing registered artifacts and versions first
        for artifact in state.get_artifacts().values():
            for version in artifact.versions:
                commit = self.scm.resolve_commit(version.commit_hexsha)
                enrichments = self.describe(
                    artifact.artifact,
                    rev=commit.hexsha,
                )
                version.add_event(
                    EnrichmentEvent(
                        artifact=artifact.artifact,
                        version=version.version,
                        created_at=commit.commit_datetime,
                        author=commit.author_name,
                        author_email=commit.author_email,
                        commit_hexsha=commit.hexsha,
                        message=commit.message,
                        committer=commit.committer_name,
                        committer_email=commit.committer_email,
                        enrichments=enrichments,
                    )
                )
                state.update_artifact(artifact)
        for commit in self.get_commits(
            all_branches=all_branches, all_commits=all_commits
        ):
            for art_name in GTOEnrichment().discover(self.scm, commit.hexsha):
                enrichments = self.describe(art_name, rev=commit.hexsha)
                artifact = state.find_artifact(art_name, create_new=True)
                version = artifact.find_version(
                    commit_hexsha=commit.hexsha, create_new=True
                )

                assert version is not None and not isinstance(
                    version, list
                ), "Expected a single Version instance"
                version.add_event(
                    EnrichmentEvent(
                        artifact=artifact.artifact,
                        version=version.version,
                        created_at=commit.commit_datetime,
                        author=commit.author_name,
                        author_email=commit.author_email,
                        commit_hexsha=commit.hexsha,
                        message=commit.message,
                        committer=commit.committer_name,
                        committer_email=commit.committer_email,
                        enrichments=enrichments,
                    )
                )
                state.update_artifact(artifact)
        return state


class GTOInfo(EnrichmentInfo):
    source: str = "gto"
    artifact: Artifact

    def get_object(self) -> BaseModel:
        return self.artifact

    def get_human_readable(self) -> str:
        return self.artifact.model_dump_json()

    def get_path(self):
        return self.artifact.path


class GTOEnrichment(EnrichmentReader):
    source: str = "gto"

    def discover(  # pylint: disable=no-self-use
        self, url_or_scm: Union[str, Git], rev: str
    ) -> Dict[str, GTOInfo]:
        with RepoIndexManager.from_url(url_or_scm) as index:
            index = index.get_commit_index(rev)
        if index:
            return {
                name: GTOInfo(artifact=artifact)
                for name, artifact in index.state.items()
            }
        return {}

    def describe(
        self, url_or_scm: Union[str, Git], obj: str, rev: Optional[str]
    ) -> Optional[GTOInfo]:
        with RepoIndexManager.from_url(url_or_scm) as index:
            index = index.get_commit_index(rev or index.scm.get_rev())
        if index and obj in index.state:
            return GTOInfo(artifact=index.state[obj])
        return None
