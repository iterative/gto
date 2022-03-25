# GTO

Great Tool Ops. Turn your Git Repo into Artifact Registry:
* Index files in repo as artifacts to make them visible for others
* Register new versions of artifacts marking significant changes to them
* Promote versions to environments to signal downstream systems to act
* Act on new versions and promotions in CI
* [WIP] Add enrichments that will add more information about the artifacts

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

## See example repo

Check out the example repo:
https://github.com/iterative/gto-example
read README in it and try it out

## To try out the latest version

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
