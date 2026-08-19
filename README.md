# graspable
`graspable` aims to provide users with a YAML-based set of python tools to set up and run atomic structure calculations using the `GRASP` package (see below). `graspable` is currently under early development.


# Installation
In the future, `graspable` will be available on the Python package index. For now, `graspable` can be installed by cloning the repo, ensuring all dependencies are installed and invoking
```
$ pip install .
```
from the project's root.

# Examples
Multiple example configuration files are included under `example_configs`. To start a calculation, invoke
```
$ graspable -c=path/to/config.yaml
```

# Documentation
The documentation for `graspable` is unfinished. In the future, it will be included with the source and also available on the web.

# Development tools
Colleagues who wish to contribute by submitting pull requests to `graspable` require the following tools:

## `poetry`
`poetry` manages dependencies and the package description file `pyproject.toml` among other things. It can be installed as follows:
```
$ curl -sSL https://install.python-poetry.org | python3 -
```
`poetry` is automatically invoked at every commit using the pre-commit hooks:

## `pre-commit`
`pre-commit` runs numerous checks defined in `.pre-commit-config.yaml` before accepting commits. It can be installed as follows:
```
$ pip install pre-commit
$ pre-commit install # run in project top directory
```

## `sphinx`
`sphinx` is used to build the documentation:
```
$ pip install sphinx
```


# GRASP
The General Relativistic Atomic Structure Package (`GRASP`) is described by its authors in the following publication:
> C. Froese Fischer, G. Gaigalas, P. Jönsson, J. Bieroń, "GRASP2018 — a Fortran 95 version of the General Relativistic Atomic Structure Package", Computer Physics Communications, 237, 184-187 (2018), https://doi.org/10.1016/j.cpc.2018.10.032

Its source code is distributed under MIT licence at https://github.com/compas/grasp.

The developers of `graspable` are not affiliated with the authors and maintainers of `GRASP`.

# Acknowledgement
Parts of the configuration file structure were inspired by the Python interface for the `pCI` atomic structure package:
> C. Cheung, M. G. Kozlov, S. G. Porsev, M. S. Safronova, I. I. Tupitsyn, and A. I. Bondarev, pci: A parallel configuration interaction software package for high-precision atomic structure calculations, Computer Physics Communications 308, 109463 (2025), https://doi.org/10.1016/j.cpc.2024.109463

Its source code is distributed under GPL-3.0 licence at https://github.com/ud-pci/pCI.

The developers of `graspable` are not affiliated with the authors and maintainers of `pCI`.

# Disclaimer
`graspable` is human written software, no machine-generated code was used in its development.
