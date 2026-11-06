package checks

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

// ReceiptToCheck 是纯映射，只记录执行事实；不填 reviews、confirmation 或 waiver。
func ReceiptToCheck(r model.RunReceipt) ([]byte, error) {
	d, err := protocol.Object(r.Observation.Details)
	if err != nil {
		return nil, err
	}
	if _, _, _, err := receiptInputData(d); err != nil {
		return nil, err
	}
	spec, ok := d["check_spec"].(map[string]any)
	if !ok || d["receipt_version"] != json.Number("1") || d["complete"] != true || d["check_id"] != r.Observation.CheckID || d["result"] != r.Observation.Result || r.Observation.Provenance != "runner" || spec["id"] != d["check_id"] {
		return nil, fmt.Errorf("收据不完整或观察身份不一致")
	}
	specHash, err := protocol.CanonicalSHA256(spec)
	if err != nil || specHash != d["check_spec_sha256"] {
		return nil, fmt.Errorf("收据检查定义摘要不一致")
	}
	method, ok := spec["method"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("收据缺少方法")
	}
	methodHash, err := protocol.CanonicalSHA256(method)
	if err != nil || methodHash != d["method_sha256"] {
		return nil, fmt.Errorf("收据方法摘要不一致")
	}
	if d["result"] == "passed" && (d["started"] != true || d["forced_termination"] != false || d["process_tree_cleaned"] != true || d["inputs_stable"] != true || d["reports_fresh"] != true || d["exit_code"] != json.Number("0") || d["timed_out"] != false || d["interrupted"] != false || d["signal"] != "") {
		return nil, fmt.Errorf("passed 收据与执行事实矛盾")
	}
	for _, key := range []string{"stdout", "stderr"} {
		file, ok := d[key].(map[string]any)
		capture, valid := d[key+"_capture"].(map[string]any)
		if !ok || !valid || capture["sha256"] != file["sha256"] {
			return nil, fmt.Errorf("收据原始流摘要与已发布日志不一致")
		}
		n, ok := capture["bytes"].(json.Number)
		count, e := strconv.ParseInt(string(n), 10, 64)
		if !ok || e != nil || count < 0 {
			return nil, fmt.Errorf("收据缺少实际采集字节数")
		}
	}
	reports, ok := d["reports"].([]any)
	if !ok {
		return nil, fmt.Errorf("收据 reports 必须为列表")
	}
	evidence := []map[string]any{}
	for _, value := range append([]any{d["stdout"], d["stderr"]}, reports...) {
		f, ok := value.(map[string]any)
		p, pok := f["path"].(string)
		hash, hok := f["sha256"].(string)
		if !ok || !pok || !hok || f["kind"] != "file" || !hexDigest.MatchString(hash) {
			return nil, fmt.Errorf("收据缺少原始输出身份")
		}
		if normalized, e := workspace.NormalizePath(p); e != nil || normalized != p {
			return nil, fmt.Errorf("收据输出路径无效")
		}
		evidence = append(evidence, map[string]any{"path": p, "sha256": hash})
	}
	if p, e := workspace.NormalizePath(r.Path); e != nil || p != r.Path {
		return nil, fmt.Errorf("收据路径无效")
	}
	body := append(append([]byte{}, r.Observation.Details...), '\n')
	evidence = append(evidence, map[string]any{"path": r.Path, "sha256": fmt.Sprintf("%x", sha256.Sum256(body))})
	argv, ok := d["argv"].([]any)
	if !ok || len(argv) == 0 {
		return nil, fmt.Errorf("收据缺少实际 argv")
	}
	for _, v := range argv {
		if _, ok := v.(string); !ok {
			return nil, fmt.Errorf("收据 argv 类型无效")
		}
	}
	command, _ := json.Marshal(argv)
	mode := "executed"
	if d["started"] != true {
		mode = "not_run"
	}
	return json.Marshal(map[string]any{"id": d["check_id"], "required": spec["applicability"] == "required", "result": d["result"], "mode": mode, "command": string(command), "cwd": d["cwd"], "exit_code": d["exit_code"], "acceptance_ids": spec["acceptance_ids"], "evidence": evidence, "receipt_path": r.Path})
}
