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
pip install --upgrade pip setuptools wheel .
```

**3. Run**

```bash
bash showcase.sh
```

This will create `demo` branch and tags. Please don't push them back to this repo :)
To continue experimenting, call
```bash
gto --help
```
to see functionality and read through demo example.
For this to work, you need to be locally in this repo.
Working with remote repo isn't supported yet.
