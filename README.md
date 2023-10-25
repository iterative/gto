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

GTO works by creating annotated Git tags in a standard format.

💡 Together with [DVC](https://dvc.org), GTO serves as a backbone for Git-based
[Iterative Studio Model Registry](https://dvc.org/doc/studio/user-guide/model-registry/what-is-a-model-registry).

## Installation

GTO requires Python 3. It works on any OS.

```console
$ pip install gto
```

This will install the `gto`
[command-line interface](https://dvc.org/doc/gto/command-reference) (CLI) and
make the Python API available for use in code.

## Getting started

To Get Started, please head to [GTO docs](https://dvc.org/doc/gto/get-started).

## Contributing

Contributions are welcome! Please see our
[Contributing Guide](https://dvc.org/doc/contributing/core) for more details.

Check out the
[DVC weekly board](https://github.com/orgs/iterative/projects/189)
to learn about what we do, and about the exciting new functionality that is
going to be added soon.

Thanks to all our contributors!

<details>

How to setup GTO development environment

1. Clone this repository

```console
$ git clone git@github.com:iterative/gto.git
$ cd gto
```

2. Create virtual environment named `venv`

```console
$ python3 -m venv .venv
$ source .venv/bin/activate
```

Install python libraries

```console
$ pip install --upgrade pip ".[tests]"
```

3. Run

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
[in this fixture](https://github.com/iterative/gto/blob/main/tests/conftest.py).

To continue experimenting, call `gto --help`

</details>

## Copyright

This project is distributed under the Apache license version 2.0 (see the
LICENSE file in the project root).

By submitting a pull request to this project, you agree to license your
contribution under the Apache license version 2.0 to this project.
