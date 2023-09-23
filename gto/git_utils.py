import logging
import os.path
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Union

from scmrepo.exceptions import SCMError
from scmrepo.git import Git, SyncStatus

from gto.config import RegistryConfig
from gto.exceptions import GTOException, NoRepo, WrongArgs
from gto.ui import echo


class RemoteRepoMixin:
    @classmethod
    @contextmanager
    def from_scm(
        cls,
        scm: Git,
        cloned: bool = False,
        config: Optional[RegistryConfig] = None,
    ):
        """
        `cloned` - scm is a remote repo that was cloned locally into a tmp
                   directory to be used for the duration of the context manager.
                   Means that we push tags and changes back to the remote repo.
        """
        raise NotImplementedError()

    @classmethod
    @contextmanager
    def from_url(
        cls,
        url_or_scm: Union[str, Path, Git],
        config: Optional[RegistryConfig] = None,
        branch=None,
    ):
        if isinstance(url_or_scm, Git):
            with cls.from_scm(url_or_scm) as obj:
                yield obj
            return
        url_or_scm = str(url_or_scm)
        if os.path.exists(url_or_scm):
            scm = Git(url_or_scm)
            try:
                scm.dir
            except SCMError as e:
                scm.close()
                raise NoRepo(url_or_scm) from e
            if branch:
                raise WrongArgs("branch can only be set for remote repos")
            try:
                with cls.from_scm(scm=scm, config=config) as obj:
                    yield obj
            finally:
                scm.close()
        else:
            with cloned_git_repo(url_or_scm) as scm:
                if branch:
                    scm.checkout(branch)
                with cls.from_scm(scm=scm, config=config, cloned=True) as obj:
                    yield obj

    def _call_commit_push(
        self,
        func,
        commit=False,
        commit_message=None,
        push=False,
        stdout=False,
        **kwargs,
    ):
        if not (commit or push):
            return func(**kwargs, stdout=stdout)
        stashed = set()
        stashed.update(self.scm.status())
        with self.scm.stash_workspace(include_untracked=True):
            result = func(**kwargs, stdout=stdout)
            if any(stashed.intersection(files) for files in self.scm.status()):
                _reset_repo_to_head(self.scm)
                raise GTOException(
                    msg="The command would have changed files that were not committed, "
                    "automated committing is not possible.\n"
                    "Suggested action: Commit the changes and re-run this command."
                )
            git_add_and_commit_all_changes(
                self.scm,
                message=commit_message,
            )
            if push:
                self.scm.push()
            if stdout:
                echo(
                    "Running `git commit`"
                    if not push
                    else "Running `git commit` and `git push`"
                    "\nSuccessfully pushed a new commit to remote."
                )
        return result


@contextmanager
def cloned_git_repo(url: str) -> Git:
    with TemporaryDirectory() as tmp_dir:
        logging.debug("create temporary directory %s", tmp_dir)
        scm = Git.clone(url, tmp_dir)
        try:
            scm.dir
        except SCMError as e:
            scm.close()
            raise NoRepo(url) from e
        try:
            yield scm
        finally:
            scm.close()


def git_push_tag(
    scm: Git,
    tag_name: str,
    delete: bool = False,
    remote_name: str = "origin",
) -> None:
    ref = f"refs/tags/{tag_name}"
    src = "" if delete else ref
    refspec = f"{src}:{ref}"
    logging.debug(
        "push %s tag %s from directory %s to remote %s",
        "--delete" if delete else "",
        tag_name,
        scm.root_dir,
        remote_name,
    )
    try:
        result = scm.push_refspecs(remote_name, refspec)
    except SCMError as e:
        raise GTOException(
            msg=f"The command `git push {remote_name} {tag_name}` failed. "
            f"Make sure your local repository is in sync with the remote."
        ) from e
    for _ref, status in result.items():
        if status == SyncStatus.DIVERGED:
            raise GTOException(
                msg=f"The command `git push {remote_name} {tag_name}` failed. "
                f"Make sure your local repository is in sync with the remote."
            )


def git_add_and_commit_all_changes(scm: Git, message: str) -> None:
    staged, unstaged, untracked = scm.status()
    if staged or unstaged or untracked:
        files = list(chain(staged, unstaged, untracked))
        logging.debug("Adding to the index the untracked files %s", untracked)
        logging.debug("Add and commit changes to files %s", files)
        scm.add(files)
        scm.commit(message)


def _reset_repo_to_head(scm: Git) -> None:
    if scm.stash.push(include_untracked=True):
        scm.stash.drop()
