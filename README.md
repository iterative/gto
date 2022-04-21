# GTO

[![Check, test and release](https://github.com/iterative/gto/actions/workflows/check-test-release.yml/badge.svg)](https://github.com/iterative/gto/actions/workflows/check-test-release.yml)
[![Codecov](https://codecov.io/gh/iterative/gto/branch/main/graph/badge.svg?token=NXT11717BG)](https://codecov.io/gh/iterative/gto)
[![PyPi](https://img.shields.io/pypi/v/gto.svg?label=pip&logo=PyPI&logoColor=white)](https://pypi.org/project/gto)

Git Tag Ops. Turn your Git repository into an Artifact Registry:

* Register new versions of artifacts marking releases/significant changes
* Promote versions to ordered, named stages to track their lifecycles
* GitOps: signal CI/CD automation or downstream systems to act upon these actions
* Maintain and query artifact metadata / additional info with Enrichments machinery

GTO versions and promotes artifacts by creating annotated Git tags in special format.

## Installation

Install GTO with pip:

```
$ pip install gto
```

This will install both python package with API you can use and CLI `gto` entrypoint.

Installing this package is enough to get started with using any repo as an artifact registry - no need to set up neither other services, nor a DB.

## Quick walkthrough

The README will cover CLI usage, but for every command there is a Python API counterpart in the [`gto.api`](/iterative/gto/blob/main/gto/api.py) module. In README we'll use this example repo: https://github.com/iterative/gto-example

Let's clone the example repo first:
```
$ git clone git@github.com:iterative/gto-example.git
$ cd gto-example
```

## Versioning

To register new version of artifact, you can use `gto register` command. You usually use those to mark significant changes to the artifact. Running `gto register` creates a special git tag.

```
$ gto register rf
Created git tag 'rf@v0.0.1' that registers a new version
```

## Promoting

You could also promote a specific artifact version to Stage. Stages are statuses of your artifact specifying the readiness to be used by downstream systems. You can use promotions to signal downstream systems to act via CI/CD or webhooks - for example, redeploy a ML model (if your artifact is a model) or update the some special file on server (if your artifact is a file).

```
$ gto promote rf prod
Created git tag 'rf#prod#1' that promotes 'v0.0.1'
```

There are two notations used for git tags in promotion:
- simple: `rf#prod`
- incremental: `rf#prod-N`

Incremental is the default one and we suggest you use it when possible. The benefit of using it is that you don't have to delete git tags (with simple notation you'll need to delete them because you can't have two tags with the same name). This will keep the history of your promotions.

## Artifacts

So far we've seen how to register versions and promote them, but we still didn't specify `type` of artifact (dataset, model, something else) and `path` to it. For simple workflows, when we have a single artifact, we can hardcore those to CI/CD or downstream systems. But for more advanced cases we would like to codify them - and we can do that with `artifacts.yaml` file.

To annotate artifact, use `gto annotate`:

```
$ gto annotate rf --type model --path models/neural-network.pkl
```

You could also modify `artifacts.yaml` file directly.

There are two kinds of artifacts that GTO recognizes:
1. Files/folders committed to the repo. When you register a new version or promote it to stage, Git guarantees that it's immutable. You can return to your repo a year later and be able to get 100% the same artifact by providing the same version.
2. `virtual` artifacts. This could be an external path, e.g. `s3://mybucket/myfile` or a local path if the file wasn't committed (as in case with DVC). In this case GTO can't pin the current physical state of the artifact and guarantee it's immutability. If `s3://mybucket/myfile` changes, you won't have any way neither retrieve, nor understand it's different now than it was before when you registered that artifact version.

By default GTO treats your artifact as a `vitrual` one. To make sure it's not a vitrual one, you could supply `--must_exist` flag to `gto annotate`.

In future versions, we will add enrichments: useful information other tools like DVC and MLEM can provide about the artifacts. This will allow treating files versioned with DVC and DVC PL outputs as usual artifacts instead `virtual` ones.

## Using the registry

Let's see what are the commands that help us use the registry.

### Show the actual state

This is the actual state of the registry: all artifacts, their latest versions, and what is promoted to stages right now.

```
$ gto show
╒══════════════╤══════════════════╤════════════════════╤═════════════════╕
│ name         │ latest version   │ stage/production   │ stage/staging   │
╞══════════════╪══════════════════╪════════════════════╪═════════════════╡
│ nn           │ v0.0.1           │ -                  │ v0.0.1          │
│ rf           │ v1.0.1           │ v1.0.0             │ v1.0.1          │
│ features-dvc │ -                │ -                  │ -               │
╘══════════════╧══════════════════╧════════════════════╧═════════════════╛
```

Here we'll see both artifacts that have git tags created for them (i.e. artifacts with registered or promoted versions) and artifacts that were annotated in `artifacts.yaml`. Use `--all-branches` or `--all-commits` to read `artifacts.yaml` from more commits than just HEAD.

Add artifact name to print versions of that artifact:

```
$ gto show rf
╒════════════╤════════╤════════════╤═════════════════════╤═══════════════════╤════════════════╕
│ artifact   │ name   │ stage      │ creation_date       │ author            │ commit_hexsha  │
╞════════════╪════════╪════════════╪═════════════════════╪═══════════════════╪════════════════╡
│ rf         │ v1.0.0 │ production │ 2022-04-18 18:49:36 │ Alexander Guschin │ 0e87447        │
│ rf         │ v1.0.1 │ staging    │ 2022-04-18 18:50:41 │ Alexander Guschin │ ff5d58e        │
╘════════════╧════════╧════════════╧═════════════════════╧═══════════════════╧════════════════╛
```

### See the history of an artifact

`gto history` will print a journal of events happened with your artifact. This will help you to understand what was happening and audit changes.

```
$ gto history rf
╒═════════════════════╤════════╤══════════════╤═══════════╤════════════╤══════════╤═══════════════════╕
│ timestamp           │ name   │ event        │ version   │ stage      │ commit   │ author            │
╞═════════════════════╪════════╪══════════════╪═══════════╪════════════╪══════════╪═══════════════════╡
│ 2022-04-18 18:49:34 │ rf     │ commit       │ -         │ -          │ 0e87447  │ Alexander Guschin │
│ 2022-04-18 18:49:36 │ rf     │ registration │ v1.0.0    │ -          │ 0e87447  │ Alexander Guschin │
│ 2022-04-18 18:50:38 │ rf     │ commit       │ -         │ -          │ ff5d58e  │ Alexander Guschin │
│ 2022-04-18 18:50:41 │ rf     │ registration │ v1.0.1    │ -          │ ff5d58e  │ Alexander Guschin │
│ 2022-04-18 18:51:45 │ rf     │ promotion    │ v1.0.0    │ production │ 0e87447  │ Alexander Guschin │
│ 2022-04-18 18:52:48 │ rf     │ promotion    │ v1.0.1    │ staging    │ ff5d58e  │ Alexander Guschin │
╘═════════════════════╧════════╧══════════════╧═══════════╧════════════╧══════════╧═══════════════════╛
```

## Act on new versions and promotions in CI

To act upon created git tags, you can create simple CI workflow. With GH actions it can look like this:
```
name: Act on git tags that register versions / promote "rf" actifact
on:
  push:
    tags:
      - "rf*"
```

When CI is triggered, you can use the git reference to determine the version of the artifact that was registered or promoted. In GH Actions you can use the `GITHUB_REF` environment variable to determine the version (check out GH Actions workflow in the example repo). You can parse tags manually or use `gto check-ref`. You can check out how it works locally:

```
$ gto check-ref rf@v1.0.1
version:
  rf:
    artifact: rf
    author: Alexander Guschin
    commit_hexsha: 9fbb8664a4a48575ee5d422e177174f20e460b94
    created_at: '2022-03-18T12:11:21'
    deprecated_date: null
    name: v1.0.1
```

### Getting right versions in downstream systems

To get the latest artifact version, it's path and git reference, run:

```
$ gto latest rf
v1.0.1
$ gto latest rf --ref
rf@v1.0.1
```

To get the version that is currently promoted to environment, run:

```
$ gto which rf production
v1.0.0
$ gto which rf production --ref
rf#production#2
```

To get details about those artifacts from `artifacts.yaml`, use `gto describe`:
```
$ gto describe rf
{
    "type": "model",
    "path": "models/random-forest.pkl",
    "virtual": false
}
```

## Configuration

You can write configuration in `.gto` file in the root of your repo or use environment variables like this (note the `GTO_` prefix):
```shell
GTO_EMOJIS=false gto show
```

The example config written to `.gto` file could look like this:
```
type_allowed: [model, dataset]  # list of allowed types
stage_allowed: [dev, stage, prod]  # list of allowed Stages
```

## Trying out the latest version

### 1. Clone this repository

```bash
git clone git@github.com:iterative/gto.git
cd gto
```

### 2. Create virtual environment named `venv`
```bash
python3 -m venv venv
source venv/bin/activate
```
Install python libraries

```bash
pip install --upgrade pip setuptools wheel ".[tests]"
```

### 3. Run

```bash
pytest --basetemp=pytest-cache
```

This will create `pytest-cache` folder with some fixtures that can serve as examples.

Notably, check out this folder:
```
cd pytest-cache/test_api0/
gto show -v
```
The code that generates this folder could be found [in this fixture](https://github.com/iterative/gto/blob/main/tests/conftest.py#L58).

To continue experimenting, call
```bash
gto --help
```
