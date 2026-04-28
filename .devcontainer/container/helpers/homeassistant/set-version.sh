#!/usr/bin/env bash

read -p 'Set Home Assistant version: ' -r version
uv pip install --system --upgrade homeassistant=="$version"

if [[ -n "$POST_SET_VERSION_HOOK" ]]; then
    "$POST_SET_VERSION_HOOK" "$version"
fi