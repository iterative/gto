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

### Versioning an artifact

Registering a version is usually done to mark significant changes to the
artifact. To release a new version (including the very first one), use
`gto register`.

```console
$ gto register awesome-model HEAD --version v0.0.1
Created git tag 'awesome-model@v0.0.1' that registers a version
```

<details summary="What happens under the hood?">

GTO creates a special Git tag for the artifact version, in a standard format:
`{artifact_name}@{version_number}`.

The version is now associated to the current Git commit (`HEAD`). You can use
another Git commit if you provide it's hexsha as an additional argument, like
`$ gto register awesome-model abc1234`.

</details>

### Assigning a stage to version

To assign an actionable stage for a specific artifact version use the same
`gto assign` command. Stages can mark the artifact readiness for a specific
consumer. You can plug in a real downsteam system via CI/CD or web hooks, e.g.
to redeploy an ML model.

```console
$ gto assign awesome-model --version v0.0.1 --stage prod
Created git tag 'awesome-model#prod#1' that assigns a stage to 'v0.0.1'
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

### Annotating

So far we've seen how to register a new version and assign a stage to an
artifact versions, but we still don't have much information about them. What
about the type of artifact (dataset, model, etc.) or the file path to find it in
the working tree?

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

- Physical files/directories are committed to the repo. When you create a new
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

### Unassigning a stage

Sometimes you need to mark an artifact version no longer ready for a specific
consumer, and maybe signal a downstream system about this. You can use
`gto deprecate` for that:

```console
$ gto deprecate awesome-model v0.0.1 prod
Created git tag 'awesome-model#prod!#2' that unassigns a stage from 'v0.0.1'
```

<details summary="Some details and options">

GTO creates a special Git tag in a standard format:
`{artifact_name}#{stage}!#{e}`.

Note, that later you can create this stage again, if you need to, by calling
`$ gto assign` again.

You also may want to delete the git tag instead of creating a new one. This is
useful if you don't want to keep extra tags in you Git repo, don't need history
and don't want to trigger a CI/CD or another downstream system. For that, you
can use:

```console
$ gto deprecate awesome-model v0.0.1 prod --delete
Deleted git tag 'awesome-model#prod#1' that assigned a stage to 'v0.0.1'
To push the changes upstream, run:
git push origin awesome-model#prod#1 --delete
```

</details>

### Deregister a version

Sometimes you need mark a specific artifact version as a no longer ready for
usage. You could just delete a git tag, but if you want to preserve a history of
the actions, you may again use `gto deprecate`.

```console
$ gto deprecate awesome-model v0.0.1
Created git tag 'awesome-model@v0.0.1!' that deregistered a version.
```

<details summary="Some details and options">

If you want to deregister the version by deleting the Git tags itself, you could
use

```console
$ gto deprecate awesome-model v0.0.1 --delete
Deleted git tag 'awesome-model@v0.0.1' that registered a version.
Deleted git tag 'awesome-model#prod#1' that assigned a stage to 'v0.0.1'.
Deleted git tag 'awesome-model#prod!#2' that unassigned a stage to 'v0.0.1'.
To push the changes upstream, run:
git push origin awesome-model@v0.0.1 awesome-model#prod#1 awesome-model#prod!#2 --delete
```

This includes all Git tags related to the version: a tag that registered it and
all tags that assigned stages to it.

</details>

### Deprecating an artifact

Sometimes you need to need to mark the artifact as "deprecated", usually meaning
it's outdated and will no longer be developed. To do this, you could run:

```console
$ gto deprecate awesome-model
Created Git tag 'awesome-model@deprecated' that deprecates an artifact.
```

<details summary="Some details and options">

With `awesome-model@deprecated` Git tag the artifact will be considered
deprecated until you register a new version or assign a new stage to it after
the deprecation.

If you want to deprecate an artifact by deleting git tags, you'll need to delete
all of them for the artifact. You could do that with

```console
$ gto deprecate awesome-model --delete
Deleted git tag 'awesome-model@v0.0.1' that registered a version.
Deleted git tag 'awesome-model#prod#1' that assigned a stage to 'v0.0.1'.
Deleted git tag 'awesome-model#prod!#2' that unassigned a stage to 'v0.0.1'.
To push the changes upstream, run:
git push origin awesome-model@v0.0.1 awesome-model#prod#1 awesome-model#prod!#2 --delete
```

</details>

## Using the registry locally

Let's look at the usage of the `gto show` and `gto history`.

### Show the current state

This is the entire state of the registry: all artifacts, their latest versions,
and the versions in each stage.

```console
$ gto show
╒═══════════════╤══════════╤════════╤═════════╤════════════╕
│ name          │ latest   │ #dev   │ #prod   │ #staging   │
╞═══════════════╪══════════╪════════╪═════════╪════════════╡
│ churn         │ v3.1.0   │ v3.1.0 │ v3.0.0  │ v3.1.0     │
│ segment       │ v0.4.1   │ v0.4.1 │ -       │ -          │
│ cv-class      │ v0.1.13  │ -      │ -       │ -          │
│ awesome-model │ v0.0.1   │ -      │ v0.0.1  │ -          │
╘═══════════════╧══════════╧════════╧═════════╧════════════╛
```

Here we'll see artifacts that have Git tags or are annotated in
`artifacts.yaml`. The artifacts that have annotation, but have no Git tags, are
considered yet `unregistered` and will be marked with an asterisk, e.g.
`*annotated`. Use `--all-branches` or `--all-commits` to read `artifacts.yaml`
from more commits than just `HEAD`.

Add an artifact name to print all of its versions instead:

```console
$ gto show churn
╒════════════╤═══════════╤══════════════╤═════════════════════╤══════════════╕
│ artifact   │ version   │ stage        │ created_at          │ ref          │
╞════════════╪═══════════╪══════════════╪═════════════════════╪══════════════╡
│ churn      │ v3.1.0    │ dev, staging │ 2022-08-28 16:58:50 │ churn@v3.1.0 │
│ churn      │ v3.0.0    │ prod         │ 2022-08-24 01:52:10 │ churn@v3.0.0 │
╘════════════╧═══════════╧══════════════╧═════════════════════╧══════════════╛
```

Note, that by default, assignments are sorted by the creation time (the latest
assignment wins). You can sort them by Semver with `--sort semver` option (the
greatest version in stage wins).

#### Enabling multiple versions in the same Stage workflow

<details summary="Details">

Note: this functionality is experimental and subject to change. If you find it
useful, please share your feedback in GH issues to help us make it stable.

If you would like to see more than a single version assigned in a stage, use
`--vs` (short for `--versions-per-stage`), e.g. `-1` to show all versions.

```console
$ gto show churn --vs -1
╒════════════╤═══════════╤══════════════╤═════════════════════╤══════════════╕
│ artifact   │ version   │ stage        │ created_at          │ ref          │
╞════════════╪═══════════╪══════════════╪═════════════════════╪══════════════╡
│ churn      │ v3.1.0    │ dev, staging │ 2022-08-28 16:58:50 │ churn@v3.1.0 │
│ churn      │ v3.0.0    │ dev, prod    │ 2022-08-24 01:52:10 │ churn@v3.0.0 │
╘════════════╧═══════════╧══════════════╧═════════════════════╧══════════════╛
```

</details>

#### Enabling Kanban workflow

<details summary="Details">

Note: this functionality is experimental and subject to change. If you find it
useful, please share your feedback in GH issues to help us make it stable.

If you would like the latest stage to replace all the previous stages for an
artifact version, use `--vs` flag combined with `--av`
(`--assignments-per-version` for short):

```console
$ gto show churn --av 1 --vs -1
╒════════════╤═══════════╤═════════╤═════════════════════╤══════════════╕
│ artifact   │ version   │ stage   │ created_at          │ ref          │
╞════════════╪═══════════╪═════════╪═════════════════════╪══════════════╡
│ churn      │ v3.1.0    │ staging │ 2022-08-28 16:58:50 │ churn@v3.1.0 │
│ churn      │ v3.0.0    │ dev     │ 2022-08-24 01:52:10 │ churn@v3.0.0 │
╘════════════╧═══════════╧═════════╧═════════════════════╧══════════════╛
```

In this case the version will always have a single stage (or have no stage at
all). This resembles Kanban workflow, when you "move" your artifact version from
one column ("stage-1") to another ("stage-2"). This is how MLFlow and some other
Model Registries work.

</details>

### See the history of an artifact

`gto history` will print a journal of the events that happened to an artifact.
This allows you to audit the changes.

```console
$ gto history churn
╒═════════════════════╤════════════╤══════════════╤═══════════╤═════════╤══════════╤═════════════════╕
│ timestamp           │ artifact   │ event        │ version   │ stage   │ commit   │ ref             │
╞═════════════════════╪════════════╪══════════════╪═══════════╪═════════╪══════════╪═════════════════╡
│ 2022-09-02 08:05:30 │ churn      │ assignment   │ v3.1.0    │ dev     │ dd5fb99  │ churn#dev#4     │
│ 2022-09-01 04:18:50 │ churn      │ assignment   │ v3.0.0    │ prod    │ 708402b  │ churn#prod#3    │
│ 2022-08-31 00:32:10 │ churn      │ assignment   │ v3.1.0    │ staging │ dd5fb99  │ churn#staging#2 │
│ 2022-08-29 20:45:30 │ churn      │ assignment   │ v3.0.0    │ dev     │ 708402b  │ churn#dev#1     │
│ 2022-08-28 16:58:50 │ churn      │ registration │ v3.1.0    │ -       │ dd5fb99  │ churn@v3.1.0    │
│ 2022-08-27 13:12:10 │ churn      │ commit       │ v3.1.0    │ -       │ dd5fb99  │ dd5fb99         │
│ 2022-08-24 01:52:10 │ churn      │ registration │ v3.0.0    │ -       │ 708402b  │ churn@v3.0.0    │
│ 2022-08-22 22:05:30 │ churn      │ commit       │ v3.0.0    │ -       │ 708402b  │ 708402b         │
╘═════════════════════╧════════════╧══════════════╧═══════════╧═════════╧══════════╧═════════════════╛
```

## Consuming the registry downstream

Let's look at integrating with GTO via Git as well as using the `gto check-ref`,
`gto show`, and `gto describe` utility commands downstream.

### Act on new versions and stage assignments in CI

To act upon registrations and assignments (Git tags), you can create simple CI
workflow. Check out
[the example workflow in `example-gto` repo](https://github.com/iterative/example-gto/blob/main/.github/workflows/gto-act-on-tags.yml).
The workflow uses [the GTO GH Action](https://github.com/iterative/gto-action)
that fetches all Git tags (to correctly interpret the Registry) and finds out
the version of the artifact that was registered, or the stage that was assigned,
so you could use them in later steps of the CI.

### Inspecting Git tags

You can use `gto check-ref` to interpret the Git tag:

```console
$ gto check-ref -r build/example-gto churn#prod#3
✅  Stage "prod" was assigned to version "v3.0.0" of artifact "churn"
```

For machine-consumable format, use `--json` flag or output specific pieces of
information with `--name`, `--version`, `--stage` or `--event`.

### Getting the right version

To get the highest artifact version or Git reference, use
`gto show artifact@greatest`:

```console
$ gto show churn@greatest
╒════════════╤═══════════╤══════════════╤═════════════════════╤══════════════╕
│ artifact   │ version   │ stage        │ created_at          │ ref          │
╞════════════╪═══════════╪══════════════╪═════════════════════╪══════════════╡
│ churn      │ v3.1.0    │ dev, staging │ 2022-08-28 16:58:50 │ churn@v3.1.0 │
╘════════════╧═══════════╧══════════════╧═════════════════════╧══════════════╛

$ gto show churn@greatest --ref
churn@v3.1.0
```

To get the version that is currently assigned to a stage, use
`gto show artifact#stage`:

```console
$ gto show churn#prod
╒════════════╤═══════════╤═════════╤═════════════════════╤══════════════╕
│ artifact   │ version   │ stage   │ created_at          │ ref          │
╞════════════╪═══════════╪═════════╪═════════════════════╪══════════════╡
│ churn      │ v3.0.0    │ prod    │ 2022-08-24 01:52:10 │ churn@v3.0.0 │
╘════════════╧═══════════╧═════════╧═════════════════════╧══════════════╛

$ gto show churn#prod --ref
churn@v3.0.0
```

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
`main` branch, you need to check it out first with `git checkout main`.

```console
$ GTO_EMOJIS=false gto show
```

## Contributing

Contributions are welcome! Please see our
[Contributing Guide](https://mlem.ai/doc/contributing/core) for more details.

Check out the
[MLEM+GTO weekly board](https://github.com/orgs/iterative/projects/322/views/4)
to learn about what we do, and about the exciting new functionality that is
going to be added soon.

Thanks to all our contributors!

### Setup GTO development environment

#### 1. Clone this repository

```console
$ git clone git@github.com:iterative/gto.git
$ cd gto
```

#### 2. Create virtual environment named `venv`

```console
$ python3 -m venv venv
$ source venv/bin/activate
```

Install python libraries

```console
$ pip install --upgrade pip setuptools wheel ".[tests]"
```

#### 3. Run

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

## Copyright

This project is distributed under the Apache license version 2.0 (see the
LICENSE file in the project root).

By submitting a pull request to this project, you agree to license your
contribution under the Apache license version 2.0 to this project.
