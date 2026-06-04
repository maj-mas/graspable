# graspable
`graspable` aims to provide users with a YAML-based set of python tools to set up and run atomic structure calculations using the `GRASP` package (see below). `graspable` is currently under early development.


# Installation
TODO
```
$ pip install graspable
```

# Example
TODO

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


# GRASP
The General Relativistic Atomic Structure Package (`GRASP`) is described by its authors in the following publication:
> C. Froese Fischer, G. Gaigalas, P. Jönsson, J. Bieroń, "GRASP2018 — a Fortran 95 version of the General Relativistic Atomic Structure Package", Computer Physics Communications, 237, 184-187 (2018), https://doi.org/10.1016/j.cpc.2018.10.032

Its source code is distributed under MIT license at https://github.com/compas/grasp .

The developers of graspable are not affiliated with the authors and maintainers of GRASP.
