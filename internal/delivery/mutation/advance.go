package mutation

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

var ErrCapability = errors.New("推进运行能力不可用")

type CheckAction func(context.Context, model.Workspace, model.Scope, model.Action) (model.CheckReport, error)

// Advance 的快照只用于并发前置；锁内仍重新执行全部当前门禁。
func Advance(ctx context.Context, w model.Workspace, scope model.Scope, target, expected string, check CheckAction) (model.MutationResult, error) {
	result := model.MutationResult{WrittenPaths: []string{}}
	intent := map[string]model.Intent{"split_ready": "analyze", "design_ready": "design", "in_dev": "implement", "acceptance_frozen": "ui", "visual_acceptance_passed": "verify", "merged": "merge"}[target]
	if target == "archived" {
		return result, fmt.Errorf("advance 不支持 archived；请使用 archive")
	}
	if intent == "" || expected == "" {
		return result, fmt.Errorf("需要合法目标状态及 expected_snapshot")
	}
	if err := workspace.ValidateScope(scope); err != nil {
		return result, err
	}
	unlock, err := projectfs.ProjectLock(w.ProjectRoot)
	if err != nil {
		return result, fmt.Errorf("%w: %v", ErrCapability, err)
	}
	defer unlock()
	action := model.Action{Intent: intent, TargetStatus: target}
	report, err := check(ctx, w, scope, action)
	if err != nil {
		return result, err
	}
	result.Decision = report.Decision
	result.BeforeSnapshotID = report.Snapshot.ID()
	if report.Snapshot.ID() != expected {
		result.Decision.Allowed = false
		result.Decision.Diagnostics = append(result.Decision.Diagnostics, model.Diagnostic{Code: "snapshot_mismatch", Category: "concurrency", Scope: scope.SubrequirementID, Message: "动作输入或 intent/target 已改变", Recovery: "对同一目标重新 check 后重试"})
	}
	if !result.Decision.Allowed {
		return result, nil
	}
	facts, err := workspace.Facts(report.Snapshot)
	if err != nil {
		return result, err
	}
	body, ok := model.Fact(report.Snapshot, "status")
	if !ok {
		return result, fmt.Errorf("快照缺少 status")
	}
	status, err := protocol.Object(body)
	if err != nil {
		return result, err
	}
	entries, ok := status["sub_requirements"].(map[string]any)
	if !ok {
		return result, fmt.Errorf("无效 sub_requirements")
	}
	entry, ok := entries[scope.SubrequirementID].(map[string]any)
	if !ok {
		return result, fmt.Errorf("无效切片")
	}
	if entry["status"] == target {
		return result, nil
	}
	entry["status"] = target
	body, err = json.MarshalIndent(status, "", "  ")
	if err != nil {
		return result, err
	}
	path := facts.Artifacts["status"]
	targetPath := filepath.Join(w.ProjectRoot, filepath.FromSlash(path))
	verify := func(temporaryPath string) error {
		if err := ctx.Err(); err != nil {
			return err
		}
		if err := projectfs.NoLinkedParents(w.ProjectRoot, targetPath); err != nil {
			return err
		}
		if temporaryPath != "" {
			return (workspace.Reader{}).VerifyPublication(ctx, report.Snapshot, temporaryPath)
		}
		return (workspace.Reader{}).Verify(ctx, report.Snapshot)
	}
	if err = verify(""); err != nil {
		return result, err
	}
	if err = projectfs.AtomicWriteFileChecked(targetPath, append(body, '\n'), 0600, verify); err != nil {
		return result, err
	}
	result.WrittenPaths = []string{path}
	return result, nil
}
