#!/bin/bash -eu (source'd file)

die() {
    echo "FATAL: $*" >&2
    exit 1
}
