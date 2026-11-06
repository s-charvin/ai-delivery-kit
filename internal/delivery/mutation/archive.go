package mutation

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/contextview"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
	"github.com/s-charvin/ai-delivery-kit/internal/projectfs"
)

// Archiver 的边界可接入实际文件发布器；默认使用共同原子写入能力。
// 逐文件发布不是跨目录事务；任一步失败保留已发布输出，status 最后发布。
type Archiver struct {
	Check   CheckAction
	Now     func() time.Time
	Publish func(string, []byte, os.FileMode, func(string) error) error
}
type archiveOutput struct {
	path string
	body []byte
}

func (a Archiver) Archive(ctx context.Context, w model.Workspace, scope model.Scope, req model.ArchiveRequest) (model.MutationResult, error) {
	result := model.MutationResult{WrittenPaths: []string{}}
	if !req.Confirmed {
		return result, fmt.Errorf("归档需要调用方明确确认已取得此次用户 CP-ARCHIVE 授权；checkpoint 和 snapshot 不是批准")
	}
	if req.ExpectedSnapshot == "" {
		return result, fmt.Errorf("归档需要 expected_snapshot")
	}
	if err := workspace.ValidateScope(scope); err != nil {
		return result, err
	}
	unlock, err := projectfs.ProjectLock(w.ProjectRoot)
	if err != nil {
		return result, fmt.Errorf("%w: %v", ErrCapability, err)
	}
	defer unlock()
	report, err := a.Check(ctx, w, scope, model.Action{Intent: "archive"})
	if err != nil {
		return result, err
	}
	result.Decision = report.Decision
	result.BeforeSnapshotID = report.Snapshot.ID()
	if report.Snapshot.ID() != req.ExpectedSnapshot {
		result.Decision.Allowed = false
		result.Decision.Diagnostics = append(result.Decision.Diagnostics, model.Diagnostic{Code: "snapshot_mismatch", Category: "concurrency", Scope: scope.SubrequirementID, Message: "归档门禁输入已改变", Recovery: "对 archive 意图重新 check 后重试"})
	}
	if !result.Decision.Allowed {
		return result, nil
	}
	raw, _ := model.Fact(report.Snapshot, "status")
	status, err := protocol.Object(raw)
	if err != nil {
		return result, err
	}
	entries, _ := status["sub_requirements"].(map[string]any)
	entry, _ := entries[scope.SubrequirementID].(map[string]any)
	if entry["status"] != "merged" {
		return result, fmt.Errorf("仅 merged 可新归档；历史终态不重写")
	}
	if id, ok := status["requirement_id"]; ok && id != scope.RequirementID {
		return result, fmt.Errorf("requirement_id 与当前范围不一致")
	}
	facts, err := workspace.Facts(report.Snapshot)
	if err != nil {
		return result, err
	}
	complete := true
	for id, raw := range entries {
		e, ok := raw.(map[string]any)
		if !ok {
			return result, fmt.Errorf("无效切片 %s", id)
		}
		complete = complete && (id == scope.SubrequirementID || e["status"] == "archived")
	}
	now := time.Now().UTC()
	if a.Now != nil {
		now = a.Now()
	}
	ledger, _ := report.Snapshot.Document(facts.Artifacts["retrospective"])
	rows, err := checks.RetrospectiveEntries(ledger, now)
	if err != nil {
		return result, err
	}
	// 模板是本次调用的显式消费输入；其身份与输出 CAS 不改变 check 返回的门禁身份。
	gate := report.Snapshot
	r := workspace.Reader{}
	templates := map[string]string{}
	for name, p := range map[string]string{"report": req.DeliveryReportTemplate, "index": req.RetrospectiveIndexTemplate} {
		if p == "" {
			continue
		}
		if filepath.IsAbs(p) {
			p, err = filepath.Rel(w.ProjectRoot, p)
			if err != nil {
				return result, err
			}
			p = filepath.ToSlash(p)
		}
		p, err = workspace.NormalizePath(p)
		if err != nil {
			return result, err
		}
		gate, err = r.Extend(ctx, gate, []string{p})
		if err != nil {
			return result, err
		}
		b, ok := gate.Document(p)
		if !ok || !utf8.Valid(b) {
			return result, fmt.Errorf("缺少有效本地化模板: %s", p)
		}
		if strings.Contains(string(b), "ai-delivery-template-language") {
			return result, fmt.Errorf("模板仍含语言说明，须完成本地化并移除说明: %s", p)
		}
		templates[name] = string(b)
	}
	outputs := []archiveOutput{}
	outputPaths := []string{facts.Artifacts["status"]}
	if complete {
		outputPaths = append(outputPaths, facts.Artifacts["delivery_report"], facts.Artifacts["retrospective_index"])
	}
	seen := map[string]bool{}
	for _, p := range outputPaths {
		if p == "" || seen[p] {
			return result, fmt.Errorf("归档输出路径冲突")
		}
		seen[p] = true
		abs := filepath.Join(w.ProjectRoot, filepath.FromSlash(p))
		if err := projectfs.NoLinkedParents(w.ProjectRoot, abs); err != nil {
			return result, err
		}
		if p != facts.Artifacts["status"] {
			for _, id := range gate.Files() {
				if id.Path == p || id.ResolvedPath == p {
					return result, fmt.Errorf("归档输出覆盖已消费门禁输入: %s", p)
				}
			}
			sources, _ := contextview.Plan(gate, model.ContextRequest{Role: "finish"})
			for _, source := range sources {
				raw, ok := gate.Document(source.Path)
				if !ok {
					continue
				}
				// 已消费来源中的精确项目路径和本地 Markdown 引用采用保守冲突规则，
				// 不用自然语言动词猜测该引用是否可被忽略。
				referenced := strings.Contains(string(raw), p)
				for _, link := range regexp.MustCompile(`\]\(<?([^\s)>#]+)`).FindAllStringSubmatch(string(raw), -1) {
					referenced = referenced || filepath.ToSlash(filepath.Clean(filepath.Join(filepath.Dir(source.Path), link[1]))) == p
				}
				if referenced {
					return result, fmt.Errorf("归档输出被已消费来源 %s 显式引用: %s", source.Path, p)
				}
			}
		}
	}
	before, err := r.CaptureFiles(ctx, w, outputPaths)
	if err != nil {
		return result, err
	}
	existing := map[string][]byte{}
	for _, p := range outputPaths {
		b, err := os.ReadFile(filepath.Join(w.ProjectRoot, filepath.FromSlash(p)))
		if err != nil && !os.IsNotExist(err) {
			return result, err
		}
		if !utf8.Valid(b) {
			return result, fmt.Errorf("归档输出不是有效 UTF-8，不能无损合并: %s", p)
		}
		existing[p] = b
	}
	after, err := r.CaptureFiles(ctx, w, outputPaths)
	if err != nil || !reflect.DeepEqual(before, after) {
		return result, fmt.Errorf("读取归档输出期间身份漂移: %v", err)
	}
	entry["status"] = "archived"
	evidence, err := checks.ArchiveEvidence(gate, facts.Artifacts, entry)
	if err != nil {
		return result, err
	}
	entry["archive_evidence"] = evidence
	if complete {
		template := templates["report"]
		for _, marker := range []string{"<req-id>", "<archived_at>", "<subreq_count>", "<subreq_rows>"} {
			if !strings.Contains(template, marker) {
				return result, fmt.Errorf("最终归档需要本地化交付报告模板，缺少 %s", marker)
			}
		}
		bindingRaw, _ := model.Fact(gate, "binding")
		binding, err := protocol.Object(bindingRaw)
		if err != nil {
			return result, err
		}
		ids := []string{}
		for id := range entries {
			ids = append(ids, id)
		}
		sort.Strings(ids)
		lines := []string{}
		reqDir := facts.Artifacts["requirement_root"]
		for _, id := range ids {
			paths, err := workspace.ArtifactPaths(w, model.Scope{RequirementID: scope.RequirementID, SubrequirementID: id}, binding)
			if err != nil {
				return result, err
			}
			subdir, _ := filepath.Rel(reqDir, paths["sub_requirement_dir"])
			verification, _ := filepath.Rel(reqDir, paths["verification"])
			e := entries[id].(map[string]any)
			lines = append(lines, fmt.Sprintf("| %s | %v | %s/ | %s |", id, e["status"], filepath.ToSlash(subdir), filepath.ToSlash(verification)))
		}
		base := strings.NewReplacer("<req-id>", scope.RequirementID, "<subreq_count>", fmt.Sprint(len(entries)), "<subreq_rows>", strings.Join(lines, "\n")).Replace(template)
		reportPath := facts.Artifacts["delivery_report"]
		if old := existing[reportPath]; len(old) > 0 {
			pattern := "^" + strings.ReplaceAll(regexp.QuoteMeta(base), "<archived_at>", "([^\\r\\n]+)") + "$"
			match := regexp.MustCompile(pattern).FindStringSubmatch(string(old))
			if len(match) < 2 {
				return result, fmt.Errorf("交付报告已有无法无损合并的人工内容或模板冲突: %s", reportPath)
			}
			for _, value := range match[2:] {
				if value != match[1] {
					return result, fmt.Errorf("报告包含冲突归档时间")
				}
			}
			stamp, err := time.Parse(time.RFC3339Nano, match[1])
			if err != nil || stamp.Format("2006-01-02") != now.Format("2006-01-02") {
				return result, fmt.Errorf("现有交付报告时间与本次归档不一致")
			}
			now = stamp
		}
		outputs = append(outputs, archiveOutput{reportPath, []byte(strings.ReplaceAll(base, "<archived_at>", now.Format(time.RFC3339Nano)))})
		content, write, err := archiveIndex(existing[facts.Artifacts["retrospective_index"]], templates["index"], rows, scope.RequirementID, facts.Artifacts["retrospective"], facts.Artifacts["retrospective_index"], now)
		if err != nil {
			return result, err
		}
		if write {
			outputs = append(outputs, archiveOutput{facts.Artifacts["retrospective_index"], content})
		}
	}
	body, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		return result, err
	}
	outputs = append(outputs, archiveOutput{facts.Artifacts["status"], append(body, '\n')})
	expected := before
	publish := a.Publish
	if publish == nil {
		publish = projectfs.AtomicWriteFileChecked
	}
	for _, out := range outputs {
		verify := func(tmp string) error {
			if err := ctx.Err(); err != nil {
				return err
			}
			if tmp == "" {
				if err := r.Verify(ctx, gate); err != nil {
					return err
				}
			} else {
				if err := r.VerifyPublication(ctx, gate, tmp); err != nil {
					return err
				}
			}
			for _, p := range outputPaths {
				if err := projectfs.NoLinkedParents(w.ProjectRoot, filepath.Join(w.ProjectRoot, filepath.FromSlash(p))); err != nil {
					return err
				}
			}
			current, err := r.CaptureFiles(ctx, w, outputPaths)
			if err != nil {
				return err
			}
			if !reflect.DeepEqual(expected, current) {
				return fmt.Errorf("归档输出在发布期间发生并发修改")
			}
			return nil
		}
		if err := verify(""); err != nil {
			return result, err
		}
		abs := filepath.Join(w.ProjectRoot, filepath.FromSlash(out.path))
		if !bytes.Equal(existing[out.path], out.body) {
			if err := publish(abs, out.body, 0644, verify); err != nil {
				return result, err
			}
			result.WrittenPaths = append(result.WrittenPaths, out.path)
		}
		// 发布后的精确字节也必须仍然存在，不能把外部改动吸收为新的 CAS 基线。
		actual, err := os.ReadFile(abs)
		if err != nil || !bytes.Equal(actual, out.body) {
			return result, fmt.Errorf("已发布归档输出已改变: %s", out.path)
		}
		current, err := r.CaptureFiles(ctx, w, outputPaths)
		if err != nil {
			return result, err
		}
		for i, id := range expected {
			if id.Path == out.path {
				expected[i] = identityAt(current, out.path)
			} else {
				if !reflect.DeepEqual(id, identityAt(current, id.Path)) {
					return result, fmt.Errorf("发布期间其他输出已改变: %s", id.Path)
				}
			}
		}
	}
	return result, nil
}
func identityAt(ids []model.FileIdentity, p string) model.FileIdentity {
	for _, id := range ids {
		if id.Path == p {
			return id
		}
	}
	return model.FileIdentity{}
}

func archiveIndex(old []byte, template string, entries []checks.RetrospectiveEntry, req, ledger, index string, at time.Time) ([]byte, bool, error) {
	if len(entries) == 0 {
		return nil, false, nil
	}
	rows := []string{}
	relative, _ := filepath.Rel(filepath.Dir(index), ledger)
	for _, e := range entries {
		if e.Indexable() {
			rows = append(rows, fmt.Sprintf("| %s/%s | %s | %s | %s | %s | %s | [%s/%s](%s#%s) |", req, e.ID, e.Trigger, e.Scenario, e.Path, e.Status, at.Format(time.RFC3339Nano), req, e.ID, filepath.ToSlash(relative), e.Anchor))
		}
	}
	if len(rows) == 0 && len(old) == 0 {
		return nil, false, nil
	}
	text := string(old)
	if strings.Count(text, checks.ProjectIndexStart) > 1 || strings.Count(text, checks.ProjectIndexEnd) > 1 {
		return nil, false, fmt.Errorf("复盘索引有重复锚点")
	}
	start, end := strings.Index(text, checks.ProjectIndexStart), strings.Index(text, checks.ProjectIndexEnd)
	if start >= 0 && end > start {
		block := text[start:end]
		lines := strings.Split(strings.TrimSuffix(block, "\n"), "\n")
		separator := -1
		for i, line := range lines {
			if strings.HasPrefix(line, "| ---") {
				separator = i
				break
			}
		}
		if separator < 0 {
			return nil, false, fmt.Errorf("复盘索引缺少可写表分隔符")
		}
		keep := append([]string{}, lines[:separator+1]...)
		own := map[string]bool{}
		for _, line := range lines[separator+1:] {
			cells := indexRowCells(line)
			if len(cells) > 0 && strings.HasPrefix(cells[0], req+"/") {
				if len(cells) < 7 {
					return nil, false, fmt.Errorf("本需求索引行冲突")
				}
				key := cells[0]
				if own[key] {
					return nil, false, fmt.Errorf("本需求索引行重复: %s", key)
				}
				own[key] = true
				matched := false
				for _, wanted := range rows {
					wc := indexRowCells(wanted)
					if len(cells) == len(wc) {
						same := true
						for j := range cells {
							if j != 5 && cells[j] != wc[j] {
								same = false
							}
						}
						matched = matched || same
					}
				}
				if !matched {
					return nil, false, fmt.Errorf("本需求复盘索引已有冲突人工编辑: %s", key)
				}
				continue
			}
			keep = append(keep, line)
		}
		keep = append(keep, rows...)
		return []byte(text[:start] + strings.Join(keep, "\n") + "\n" + text[end:]), true, nil
	}
	if start >= 0 || end >= 0 {
		return nil, false, fmt.Errorf("复盘索引锚点冲突")
	}
	if strings.Count(template, "<retrospective_rows>") != 1 || strings.Count(template, checks.ProjectIndexStart) != 1 || strings.Count(template, checks.ProjectIndexEnd) != 1 || strings.Index(template, checks.ProjectIndexEnd) < strings.Index(template, checks.ProjectIndexStart) {
		return nil, false, fmt.Errorf("首次创建复盘索引需要有效本地化模板")
	}
	block := template[strings.Index(template, checks.ProjectIndexStart):strings.Index(template, checks.ProjectIndexEnd)]
	separator := regexp.MustCompile(`(?m)^\| ---[^\n]*`).FindStringIndex(block)
	if separator == nil || strings.Index(block, "<retrospective_rows>") < separator[1] {
		return nil, false, fmt.Errorf("复盘索引模板必须在可写表分隔符之后包含行占位符")
	}
	standalone := false
	for _, line := range strings.Split(block, "\n") {
		standalone = standalone || strings.TrimSpace(line) == "<retrospective_rows>"
	}
	if !standalone {
		return nil, false, fmt.Errorf("复盘索引模板的 <retrospective_rows> 必须独占可写行，不能附带正文或注释")
	}
	content := strings.TrimRight(strings.ReplaceAll(template, "<retrospective_rows>", strings.Join(rows, "\n")), "\n") + "\n"
	if len(old) > 0 {
		content = strings.TrimRight(text, "\n") + "\n\n" + content
	}
	return []byte(content), true, nil
}

// 首列按单元格语义识别归属；合法空白及可选边界竖线不改变本需求行身份。
func indexRowCells(line string) []string {
	if !strings.Contains(line, "|") {
		return nil
	}
	cells := strings.Split(strings.TrimSpace(line), "|")
	if cells[0] == "" {
		cells = cells[1:]
	}
	if len(cells) > 0 && cells[len(cells)-1] == "" {
		cells = cells[:len(cells)-1]
	}
	for i := range cells {
		cells[i] = strings.TrimSpace(cells[i])
	}
	return cells
}
