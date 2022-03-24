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

Some example configs (skipping default values):

```
type_allowed: [model, dataset]
version_convention: semver
version_required_for_env: false
env_allowed: [dev, test, prod]
```

```
version_base: commit
version_required_for_env: true
env_base: branch
env_branch_mapping:
    master: prod
    develop: dev
```


## See example repo**

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
