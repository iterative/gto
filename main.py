import warnings

import click
import git
import pandas as pd
from IPython.display import display

import tag


@click.group()
def cli():
    """Early prototype for registering/status assignment for tags-based approach"""
    pass


@cli.command()
@click.argument("model")
@click.argument("version")
def register(model, version):
    """Register new model version"""
    repo.create_tag(
        tag.name(tag.REGISTER, model, version=version, repo=repo),
        message=f"Registering model {model} version {version}",
    )
    click.echo(f"Registered model {model} version {version}")


@cli.command()
@click.argument("model")
@click.argument("version")
def unregister(model, version):
    """Unregister model version"""
    tags = tag.find(action=tag.REGISTER, model=model, version=version, repo=repo)
    if len(tags) != 1:
        raise ValueError(f"Found {len(tags)} tags for model {model} version {version}")
    repo.create_tag(
        tag.name(tag.UNREGISTER, model, version=version, repo=repo),
        ref=tags[0].commit.hexsha,
        message=f"Unregistering model {model} version {version}",
    )
    click.echo(f"Unregistered model {model} version {version}")


@cli.command()
@click.argument("model")
@click.argument("version")
@click.argument("status")
def promote(model, version, status):
    """Assign status to specific model version"""
    version_hexsha = repo.tags[
        tag.name(tag.REGISTER, model, version=version)
    ].commit.hexsha
    name = tag.name(tag.PROMOTE, model, status=status, repo=repo)
    repo.create_tag(
        name,
        ref=version_hexsha,
        message=f"Promoting model {model} version {version} to status {status}",
    )
    click.echo(f"Promoted model {model} version {version} to status {status}")


@cli.command()
@click.argument("model")
def latest(model):
    """Return latest version for model"""
    click.echo(tag.parse(tag.find_latest(model, repo=repo).name)["version"])


@cli.command()
@click.argument("model")
@click.argument("status")
def which(model, status):
    """Return version of model with specific status active"""
    tags = tag.find(action=tag.PROMOTE, model=model, status=status, repo=repo)
    version_sha = tags[-1].commit.hexsha

    # if this commit has been tagged several times (model-v1, model-v2)
    # you may have several tags with different versions
    # so when you PROMOTE model, you won't know which version you've promoted
    # v1 or v2
    tags = tag.find(action=tag.REGISTER, model=model, repo=repo)
    tags = [t for t in tags if t.commit.hexsha == version_sha]
    click.echo(tag.parse(tags[-1].name)["version"])


@cli.command()
@click.argument("model")
@click.argument("status")
def demote(model, status):
    """De-promote model from given status"""
    promoted_tag = tag.find(action=tag.PROMOTE, model=model, status=status, repo=repo)[-1]
    repo.create_tag(
        tag.name(tag.DEMOTE, model, status=status, repo=repo),
        rev=promoted_tag.commit.hexsha,
        message=f"Demoting model {model} from status {status}",
    )
    click.echo(f"Demoted model {model} from status {status}")



@cli.command()
def show():
    """Show current registry state"""
    versions = []
    statuses = []
    tags_info = []
    for t in tag.find(repo=repo):
        tag_parsed = tag.parse(t.name)
        tag_parsed["tag_name"] = t.name  # better use hexsha
        if tag_parsed["action"] in (tag.PROMOTE, tag.DEMOTE):
            statuses.append(tag_parsed)
        else:
            versions.append(tag_parsed)
        tags_info.append(
            dict(
                tag_name=t.name,
                commit_hexsha=t.commit.hexsha[:7],
                datetime=pd.Timestamp(t.tag.tagged_date * 1e9),
                # message=t.tag.message,
                author=t.tag.tagger.name,
            )
        )
    versions = pd.DataFrame(versions)
    statuses = pd.DataFrame(statuses)
    tags_info = pd.DataFrame(tags_info)
    statuses_info = (
        (
            statuses
            .drop(columns=["action"])
            .merge(
                tags_info[["tag_name", "commit_hexsha"]], how="left", on="tag_name"
            )
        )
        .merge(
            (
                versions
                .drop(columns=["action"])
                .merge(
                    tags_info[["tag_name", "commit_hexsha"]], how="left", on="tag_name"
                ).drop(columns=["tag_name"])
            ),
            how="left",
            on=["model", "commit_hexsha"],
        )
        .drop(columns=["commit_hexsha"])
        .merge(tags_info, how="left", on=["tag_name"])
        .sort_values(["datetime"], ascending=False)
    )
    statuses_info = statuses_info[
        ["model", "version", "status"]
        + [c for c in statuses_info.columns if c not in ["model", "version", "status"]]
    ]

    display("\n=== Current statuses (MLflow dashboard) ===")
    latest_statuses = (
        statuses_info.sort_values("datetime", ascending=False)
        .groupby(["model", "status"])
        .first()[["version"]]
        .unstack()
    )
    latest_versions = (
        versions.groupby("model")
        .version.max()
        .to_frame()
        .rename(columns={"version": "latest_version"})
    )
    display(
        latest_versions.merge(
            latest_statuses, how="left", left_index=True, right_index=True
        )
    )
    display("\n=== Status assigning audit trail ===")
    display(statuses_info)
    display("\n=== Model registration audit trail ===")
    display(
        versions.merge(tags_info, how="left", on=["tag_name"]).sort_values(
            "datetime", ascending=False
        )
    )


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    pd.set_option('display.max_colwidth', 100)

    repo = git.Repo(".")
    cli()
