#!/usr/bin/env bash
exec bash "$(git rev-parse --show-toplevel)/.ai-delivery/scripts/hooks/validate-ui-contract.sh" "$@"
