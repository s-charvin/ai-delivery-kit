package protocol

import "fmt"

// FormatError 保存真实文件位置；格式拒绝不等同于正常缺材料。
type FormatError struct {
	Path  string
	Cause error
}

func (e *FormatError) Error() string {
	if e.Path == "" {
		return e.Cause.Error()
	}
	return fmt.Sprintf("%s: %v", e.Path, e.Cause)
}
func (e *FormatError) Unwrap() error { return e.Cause }

// RequireObjectField 为读取与检查入口保留同一字段格式原因。
func RequireObjectField(data map[string]any, field, path string) (map[string]any, error) {
	value := data[field]
	object, ok := value.(map[string]any)
	if !ok {
		return nil, &FormatError{Path: path + "#/" + field, Cause: fmt.Errorf("%s 实际类型=%T，实际值=%v；当前要求 JSON 对象", field, value, value)}
	}
	return object, nil
}

func FormatRecovery(path string) string {
	return "A. 将此文件及诊断交给自己的 AI：先备份，再按当前模板逐字段迁移，保留业务含义，不伪造批准/评审/执行证据。当前时间格式为带时区 RFC3339Nano，例如 2026-11-05T12:00:00+08:00，不自动重写批准时间。B. 显式备份重建：ai-delivery init --upgrade --reset-data[=实际治理根相对路径] <项目路径>。文件：" + path + "。读取完整当前指引：ai-delivery info --resource kit://ai-delivery-orchestrator/references/version-upgrade.md；模板可通过 info --resource kit://ai-delivery-orchestrator/templates/<文件名> 读取。"
}
