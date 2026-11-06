//go:build windows

package runner

import (
	"fmt"
	"os/exec"
	"sync"
	"syscall"
	"time"
	"unsafe"
)

var kernel32 = syscall.NewLazyDLL("kernel32.dll")
var createJob = kernel32.NewProc("CreateJobObjectW")
var setJob = kernel32.NewProc("SetInformationJobObject")
var assignJob = kernel32.NewProc("AssignProcessToJobObject")
var terminateJob = kernel32.NewProc("TerminateJobObject")
var queryJob = kernel32.NewProc("QueryInformationJobObject")
var resumeProcess = syscall.NewLazyDLL("ntdll.dll").NewProc("NtResumeProcess")

type jobBasicLimits struct {
	ProcessTime, JobTime           int64
	Flags                          uint32
	MinWorkingSet, MaxWorkingSet   uintptr
	ActiveProcessLimit             uint32
	Affinity                       uintptr
	PriorityClass, SchedulingClass uint32
}
type jobExtendedLimits struct {
	Basic                                                                        jobBasicLimits
	IOCounters                                                                   [6]uint64
	ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed uintptr
}
type jobAccounting struct {
	Times                                                            [4]int64
	PageFaults, TotalProcesses, ActiveProcesses, TerminatedProcesses uint32
}

// 挂起创建后先纳入 Job，再恢复，避免子进程在 Job 绑定前逃离清理范围。
func prepareProcess(cmd *exec.Cmd) error {
	for _, p := range []*syscall.LazyProc{createJob, setJob, assignJob, resumeProcess, terminateJob, queryJob} {
		if err := p.Find(); err != nil {
			return fmt.Errorf("Windows 进程隔离能力不可用: %w", err)
		}
	}
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x00000004}
	return nil
}
func startedProcess(cmd *exec.Cmd) (func() (bool, error), error) {
	job, _, e := createJob.Call(0, 0)
	if job == 0 {
		return nil, fmt.Errorf("CreateJobObjectW: %w", e)
	}
	fail := func(err error) (func() (bool, error), error) {
		syscall.CloseHandle(syscall.Handle(job))
		return nil, err
	}
	limits := jobExtendedLimits{Basic: jobBasicLimits{Flags: 0x00002000}}
	if ok, _, err := setJob.Call(job, 9, uintptr(unsafe.Pointer(&limits)), unsafe.Sizeof(limits)); ok == 0 {
		return fail(fmt.Errorf("SetInformationJobObject: %w", err))
	}
	handle, err := syscall.OpenProcess(0x0100|0x0200|0x0001|0x0800, false, uint32(cmd.Process.Pid))
	if err != nil {
		return fail(err)
	}
	defer syscall.CloseHandle(handle)
	if ok, _, err := assignJob.Call(job, uintptr(handle)); ok == 0 {
		return fail(fmt.Errorf("AssignProcessToJobObject: %w", err))
	}
	if status, _, _ := resumeProcess.Call(uintptr(handle)); status != 0 {
		return fail(fmt.Errorf("NtResumeProcess 状态: %#x", status))
	}
	var once sync.Once
	var closeErr error
	var forced bool
	return func() (bool, error) {
		once.Do(func() {
			defer syscall.CloseHandle(syscall.Handle(job))
			var initial jobAccounting
			if ok, _, err := queryJob.Call(job, 1, uintptr(unsafe.Pointer(&initial)), unsafe.Sizeof(initial), 0); ok == 0 {
				closeErr = fmt.Errorf("QueryInformationJobObject: %w", err)
				return
			}
			if initial.ActiveProcesses == 0 {
				return
			}
			if ok, _, err := terminateJob.Call(job, 1); ok == 0 {
				closeErr = fmt.Errorf("TerminateJobObject: %w", err)
				return
			}
			forced = true
			ticker := time.NewTicker(10 * time.Millisecond)
			defer ticker.Stop()
			deadline := time.NewTimer(5 * time.Second)
			defer deadline.Stop()
			for {
				var accounting jobAccounting
				if ok, _, err := queryJob.Call(job, 1, uintptr(unsafe.Pointer(&accounting)), unsafe.Sizeof(accounting), 0); ok == 0 {
					closeErr = fmt.Errorf("QueryInformationJobObject: %w", err)
					return
				}
				if accounting.ActiveProcesses == 0 {
					return
				}
				select {
				case <-ticker.C:
				case <-deadline.C:
					closeErr = fmt.Errorf("无法确认 Windows Job 中进程已全部退出")
					return
				}
			}
		})
		return forced, closeErr
	}, nil
}
func processSignal(*exec.Cmd) string { return "" }
