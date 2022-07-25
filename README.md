# GTO

[![Check, test and release](https://github.com/iterative/gto/actions/workflows/check-test-release.yml/badge.svg)](https://github.com/iterative/gto/actions/workflows/check-test-release.yml)
[![Codecov](https://codecov.io/gh/iterative/gto/branch/main/graph/badge.svg?token=NXT11717BG)](https://codecov.io/gh/iterative/gto)
[![PyPi](https://img.shields.io/pypi/v/gto.svg?label=pip&logo=PyPI&logoColor=white)](https://pypi.org/project/gto)

Git Tag Ops. Turn your Git repository into an Artifact Registry:

- Registry: Track new artifacts and their versions for releases and significant
  changes.
- Lifecycle Management: Create actionable stages for versions marking status of
  artifact or it's readiness to be consumed by a specific environment.
- GitOps: Signal CI/CD automation or other downstream systems to act upon these
  new versions and lifecycle updates.
- Enrichments: Annotate and query artifact metadata with additional information.

GTO works by creating annotated Git tags in a standard format.

## Installation

> GTO requires Python 3. It works on any OS.

```console
$ python -m pip install gto
```

[This package](https://pypi.org/project/gto/) will install the `gto`
command-line interface (CLI) and make the Python API available for use in code.

There's no need to set up any services or databases :)

## Getting started

> Note: We will cover CLI usage, but every command has a corresponding Python
> API counterpart in the [`gto.api`](/iterative/gto/blob/main/gto/api.py)
> module.

In this document we'll use this example repo:
https://github.com/iterative/example-gto. Let's clone it first:

```console
$ git clone https://github.com/iterative/example-gto.git
$ cd example-gto
```

### Versioning

To register a new artifact or a new version, use `gto register`. This is usually
done to mark significant changes to the artifact (such as a release or a
deprecation).

```console
$ gto register awesome-model
Created git tag 'awesome-model@v0.0.1' that registers a new version
```

<details summary="What happens under the hood?">

GTO creates a special Git tag for the artifact version, in a standard format:
`{artifact_name}@{version_number}`.

The version is now associated to the current Git commit (`HEAD`). You can have
several versions in a given commit, ordered by their automatic version numbers.

</details>

### Assing a stage

Assing an actionable stage for a specific artifact version with `gto assign`.
Stages can mark it's readiness for a specific consumer. You can plug in a real
downsteam system via CI/CD or web hooks. For example: redeploy an ML model.

```console
$ gto assign awesome-model prod
Created git tag 'awesome-model#prod#1' that adds stage 'prod' to 'v0.0.1'
```

<details summary="What happens under the hood?">

GTO creates a special Git tag in a standard format:
`{artifact_name}#{stage}#{e}`.

The event is now associated to the latest version of the artifact. There can be
multiple events for a given version, ordered by an automatic incremental event
number (`{e}`). This will keep the history of your stages creation.

Note: if you prefer, you can use simple stage tag format without the incremental
`{e}`, but this will disable the `gto history` command. This is because
assigning a stage to an artifact version where a stage tag already existed will
require deleting the existing tag.

</details>

### Unassign a stage

Note: this functionality is in development and will be introduced soon.

Sometimes you need to mark an artifact version no longer ready for a specific
consumer, and maybe signal a downstream system about this. You can use
`gto unassign` for that:

```console
$ gto unassign awesome-model prod
Created git tag 'awesome-model#prod#2!' that unassigns stage 'prod' from 'v0.0.1'
```

<details summary="Some details and options">

GTO creates a special Git tag in a standard format:
`{artifact_name}#{stage}#{e}!`.

Note, that later you can create this stage again, if you need to, by calling
`$ gto assign`.

You also may want to delete the git tag instead of creating a new one. This is
useful if you don't want to keep extra tags in you Git repo, don't need history
and don't want to trigger a CI/CD or another downstream system. For that, you
can use:

```console
$ gto unassign --delete
Deleted git tag 'awesome-model#prod#1' that assigned 'prod' to 'v0.0.1'
To push the changes upsteam, run:
git push origin awesome-model#prod#1 --delete
```

</details>

### Annotating

So far we've seen how to register and assign a stage to an artifact versions,
but we still don't have much information about them. What about the type of
artifact (dataset, model, etc.) or the file path to find it in the working tree?

For simple projects (e.g. single artifact) we can assume the details in a
downstream system. But for more advanced cases, we should codify them in the
registry itself.

To annotate an artifact, use `gto annotate`. GTO writes to an `artifacts.yaml`
file to save this metadata. Feel free to modify the file directly!

```console
$ gto annotate awesome-model --type model --path s3://awesome/model.pkl
```

```yaml
# artifacts.yaml
awesome-model:
  type: model
  path: "s3://awesome/model.pkl"
```

> Don't forget to commit `artifacts.yaml` with Git to associate it with the
> latest artifact version and stage in any copy of the repo.

By default GTO saves artifact as `virtual`. Use the `--must_exist` flag to tell
GTO the artifact file is committed to Git.

<details summary="Virtual vs. Physical artifacts">

- Physical files/directories are committed to the repo. When you register a new
  version or assign a stage to it, Git guarantees that it's immutable -- you can
  return a year later and get the same artifact by providing a version.

- Virtual artifacts could be an external path (e.g. `s3://mybucket/myfile`) or a
  local path to a metafile representing an externally stored artifact file (as
  [with DVC](https://dvc.org/doc/start/data-management)). In this case, GTO
  can't pin versions to a physical state of the artifact and guarantee it's
  immutability later, e.g. if `s3://mybucket/myfile` changes the registry won't
  know it, nor have a way to recover the original file.

> In future versions, we will support additional enrichments: useful information
> that other tools like [DVC](https://dvc.org/) and [MLEM](https://mlem.ai/) can
> provide about the artifacts. This will allow treating DVC repo outputs as
> usual artifacts instead of `virtual` ones.

</details>

## Using the registry locally

Let's look at the usage of the `gto show` and `gto history`.

### Show the current state

This is the entire state of the registry: all artifacts, their latest versions,
and the greatest versions for each stage.

```console
$ gto show
╒═══════════════╤══════════╤════════╤═════════╤════════════╕
│ name          │ latest   │ #dev   │ #prod   │ #staging   │
╞═══════════════╪══════════╪════════╪═════════╪════════════╡
│ churn         │ v3.1.0   │ v3.0.0 │ v3.0.0  │ v3.1.0     │
│ segment       │ v0.4.1   │ v0.4.1 │ -       │ -          │
│ cv-class      │ v0.1.13  │ -      │ -       │ -          │
│ awesome-model │ v0.0.1   │ -      │ v0.0.1  │ -          │
╘═══════════════╧══════════╧════════╧═════════╧════════════╛
```

Here we'll see both artifacts that have Git tags only and those annotated in
`artifacts.yaml`. Use `--all-branches` or `--all-commits` to read
`artifacts.yaml` from more commits than just `HEAD`.

Add an artifact name to print all of its versions instead:

```console
$ gto show churn
╒════════════╤═══════════╤═══════════╤═════════════════════╤═══════════════════╤══════════════╕
│ artifact   │ version   │ stage     │ created_at          │ author            │ ref          │
╞════════════╪═══════════╪═══════════╪═════════════════════╪═══════════════════╪══════════════╡
│ churn      │ v3.1.0    │ staging   │ 2022-07-13 15:25:41 │ Alexander Guschin │ churn@v3.1.0 │
│ churn      │ v3.0.0    │ prod, dev │ 2022-07-09 00:19:01 │ Alexander Guschin │ churn@v3.0.0 │
╘════════════╧═══════════╧═══════════╧═════════════════════╧═══════════════════╧══════════════╛
```

#### Enabling Kanban workflow

In some cases, you would like to have a latest stage for an artifact version to
replace all the previous stages. In this case the version will have a single
stage. This resembles Kanban workflow, when you "move" your artifact version
from one column ("stage-1") to another ("stage-2"). This is how MLFlow and some
other Model Registries work.

To achieve this, you can use `--last-stage` flag (or `--ls` for short):

```console
$ gto show --ls
╒═══════════════╤══════════╤════════╤═════════╤════════════╕
│ name          │ latest   │ #dev   │ #prod   │ #staging   │
╞═══════════════╪══════════╪════════╪═════════╪════════════╡
│ churn         │ v3.1.0   │ -      │ v3.0.0  │ v3.1.0     │
│ segment       │ v0.4.1   │ v0.4.1 │ -       │ -          │
│ cv-class      │ v0.1.13  │ -      │ -       │ -          │
│ awesome-model │ v0.0.1   │ -      │ v0.0.1  │ -          │
╘═══════════════╧══════════╧════════╧═════════╧════════════╛
```

### See the history of an artifact

`gto history` will print a journal of the events that happened to an artifact.
This allows you to audit the changes.

```console
$ gto history churn
╒═════════════════════╤════════════╤══════════════╤═══════════╤═════════╤══════════╤═══════════════════╕
│ timestamp           │ artifact   │ event        │ version   │ stage   │ commit   │ author            │
╞═════════════════════╪════════════╪══════════════╪═══════════╪═════════╪══════════╪═══════════════════╡
│ 2022-07-17 02:45:41 │ churn      │ assignment    │ v3.0.0    │ prod    │ 631520b  │ Alexander Guschin │
│ 2022-07-15 22:59:01 │ churn      │ assignment    │ v3.1.0    │ staging │ be340cc  │ Alexander Guschin │
│ 2022-07-14 19:12:21 │ churn      │ assignment    │ v3.0.0    │ dev     │ 631520b  │ Alexander Guschin │
│ 2022-07-13 15:25:41 │ churn      │ registration │ v3.1.0    │ -       │ be340cc  │ Alexander Guschin │
│ 2022-07-12 11:39:01 │ churn      │ commit       │ -         │ -       │ be340cc  │ Alexander Guschin │
│ 2022-07-09 00:19:01 │ churn      │ registration │ v3.0.0    │ -       │ 631520b  │ Alexander Guschin │
│ 2022-07-07 20:32:21 │ churn      │ commit       │ -         │ -       │ 631520b  │ Alexander Guschin │
╘═════════════════════╧════════════╧══════════════╧═══════════╧═════════╧══════════╧═══════════════════╛
```

## Consuming the registry downstream

Let's look at integrating with GTO via Git as well as using the `gto check-ref`,
`gto latest`, `gto which`, and `gto describe` utility commands downstream.

### Act on new versions and stage assignments in CI

To act upon annotations (Git tags), you can create simple CI workflow. With
[GitHub Actions](https://github.com/features/actions) for example, it can look
like this:

```yaml
name: Act on versions or stage assignments of the "churn" actifact
on:
  push:
    tags:
      - "churn*"
```

When CI is triggered, you can use the Git reference to determine the version of
the artifact. In GH Actions, you can use the `GITHUB_REF` environment variable
(check out our
[example workflow](/gto/blob/main/.github/workflows/check-test-release.yml)).
You can parse tags manually or use `gto check-ref`:

```console
$ gto check-ref awesome-model@v0.0.1
{
    "version": {
        "awesome-model": {
            "artifact": "awesome-model",
            "name": "v0.0.1",
            "created_at": "2022-04-21T17:39:14",
            "author": "Alexander Guschin",
            "commit_hexsha": "26cafe958dca65d726b3c9023fbae71ed259b566",
            "discovered": false,
            "tag": "awesome-model@v0.0.1",
        }
    },
    "stage": {}
}
```

### Getting the right version

To get the latest artifact version, its path, and Git reference, use
`gto latest`:

```console
$ gto latest churn
v3.1.0

$ gto latest churn --ref
churn@v3.1.0
```

To get the version that is currently assigned to an environment (stage), use
`gto which`:

```console
$ gto which churn dev
v3.0.0

$ gto which churn dev --ref
churn#dev#1
```

<details summary="Kanban workflow">

If you prefer Kanban workflow described above, you could use `--last` flag. This
will take into account the last stage for a version only.

```console
$ gto which churn dev --last
```

Since the last stage for version `v3.0.0` was `prod`, this doesn't return
anything.

</details>

To get details about an artifact (from `artifacts.yaml`) use `gto describe`:

```console
$ gto describe churn
```

```yaml
{ "type": "model", "path": "models/churn.pkl", "virtual": false }
```

> The output is in JSON format for ease of parsing programatically.

## Configuration

To configure GTO, use file `.gto` in the root of your repo or use environment
variables (note the `GTO_` prefix):

```ini
# .gto config file
types: [model, dataset]  # list of allowed Types
stages: [dev, stage, prod]  # list of allowed Stages
```

When allowed Stages or Types are specified, GTO will check commands you run and
error out if you provided a value that doesn't exist in the config. Note, that
GTO applies the config from the workspace, so if want to apply the config from
`main` branch, you need to check out it first with `git checkout main`.

```console
$ GTO_EMOJIS=false gto show
```

## Setup GTO development environment

### 1. Clone this repository

```console
$ git clone git@github.com:iterative/gto.git
$ cd gto
```

### 2. Create virtual environment named `venv`

```console
$ python3 -m venv venv
$ source venv/bin/activate
```

Install python libraries

```console
$ pip install --upgrade pip setuptools wheel ".[tests]"
```

### 3. Run

```console
$ pytest --basetemp=pytest-basetemp
```

This will create `pytest-basetemp/` directory with some fixtures that can serve
as examples.

Notably, check out this dir:

```console
$ cd pytest-basetemp/test_api0/
$ gto show -v
```

The code that generates this folder could be found
[in this fixture](https://github.com/iterative/gto/blob/main/tests/conftest.py#L58).

To continue experimenting, call `gto --help`
