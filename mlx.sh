#!/bin/bash
# clean-env runner for the mlx venv (Hermes leaks PYTHONPATH with a py3.14 numpy)
cd ~/architect && env -u PYTHONPATH -u VIRTUAL_ENV HF_HOME=~/architect/models/hf .venv-mlx/bin/python "$@"
