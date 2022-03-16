"""TODO: add more tests for API"""
import pytest

import gto
from tests.utils import _check_dict


def test_empty_index(empty_git_repo):
    index = gto.api.get_index(empty_git_repo.working_dir)
    assert len(index.object_centric_representation()) == 0


def test_empty_state(empty_git_repo):
    state = gto.api.get_state(empty_git_repo.working_dir)
    assert len(state.objects) == 0


def test_api_info_commands(empty_git_repo):
    gto.api.show(empty_git_repo.working_dir)
    gto.api.audit_registration(empty_git_repo.working_dir)
    gto.api.audit_promotion(empty_git_repo.working_dir)
    gto.api.history(empty_git_repo.working_dir)


@pytest.fixture
def repo_with_artifact(init_showcase_numbers):
    path, repo, write_file = init_showcase_numbers  # pylint: disable=unused-variable
    name, type, path_ = "new-artifact", "new-type", "new/path"
    gto.api.add(path, type, name, path_)
    repo.index.add(["artifacts.yaml"])
    repo.index.commit("Added index")
    return repo, name


def test_add_remove(empty_git_repo):
    name, type, path = "new-artifact", "new-type", "new/path"
    gto.api.add(empty_git_repo.working_dir, type, name, path)
    index = gto.api.get_index(empty_git_repo.working_dir).get_index()
    assert name in index
    _check_dict(index.state[name], dict(name=name, type=type, path=path), {})
    gto.api.remove(empty_git_repo.working_dir, name)
    index = gto.api.get_index(empty_git_repo.working_dir).get_index()
    assert name not in index


def test_register(repo_with_artifact):
    repo, name = repo_with_artifact
    vname1, vname2 = "v1", "v2"
    gto.api.register(repo.working_dir, name, "HEAD", vname1)
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname1
    gto.api.add(repo.working_dir, "something-irrelevant", "doesnt-matter", "anything")
    repo.index.commit("Irrelevant action to create a git commit")
    gto.api.register(repo.working_dir, name, "HEAD")
    latest = gto.api.find_latest_version(repo.working_dir, name)
    assert latest.name == vname2


def test_promote(repo_with_artifact):
    repo, name = repo_with_artifact
    env = "staging"
    gto.api.promote(repo.working_dir, name, env, promote_ref="HEAD", name_version="v1")
    label = gto.api.find_active_label(repo.working_dir, name, env)
    author = repo.commit().author.name
    _check_dict(
        label,
        dict(
            object=name,
            version="v1",
            name=env,
            author=author,
            commit_hexsha=repo.commit().hexsha,
        ),
        {"creation_date", "deprecated_date"},
    )


def test_deprecate_show_audit(showcase):
    """Test that show/audit don't break after deprecating"""
    (
        path,
        repo,
        write_file,  # pylint: disable=unused-variable
        first_commit,  # pylint: disable=unused-variable
        second_commit,  # pylint: disable=unused-variable
    ) = showcase

    gto.api.show(path)
    gto.api.audit_registration(path)
    gto.api.audit_promotion(path)

    gto.api.deprecate(path, "rf", "v1.2.3")
    gto.api.show(path)
    gto.api.audit_registration(path)
    gto.api.audit_promotion(path)

    gto.api.deprecate(repo, "nn", "v0.0.1")
    gto.api.show(repo)
    gto.api.audit_registration(repo)
    gto.api.audit_promotion(repo)

    gto.api.deprecate(repo, "rf", "v1.2.4")
    gto.api.show(repo)
    gto.api.audit_registration(repo)
    gto.api.audit_promotion(repo)

    assert gto.api.find_latest_version(repo, "nn") is None
    assert (
        gto.api.find_latest_version(repo, "nn", include_deprecated=True).name
        == "v0.0.1"
    )
