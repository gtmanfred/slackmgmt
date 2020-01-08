#!/bin/bash
python3 -m poetry build
docker build -t slackmgmt .
