[![Check, test and release](https://github.com/iterative/gto/actions/workflows/check-test-release.yml/badge.svg)](https://github.com/iterative/gto/actions/workflows/check-test-release.yml)
[![Codecov](https://codecov.io/gh/iterative/gto/branch/main/graph/badge.svg?token=NXT11717BG)](https://codecov.io/gh/iterative/gto)
[![PyPi](https://img.shields.io/pypi/v/gto.svg?label=pip&logo=PyPI&logoColor=white)](https://pypi.org/project/gto)

# GTO

Git Tag Ops. Turn your Git repository into an Artifact Registry:

* Register new versions of artifacts by marking significant changes to them
* Promote certain versions to signal downstream systems to act
* Attach additional information about your artifact with Enrichments
* Act on new versions and promotions in CI/CD

To turn any data science repo into an artifact registry, you only need to `pip install` this package.
GTO versions and promotes artifacts by creating special Git tags.
To use the artifact registry, you also need this package only.

This tool can be used both as CLI and in Python code.
The README will cover CLI usage, but for every command there is a Python API counterpart in the `gto.api` module.

## Versioning

To register new version of artifact, you can use `gto register` command. You usually use those to mark significant changes to the artifact. Running `gto register` creates a special git tag.

```
$ gto register simple-nn HEAD --version v1.0.0
```

This will create git tag `rf@v1.0.0`.

## Promoting

You could also promote a specific artifact version to Stage. You can use that to signal downstream systems to act - for example, redeploy a ML model (if your artifact is a model) or update the some special file on server (if your artifact is a file).

```
$ gto promote simple-nn prod
```

This creates git tag `rf#prod-N`.

There are two notations used for git tags in promotion:
- simple: `rf#prod`
- incremental: `rf#prod-N`

Incremental is the default one and we suggest you use it when possible. The benefit of using it is that you don't have to delete git tags (with simple notation you'll need to delete them because you can't have two tags with the same name). This will keep the history of your promotions.

## Artifacts

So far we registered some artifacts, but we still didn't specify nowhere `type` of this artifact (dataset, model, something else) and `path` to it.
To add enrichment for artifact or remove the existing one, run `gto add` or `gto rm`:

```
$ gto add model simple-nn models/neural-network.pkl --virtual
```

You could also modify `artifacts.yaml` file directly.

There are two types of artifacts in GTO:
1. Files/folders committed to the repo. When you register a new version or promote it to stage, Git guarantees that it's immutable. You can return to your repo a year later and be able to get 100% the same artifact by providing the same version.
2. `Virtual` artifacts. This could be an external path, e.g. `s3://mybucket/myfile` or a local path if the file wasn't committed (as in case with DVC). In this case GTO can't pin the current physical state of the artifact and guarantee it's immutability. If `s3://mybucket/myfile` changes, you won't have any way neither retrieve, nor understand it's different now than it was before when you registered that artifact version.

In future versions, we will add enrichments (useful information other tools like DVC and MLEM can provide about the artifacts). This will allow treating files versioned with DVC and DVC PL outputs as usual artifacts instead `virtual` ones.

## Using the registry

Let's see what are the commands that help us use the registry. Let's clone the example repo first:
```
$ git clone git@github.com:iterative/gto-example.git
$ cd gto-example
```

### Show the actual state

This is the actual state of the registry: all artifacts, their latest versions, and what is promoted to stages right now.

```
$ gto show
╒════════╤═══════════╤═════════════════╤════════════════════╕
│ name   │ version   │ stage/staging   │ stage/production   │
╞════════╪═══════════╪═════════════════╪════════════════════╡
│ nn     │ v0.0.1    │ v0.0.1          │ -                  │
│ rf     │ v1.2.4    │ -               │ v1.2.4             │
╘════════╧═══════════╧═════════════════╧════════════════════╛
```

Use `--all-branches` or `--all-commits` to read `artifacts.yaml` from more commits than just HEAD.

Add artifact name to print versions of that artifact:

```
$ gto show rf
╒════════════╤════════╤════════════╤═════════════════════╤═══════════════════╤═════════════════╤══════════════╤═══════════════╕
│ artifact   │ name   │ stage      │ created_at       │ author            │ commit_hexsha   │ discovered   │ enrichments   │
╞════════════╪════════╪════════════╪═════════════════════╪═══════════════════╪═════════════════╪══════════════╪═══════════════╡
│ rf         │ v1.2.3 │ production │ 2022-04-11 21:51:56 │ Alexander Guschin │ d1d9736         │ False        │ ['gto']       │
│ rf         │ v1.2.4 │ production │ 2022-04-11 21:51:57 │ Alexander Guschin │ 16b7b77         │ False        │ ['gto']       │
╘════════════╧════════╧════════════╧═════════════════════╧═══════════════════╧═════════════════╧══════════════╧═══════════════╛
```

### See the history of an artifact

`gto history` will print all registered versions of the artifact and all versions promoted to environments. This will help you to understand what was happening with the artifact.

```
$ gto history rf
╒═════════════════════╤════════╤══════════════╤═══════════╤════════════╤══════════╤═══════════════════╕
│ timestamp           │ name   │ event        │ version   │ stage      │ commit   │ author            │
╞═════════════════════╪════════╪══════════════╪═══════════╪════════════╪══════════╪═══════════════════╡
│ 2022-04-11 21:51:56 │ rf     │ commit       │ -         │ -          │ d1d9736  │ Alexander Guschin │
│ 2022-04-11 21:51:56 │ rf     │ registration │ v1.2.3    │ -          │ d1d9736  │ Alexander Guschin │
│ 2022-04-11 21:51:57 │ rf     │ commit       │ -         │ -          │ 16b7b77  │ Alexander Guschin │
│ 2022-04-11 21:51:57 │ rf     │ registration │ v1.2.4    │ -          │ 16b7b77  │ Alexander Guschin │
│ 2022-04-11 21:51:57 │ rf     │ promotion    │ v1.2.3    │ production │ d1d9736  │ Alexander Guschin │
│ 2022-04-11 21:51:58 │ rf     │ promotion    │ v1.2.4    │ staging    │ 16b7b77  │ Alexander Guschin │
│ 2022-04-11 21:51:59 │ rf     │ promotion    │ v1.2.4    │ production │ 16b7b77  │ Alexander Guschin │
│ 2022-04-11 21:52:01 │ rf     │ promotion    │ v1.2.3    │ production │ d1d9736  │ Alexander Guschin │
╘═════════════════════╧════════╧══════════════╧═══════════╧════════════╧══════════╧═══════════════════╛
```

## Act on new versions and promotions in CI

When CI is triggered, you can use the triggering git reference to determine the version of the artifact that was registered or promoted. In GH Actions you can use the `GITHUB_REF` environment variable to determine the version (check out GH Actions workflow in the example repo). You can also do that locally:

```
$ gto check-ref rf@v1.0.1
WARNING:root:Provided ref doesn't exist or it is not a tag that promotes to an environment
env: {}
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
$ gto latest rf --path
models/random-forest.pkl
$ gto latest rf --ref
9fbb8664a4a48575ee5d422e177174f20e460b94
```

To get the version that is currently promoted to environment, run:

```
$ gto which rf production
v1.0.0
$ gto which rf production --path
models/random-forest.pkl
$ gto which rf production --ref
5eaf15a9fbb8664a4a48575ee5d422e177174f20e460b94
```

To download artifacts that are stored with DVC or outside of repo, e.g. in `s3://` or in DVC cache, you'll need DVC or aws CLI.

## Configuration

You can write configuration in `.gto` file in the root of your repo or use environment variables like this (note the `GTO_` prefix):
```shell
GTO_EMOJIS=true gto show
```

The default config written to `.gto` file will look like this (comments are there to help clarify the settings meaning and valid values):
```
type_allowed: []  # list of allowed types
stage_allowed: []  # list of allowed Stages to promote to
```

If a list/dict should allow something but it's empty, that means that all values are allowed.

## Trying it out

### See example repo

Check out the example repo:
https://github.com/iterative/gto-example
read README in it and try it out

### To try out the latest version

#### 1. Clone this repository

```bash
git clone git@github.com:iterative/gto.git
cd gto
```

#### 2. Create virtual environment named `venv`
```bash
python3 -m venv venv
source venv/bin/activate
```
Install python libraries

```bash
pip install --upgrade pip setuptools wheel ".[tests]"
```

#### 3. Run

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
