from pathlib import Path

from setuptools import find_packages, setup

install_requires = [
    "scmrepo>=3,<4",
    "typer>=0.4.1",
    "rich",
    # pydantic.v1.parse_obj is broken in ==2.0.0:
    # https://github.com/pydantic/pydantic/issues/6361
    "pydantic>=1.9.0,<3,!=2.0.0",
    "ruamel.yaml",
    "semver>=3.0.0",
    "entrypoints",
    "tabulate>=0.8.10",
    "funcy",
]


tests = [
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "pytest-test-utils",
    "pylint==3.0.3",
    # we use this to suppress some messages in tests, eg: foo/bar naming,
    # and, protected method calls in our tests
    "pylint-plugin-utils",
    "freezegun",
    "types-freezegun",
]


setup_args = {
    "name": "gto",
    "use_scm_version": True,
    "setup_requires": ["setuptools_scm", "fastentrypoints>=0.12"],
    "description": "Version and deploy your models following GitOps principles",
    "long_description": (Path(__file__).parent / "README.md").read_text(
        encoding="utf8"
    ),
    "long_description_content_type": "text/markdown",
    "author": "Alexander Guschin",
    "author_email": "aguschin@iterative.ai",
    "download_url": "https://github.com/iterative/gto",
    "license": "Apache License 2.0",
    "install_requires": install_requires,
    "extras_require": {"tests": tests},
    "keywords": "git repo repository artifact registry developer-tools collaboration",
    "python_requires": ">=3.9",
    "classifiers": [
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    "packages": find_packages(exclude=["tests"]),
    "include_package_data": True,
    "entry_points": {
        "console_scripts": ["gto = gto.cli:app"],
        "gto.enrichment": [
            "gto = gto.index:GTOEnrichment",
        ],
    },
    "zip_safe": False,
}

if __name__ == "__main__":
    setup(**setup_args)
