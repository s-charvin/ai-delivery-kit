//go:build !windows

package runner_test

import "syscall"

const peerResetError = syscall.ECONNRESET
