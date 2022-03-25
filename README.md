# GTO

Great Tool Ops. Turn your Git Repo into Artifact Registry:
* Index files in repo as artifacts to make them visible for others
* Register new versions of artifacts marking significant changes to them
* Promote versions to environments to signal downstream systems to act
* Act on new versions and promotions in CI
* [WIP] Add enrichments that will add more information about the artifacts

To turn your repo into an artifact registry, you only need to `pip install` this package. Indexing, versioning and promoting are done with Git using files, commits, tags and branches. To use the artifact registry, you also need this package only.

The tool is created to be used both in CLI and in Python. The README will cover CLI part, but for all commands there are Python API counterparts in `gto.api` module.

## Artifacts

To add new artifact or remove the existing ones, run `gto add` or `gto rm`:

```
$ gto add model simple-nn models/neural-network.pkl --virtual

$ gto add --help
Usage: gto add [OPTIONS] TYPE NAME PATH

  Register new artifact (add it to the Index)

Options:
  -v, --verbose
  -r, --repo TEXT  Repository to use  [default: .]
  --virtual        Virtual artifact that wasn't committed to Git
  --help           Show this message and exit.
```

You could also modify `artifacts.yaml` file directly.

There are two types of artifacts in GTO:
1. Files/folders committed to the repo. When you register a new version or promote it to env, Git guarantees that it's immutable. You can return to your repo a year later and be able to get 100% the same artifact by providing the same version.
2. `Virtual` artifacts. This could be an external path, e.g. `s3://mybucket/myfile` or a local path if the file wasn't committed (as in case with DVC). In this case GTO can't pin the current physical state of the artifact and guarantee it's immutability. If `s3://mybucket/myfile` changes, you won't have any way neither retrieve, nor understand it's different now than it was before when you registered that artifact version.

In future versions, we will add enrichments (useful information other tools like DVC and MLEM can provide about the artifacts). This will allow treating files versioned with DVC and DVC PL outputs as usual artifacts instead `virtual` ones.

## Versioning

After adding an artifact and committing modified `artifacts.yaml`, you can start creating new versions of it. You usually use those to mark significant changes to the artifact.

```
$ gto register simple-nn HEAD --version v1.0.0

$ gto register --help
Usage: gto register [OPTIONS] NAME REF

  Tag the object with a version (git tags)

Options:
  -v, --verbose
  -r, --repo TEXT        Repository to use  [default: .]
  --version, --ver TEXT  Version to promote
  -b, --bump TEXT        The exact part to use when bumping a version
  --help                 Show this message and exit.
```

If you want to deprecate specific version, use `gto deprecate`.

## Promoting

You could also promote a specific artifact version to an environment. You can use that to signal downstream systems to act - for example, redeploy a ML model (your artifact) or update the config file (your artifact).

```
$ gto promote simple-nn prod

$ gto promote --help
Usage: gto promote [OPTIONS] NAME LABEL

  Assign label to specific artifact version

Options:
  -v, --verbose
  -r, --repo TEXT  Repository to use  [default: .]
  --version TEXT   If you provide --ref, this will be used to name new version
  --ref TEXT
  --help           Show this message and exit.
```

## Using the registry

Let's see what are the commands that help us use the registry. Let's clone the example repo first:
```
$ git clone git@github.com:iterative/gto-example.git
$ cd gto-example
```

### Show the actual state

This is the actual state of the registry: all artifacts, their latest versions, and what is promoted to envs right now.

```
$ gto show
╒══════════════╤═══════════╤══════════════════╤═══════════════╕
│ name         │ version   │ env/production   │ env/staging   │
╞══════════════╪═══════════╪══════════════════╪═══════════════╡
│ nn           │ v0.0.1    │ -                │ v0.0.1        │
│ rf           │ v1.0.1    │ v1.0.0           │ v1.0.1        │
│ features-dvc │ -         │ -                │ -             │
╘══════════════╧═══════════╧══════════════════╧═══════════════╛
```

### Audit the registration and promotion

`gto audit` will print all registered versions of the artifact and all versions promoted to environments. This will help you to understand what was happening with the artifact.

```
$ gto audit --name rf

=== Registration audit trail ===
╒═════════════════════╤════════╤═══════════╤══════════════╤══════════╤═══════════════════╕
│ timestamp           │ name   │ version   │ deprecated   │ commit   │ author            │
╞═════════════════════╪════════╪═══════════╪══════════════╪══════════╪═══════════════════╡
│ 2022-03-18 12:10:15 │ rf     │ v1.0.0    │ -            │ 5eaf15a  │ Alexander Guschin │
│ 2022-03-18 12:11:21 │ rf     │ v1.0.1    │ -            │ 9fbb866  │ Alexander Guschin │
╘═════════════════════╧════════╧═══════════╧══════════════╧══════════╧═══════════════════╛

=== Promotion audit trail ===
╒═════════════════════╤════════╤════════════╤═══════════╤══════════════╤══════════╤═══════════════════╕
│ timestamp           │ name   │ label      │ version   │ deprecated   │ commit   │ author            │
╞═════════════════════╪════════╪════════════╪═══════════╪══════════════╪══════════╪═══════════════════╡
│ 2022-03-18 12:12:27 │ rf     │ production │ v1.0.0    │ -            │ 5eaf15a  │ Alexander Guschin │
│ 2022-03-18 12:13:30 │ rf     │ staging    │ v1.0.1    │ -            │ 9fbb866  │ Alexander Guschin │
│ 2022-03-18 12:14:33 │ rf     │ production │ v1.0.1    │ -            │ 9fbb866  │ Alexander Guschin │
│ 2022-03-18 12:15:37 │ rf     │ production │ v1.0.0    │ -            │ 5eaf15a  │ Alexander Guschin │
╘═════════════════════╧════════╧════════════╧═══════════╧══════════════╧══════════╧═══════════════════╛
```

### See the history of an artifact

Another way to achieve the same is by using `gto history` command:

```
$ gto history --name rf
╒═════════════════════╤════════╤══════════════╤═══════════╤════════════╤══════════════╤══════════╤═══════════════════╕
│ timestamp           │ name   │ event        │ version   │ label      │ deprecated   │ commit   │ author            │
╞═════════════════════╪════════╪══════════════╪═══════════╪════════════╪══════════════╪══════════╪═══════════════════╡
│ 2022-03-18 12:10:12 │ rf     │ commit       │ -         │ -          │ -            │ 5eaf15a  │ Alexander Guschin │
│ 2022-03-18 12:10:15 │ rf     │ registration │ v1.0.0    │ -          │ -            │ 5eaf15a  │ Alexander Guschin │
│ 2022-03-18 12:11:18 │ rf     │ commit       │ -         │ -          │ -            │ 9fbb866  │ Alexander Guschin │
│ 2022-03-18 12:11:21 │ rf     │ registration │ v1.0.1    │ -          │ -            │ 9fbb866  │ Alexander Guschin │
│ 2022-03-18 12:12:27 │ rf     │ promotion    │ v1.0.0    │ production │ -            │ 5eaf15a  │ Alexander Guschin │
│ 2022-03-18 12:13:30 │ rf     │ promotion    │ v1.0.1    │ staging    │ -            │ 9fbb866  │ Alexander Guschin │
│ 2022-03-18 12:14:33 │ rf     │ promotion    │ v1.0.1    │ production │ -            │ 9fbb866  │ Alexander Guschin │
│ 2022-03-18 12:15:37 │ rf     │ promotion    │ v1.0.0    │ production │ -            │ 5eaf15a  │ Alexander Guschin │
╘═════════════════════╧════════╧══════════════╧═══════════╧════════════╧══════════════╧══════════╧═══════════════════╛
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
    creation_date: '2022-03-18T12:11:21'
    deprecated_date: null
    name: v1.0.1
```

### [WIP] Getting right versions in downstream systems

To get the latest artifact version, run:

```
$ gto latest rf
v1.0.1
```

To get the version that is currently promoted to environment, run:

```
$ gto which rf production
v1.0.0
```

To download artifacts that are stored with DVC or outside of repo, e.g. in `s3://` or in DVC cache, you'll need DVC or aws CLI.

## Configuration

You can write configuration in `.gto` file in the root of your repo or use environment variables like this (note the `GTO_` prefix):
```shell
GTO_VERSION_BASE=tag gto show
```

The default config written to `.gto` file will look like this (comments are there to help clarify the settings meaning and valid values):
```
index: artifacts.yaml
type_allowed: []  # list of allowed types
version_base: tag  # or commit
version_convention: numbers  # or semver
version_required_for_env: true  # if false, registering a version isn't required to promote to an environment
env_base: tag  # or branch
env_allowed: []  # list of allowed environments to promote to. Make sense for env_base=tag only.
env_branch_mapping: {}  # map of branch names to environment names. Makes sense for env_base=branch only.
```

If some list/dict should allow something but it's empty, that means that all values are allowed.

### Some example configs (skipping default values)

```
type_allowed: [model, dataset]
version_convention: semver
env_allowed: [dev, test, prod]
```

In this setup you create versions and promote them with git tags (those are defaults). This would be a typical setup when you need both to register versions and promote them to envs, and your requirement is to create a version first before promoting the artifact from specific commit to the env (`gto promote` will automatically create a version for you in that case). It limits allowed types and envs and requires you to version your models with SemVer (v1.2.3 as opposed to v1 that is called Numbers in settings).

```
type_allowed: [model, dataset]
version_convention: semver
version_required_for_env: false
env_allowed: [dev, test, prod]
```

This setup has a single difference from the previous one. To promote a model to the environment, it doesn't require you to create a SemVer version. To indicate, which version was promoted, GTO will use a commit hexsha. That effectively means that registering and promoting are decoupled - you can do them independently. `gto show`, `gto audit`, `gto history` showcasing promotions will show SemVer when it's available, and commit hexsha when it's not.

```
version_base: commit
env_allowed: [dev, test, prod]
```

In this setup each commit counts as a version for artifact (it's only required for that artifact to exist in `artifacts.yaml` in those commits). You cannot create versions explicitly with `gto register` right now, because this requires to actually create PR/make a commit to the selected branch and it's not implemented yet. As for versions, you have a whitelist of allowed values. Because each commit is a version, you don't need to create a version before promoting. In fact it is similar to specifying `version_required_for_env: false`.

```
env_base: branch
env_branch_mapping:
    master: prod
    develop: dev
```

In this setup artifact version is assumed to be promoted in `prod` if it's committed in `master` and is the latest version in that branch. Because the default is `version_base: tag`, running `gto promote` will register new artifact version - and this at the same time will promote the artifact to the environment from `env_branch_mapping`. If you register a version in a branch that doesn't exist in `env_branch_mapping`, the promotion won't happen.

```
version_base: commit
env_base: branch
```

In this setup you cannot create versions explicitly with `gto register`, because each commit counts as a version for artifact (it's only required for that artifact to exist in `artifacts.yaml` in those commits) and you would need to actually create PR/make a commit to the selected branch. Likewise, you cannot promote to envs with `gto promote` because it's not implemented yet and exact way to do that is unclear - e.g. this would require to create a PR or direct commit that updates the artifact. I guess we should implement all of these in the future. For now this setup allows you to manage artifacts with `gto add` / `gto rm` and see the state of your repo `gto show`, `gto audit`, `gto history`. Finally, because `env_branch_mapping` is not specified, GTO will take into account all branches that have `artifacts.yaml` in them.

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
