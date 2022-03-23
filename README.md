# GTO

Great Tool Ops. Turn your Git Repo into Artifact Registry:
* Index your artifacts and add enrichments
* Register artifact versions
* Promote artifacts to environments
* Act on new versions and promotions in CI

**See example repo**

Check out the example repo:
https://github.com/iterative/gto-example
read README in it and try it out

# To try out the latest version

**1. Clone this repository**

```bash
git clone git@github.com:iterative/gto.git
cd gto
```

**2. Create virtual environment named `venv`**
```bash
python3 -m venv venv
source venv/bin/activate
```
Install python libraries

```bash
pip install --upgrade pip setuptools wheel ".[tests]"
```

**3. Run**

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
