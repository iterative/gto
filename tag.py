import git

REGISTER = "register"
UNREGISTER = "unregister"
PROMOTE = "promote"
DEMOTE = "demote"


def name(action, model, version=None, label=None, repo=None):
    if action == REGISTER:
        return f"model-{model}-{REGISTER}-{version}"
    if action == UNREGISTER:
        return f"model-{model}-{UNREGISTER}-{version}"

    basename = f"model-{model}-{PROMOTE}-{label}"
    existing_names = [c.name for c in repo.tags if c.name.startswith(basename)]
    if existing_names:
        last_number = 1 + max(int(n[len(basename) + 1 :]) for n in existing_names)
    else:
        last_number = 1
    if action == PROMOTE:
        return f"{basename}-{last_number}"
    if action == DEMOTE:
        return f"model-{model}-{DEMOTE}-{label}-{last_number}"
    raise ValueError(f"Unknown action: {action}")


def parse(name, raise_on_fail=True):
    if isinstance(name, git.Tag):
        name = name.name
    if UNREGISTER in name:
        model, version = name.split(f"-{UNREGISTER}-")
        model = model[len("model-") :]
        return dict(action=UNREGISTER, model=model, version=version)
    if REGISTER in name:
        model, version = name.split(f"-{REGISTER}-")
        model = model[len("model-") :]
        return dict(action=REGISTER, model=model, version=version)
    if PROMOTE in name:
        model, label = name.split(f"-{PROMOTE}-")
        model = model[len("model-") :]
        label, number = label.split("-")
        return dict(action=PROMOTE, model=model, label=label, number=number)
    if DEMOTE in name:
        model, label = name.split(f"-{DEMOTE}-")
        model = model[len("model-") :]
        label, number = label.split("-")
        return dict(action=DEMOTE, model=model, label=label, number=number)
    if raise_on_fail:
        raise ValueError(f"Unknown tag name: {name}")
    else:
        return dict()


def find(
    action=None,
    model=None,
    version=None,
    label=None,
    repo=None,
    sort="by_time",
    tags=None,
):
    if tags is None:
        tags = [t for t in repo.tags if parse(t.name, raise_on_fail=False)]
    if action:
        tags = [t for t in tags if parse(t.name)["action"] == action]
    if model:
        tags = [t for t in tags if parse(t.name).get("model") == model]
    if version:
        tags = [t for t in tags if parse(t.name).get("version") == version]
    if label:
        tags = [t for t in tags if parse(t.name).get("label") == label]
    if sort == "by_time":
        tags = sorted(tags, key=lambda t: t.tag.tagged_date)
    return tags


def find_registered(model, repo):
    """Return all registered versions for model"""
    register_tags = find(action=REGISTER, model=model, repo=repo)
    unregister_tags = find(action=UNREGISTER, model=model, repo=repo)
    return [
        r
        for r in register_tags
        if not any(
            r.commit.hexsha == u.commit.hexsha
            and parse(r.name)["model"] == parse(u.name)["model"]
            and parse(r.name)["version"] == parse(u.name)["version"]
            for u in unregister_tags
        )
    ]


def find_latest(model, repo):
    """Return latest registered version for model"""
    return find_registered(model, repo)[-1]


def find_promoted(model, label, repo):
    """Return all promoted versions for model"""
    promote_tags = find(action=PROMOTE, model=model, label=label, repo=repo)
    demote_tags = find(action=DEMOTE, model=model, label=label, repo=repo)
    # what we do if someone promotes and demotes one model+commit several times?
    return [
        p
        for p in promote_tags
        if not any(
            p.commit.hexsha == d.commit.hexsha
            and parse(p.name)["model"] == parse(d.name)["model"]
            and parse(p.name)["label"] == parse(d.name)["label"]
            for d in demote_tags
        )
    ]


def find_current_promoted(model, label, repo):
    """Return latest promoted version for model"""
    return find_promoted(model, label, repo)[-1]


def find_version(model, label, repo):
    """Return version of model with specific label active"""
    tags = find(action=PROMOTE, model=model, label=label, repo=repo)
    version_sha = tags[-1].commit.hexsha

    # if this commit has been tagged several times (model-v1, model-v2)
    # you may have several tags with different versions
    # so when you PROMOTE model, you won't know which version you've promoted
    # v1 or v2
    tags = find(action=REGISTER, model=model, repo=repo)
    tags = [t for t in tags if t.commit.hexsha == version_sha]
    return parse(tags[-1].name)["version"]
