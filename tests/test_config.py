import pytest

# from gto.api import add
from gto.config import CONFIG_FILE_NAME

# from gto.exceptions import UnknownType
from gto.index import init_index_manager
from gto.registry import GitRegistry


@pytest.fixture
def init_repo(empty_git_repo):
    repo, write_file = empty_git_repo

    write_file(
        CONFIG_FILE_NAME,
        "type_allowed: [model, dataset]",
    )
    return repo


def test_config_load_index(init_repo):
    index = init_index_manager(init_repo)
    assert index.config.TYPE_ALLOWED == ["model", "dataset"]


def test_config_load_registry(init_repo):
    registry = GitRegistry.from_repo(init_repo)
    assert registry.config.TYPE_ALLOWED == ["model", "dataset"]


# def test_adding_allowed_type(init_repo):
#     add(init_repo, "model", "name", "path", virtual=True)


# def test_adding_not_allowed_type(init_repo):
#     with pytest.raises(UnknownType):
#         add(init_repo, "unknown", "name", "path", virtual=True)
