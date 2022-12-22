from pathlib import Path

from setuptools import find_packages, setup

install_requires = [
    "gitpython",
    "typer>=0.4.1",
    "rich",
    "pydantic",
    "ruamel.yaml",
    "semver==3.0.0.dev4",
    "entrypoints",
    "tabulate>=0.8.10",
    "funcy",
]


tests = [
    "pytest",
    "pytest-cov",
    "pytest-lazy-fixture==0.6.3",
    "pytest-mock",
    "pylint<2.14",
    # we use this to suppress pytest-related false positives in our tests.
    "pylint-pytest",
    # we use this to suppress some messages in tests, eg: foo/bar naming,
    # and, protected method calls in our tests
    "pylint-plugin-utils",
    "freezegun",
    "types-freezegun",
]


setup_args = dict(  # noqa: C408
    name="gto",
    use_scm_version=True,
    setup_requires=["setuptools_scm", "fastentrypoints>=0.12"],
    description="Version and deploy your models following GitOps principles",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf8"),
    long_description_content_type="text/markdown",
    author="Alexander Guschin",
    author_email="aguschin@iterative.ai",
    download_url="https://github.com/iterative/gto",
    license="Apache License 2.0",
    install_requires=install_requires,
    extras_require={"tests": tests},
    keywords="git repo repository artifact registry developer-tools collaboration",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    entry_points={
        "console_scripts": ["gto = gto.cli:app"],
        "gto.enrichment": [
            # "mlem = gto.ext_mlem:MlemEnrichment",
            # "dvc = gto.ext_dvc:DVCEnrichment",
            # "cli = gto.ext:CLIEnrichment",
            "gto = gto.index:GTOEnrichment",
        ],
    },
    zip_safe=False,
)

if __name__ == "__main__":
    setup(**setup_args)
