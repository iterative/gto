import pytest
from scmrepo.git import Git

from gto.constants import Action
from gto.exceptions import RefNotFound, TagExists
from gto.tag import create_tag, find, name_tag, parse_name, parse_tag


def test_name_tag(scm: Git):
    assert name_tag(Action.REGISTER, "myartifact", "v1", simple=True) == "myartifact@v1"
    assert (
        name_tag(Action.REGISTER, "myartifact", "v1", simple=False, scm=scm)
        == "myartifact@v1#1"
    )
    assert (
        name_tag(Action.DEREGISTER, "myartifact", "v1", simple=True) == "myartifact@v1!"
    )
    assert (
        name_tag(Action.DEREGISTER, "myartifact", "v1", simple=False, scm=scm)
        == "myartifact@v1!#1"
    )
    assert (
        name_tag(Action.ASSIGN, "myartifact", stage="stage", simple=True)
        == "myartifact#stage"
    )
    assert (
        name_tag(Action.ASSIGN, "myartifact", scm=scm, stage="stage", simple=False)
        == "myartifact#stage#1"
    )
    assert (
        name_tag(Action.UNASSIGN, "myartifact", scm=scm, stage="stage", simple=False)
        == "myartifact#stage!#1"
    )


def test_parse_name():
    assert parse_name("path@v1.2.3") == {
        "name": "path",
        "version": "v1.2.3",
        "action": Action.REGISTER,
    }
    assert parse_name("path@v1.2.3#5") == {
        "name": "path",
        "version": "v1.2.3",
        "action": Action.REGISTER,
        "counter": 5,
    }
    assert parse_name("path@v1.2.3!") == {
        "name": "path",
        "version": "v1.2.3",
        "action": Action.DEREGISTER,
    }
    assert parse_name("path@v1.2.3!#2") == {
        "name": "path",
        "version": "v1.2.3",
        "action": Action.DEREGISTER,
        "counter": 2,
    }
    assert parse_name("path#stage") == {
        "name": "path",
        "action": Action.ASSIGN,
        "stage": "stage",
    }
    assert parse_name("path#stage#1") == {
        "name": "path",
        "action": Action.ASSIGN,
        "stage": "stage",
        "counter": 1,
    }
    assert parse_name("path#stage!#2") == {
        "name": "path",
        "action": Action.UNASSIGN,
        "stage": "stage",
        "counter": 2,
    }


@pytest.mark.parametrize(
    "tag_name",
    [
        "",
        "###",
        "@@@",
        "model@v1",
        "nn#prod#-1",
        "model@v111",
        "model-prod",
        "model@0.0.1",
        "model-prod-v1",
        "model#prod#-1",
        "model#prod#1-2",
        "model#prod?#1-2",
        "model#prod@v1.2.3",
        "model@v1.2.3#prod",
        "model-prod-v1-stage",
        "model@prod@v1@stage-1",
        "namespace/model@0.0.1",
        "@namespace/model@0.0.1",
        "model#prod#v1#stage#1-",
        "model#prod-v1-stage@1-2",
        "model#prod-v1-stage@1-2#@",
    ],
)
def test_parse_wrong_names(tag_name: str):
    assert not parse_name(tag_name, raise_on_fail=False)


@pytest.mark.parametrize(
    "tag_name",
    [
        "nn#prod",
        "nn#prod!",
        "nn#prod#1",
        "nn@v1.0.0",
        "nn#prod!#2",
        "nn@v1.0.0!",
        "nn@v1.0.0#1",
        "nn@v1.0.0!#1",
        "nn@v1.0.0-rc.2",
        "nn@v1.0.0-alpha",
        "nn@v1.0.0-alpha.1",
        "nn@v1.0.0-alpha.beta",
        "new-artifact@v1.0.1!",
    ],
)
def test_parse_correct_names(tag_name: str):
    assert parse_name(tag_name, raise_on_fail=False)


@pytest.mark.usefixtures("repo_with_commit")
def test_create_tag_bad_ref(scm: Git):
    with pytest.raises(RefNotFound):
        create_tag(scm, "name", rev="wrongref", message="msg")
    with pytest.raises(RefNotFound):
        create_tag(
            scm, "name", rev="679dd96f8f22bef6505b9646803bf3c2afe94692", message="msg"
        )


@pytest.mark.usefixtures("repo_with_commit")
def test_create_tag_repeated_tagname(scm: Git):
    create_tag(scm, "name", rev="HEAD", message="msg")
    with pytest.raises(TagExists):
        create_tag(scm, "name", rev="HEAD", message="msg")


@pytest.mark.usefixtures("repo_with_commit")
def test_lightweight_tag(scm: Git):
    scm.tag("lightweight-tag@v0.0.1")
    assert find(scm=scm) == []


@pytest.mark.usefixtures("repo_with_commit")
def test_parse_tag_created_at_timezone(scm: Git):
    create_tag(scm, "nn#prod", rev="HEAD", message="msg")
    tag = parse_tag(scm.get_tag("nn#prod"))
    d = tag.created_at
    assert d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None
