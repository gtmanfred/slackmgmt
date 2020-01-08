#!/bin/bash
python3 -m poetry build
if which podman &>/dev/null; then
    podman build -t slackmgmt .
else
    docker buildd -t slackmgmt .
fi
