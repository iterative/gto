import pytest
import git

from gto import init_index


@pytest.fixture
def empty_git_repo(tmp_path):
    return git.Repo.init(tmp_path)



