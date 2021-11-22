from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py

install_requires = [
    "gitpython",
    "click",
    "pandas",
    "ipython",
    "numpy",
]


setup_args = dict(  # noqa: C408
    name="gitops",
    version="0.0.1",
    description="Version and deploy your models following GitOps principles",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf8"),
    author="Alexander Guschin",
    author_email="aguschin@iterative.ai",
    download_url="https://github.com/iterative/gitops-object-registry",
    license="Apache License 2.0",
    install_requires=install_requires,
    keywords="git gitops mlops object registry developer-tools collaboration",
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
        "console_scripts": ["gitops = gitops.cli:cli"],
    },
    cmdclass={"build_py": build_py},
    zip_safe=False,
)

if __name__ == "__main__":
    setup(**setup_args)
