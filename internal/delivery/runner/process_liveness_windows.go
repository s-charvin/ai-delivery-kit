package runner

import (
	"fmt"
	"runtime"
	"syscall"
	"time"
	"unsafe"
)

const (
	maxJobProcesses                = 10000
	jobObjectBasicProcessIDList    = 3
	processQueryLimitedInformation = 0x1000
	errorInvalidParameter          = syscall.Errno(87)
)

func jobProcessIDs(job uintptr, deadline time.Time) ([]uint32, error) {
	capacity := 16
	for {
		if !time.Now().Before(deadline) {
			return nil, fmt.Errorf("枚举 Windows Job 进程超时")
		}
		// 两个 DWORD 头字段之后是 ULONG_PTR 数组；uintptr 分配保证对齐。
		buffer := make([]uintptr, capacity+2)
		header := (*[2]uint32)(unsafe.Pointer(&buffer[0]))
		size := 8 + uintptr(capacity)*unsafe.Sizeof(uintptr(0))
		ok, _, err := queryJob.Call(job, jobObjectBasicProcessIDList, uintptr(unsafe.Pointer(&buffer[0])), size, 0)
		if ok == 0 && err != syscall.ERROR_MORE_DATA {
			return nil, fmt.Errorf("QueryInformationJobObject 进程列表: %w", err)
		}
		if header[0] > maxJobProcesses || header[1] > maxJobProcesses {
			return nil, fmt.Errorf("Windows Job 进程列表超过 %d 个成员: assigned=%d returned=%d", maxJobProcesses, header[0], header[1])
		}
		if ok == 0 || header[0] > uint32(capacity) || header[1] < header[0] {
			if capacity == maxJobProcesses {
				return nil, fmt.Errorf("Windows Job 进程列表持续不完整: assigned=%d returned=%d capacity=%d", header[0], header[1], capacity)
			}
			capacity *= 2
			if uint64(header[0]) > uint64(capacity) {
				capacity = int(header[0])
			}
			if capacity > maxJobProcesses {
				capacity = maxJobProcesses
			}
			continue
		}
		if header[1] > uint32(capacity) {
			return nil, fmt.Errorf("Windows Job 进程列表长度无效")
		}
		ids := unsafe.Slice((*uintptr)(unsafe.Add(unsafe.Pointer(&buffer[0]), 8)), int(header[1]))
		result := make([]uint32, len(ids))
		for i, pid := range ids {
			if uint64(pid) > uint64(^uint32(0)) {
				return nil, fmt.Errorf("Windows Job 进程标识超出范围")
			}
			result[i] = uint32(pid)
		}
		runtime.KeepAlive(buffer)
		return result, nil
	}
}

func jobProcessesRunning(job uintptr, members map[uint32]syscall.Handle, deadline time.Time) (bool, error) {
	// 已持有句柄不代表此前已确认退出，强杀后的核对必须重新建立退出闭包。
	confirmedExit := map[uint32]bool{}
	for {
		ids, err := jobProcessIDs(job, deadline)
		if err != nil {
			return false, err
		}
		needsRescan := false
		for _, pid := range ids {
			if !time.Now().Before(deadline) {
				return false, fmt.Errorf("核对 Windows Job 成员退出状态超时")
			}
			handle, known := members[pid]
			if !known {
				// 保留成员句柄直到清理结束，防止 PID 复用伪造同一成员。
				handle, err = syscall.OpenProcess(syscall.SYNCHRONIZE|processQueryLimitedInformation, false, pid)
				if err == errorInvalidParameter {
					// 已消失的 PID 可能在退出前产生新后代，必须重新取完整列表。
					needsRescan = true
					continue
				}
				if err != nil {
					return false, fmt.Errorf("打开 Windows Job 成员 %d: %w", pid, err)
				}
				var inJob int32
				ok, _, membershipErr := isProcessInJob.Call(uintptr(handle), job, uintptr(unsafe.Pointer(&inJob)))
				if ok == 0 || inJob == 0 {
					syscall.CloseHandle(handle)
					if ok == 0 {
						return false, fmt.Errorf("IsProcessInJob %d: %w", pid, membershipErr)
					}
					needsRescan = true
					continue
				}
				if len(members) == maxJobProcesses {
					syscall.CloseHandle(handle)
					return false, fmt.Errorf("Windows Job 退出核对超过 %d 个成员", maxJobProcesses)
				}
				members[pid] = handle
				needsRescan = true
			}
			if !confirmedExit[pid] {
				needsRescan = true
			}
			state, err := syscall.WaitForSingleObject(handle, 0)
			if err != nil {
				return false, fmt.Errorf("核对 Windows Job 成员 %d 退出状态: %w", pid, err)
			}
			switch state {
			case syscall.WAIT_OBJECT_0:
				confirmedExit[pid] = true
			case syscall.WAIT_TIMEOUT:
				return true, nil
			default:
				return false, fmt.Errorf("Windows Job 成员 %d 等待状态无效: %d", pid, state)
			}
		}
		// 再枚举只含先前已确认退出的成员，才形成不能再生成后代的封闭集合。
		if !needsRescan {
			return false, nil
		}
	}
}
