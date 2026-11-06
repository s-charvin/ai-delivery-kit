package cli

import (
	"context"
	"flag"
	"fmt"
	"io"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/checks"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

func (a *App) runEvidence(args []string) int {
	if len(args) > 0 && (args[0] == "--help" || args[0] == "-h") {
		return a.deliveryJSON(map[string]any{"command": "evidence", "operations": []string{"fingerprint", "review-digest"}, "usage": "ai-delivery evidence fingerprint --help | ai-delivery evidence review-digest --help"}, 0)
	}
	if len(args) == 0 || args[0] != "fingerprint" && args[0] != "review-digest" {
		return a.checkError(fmt.Errorf("evidence 需要 fingerprint 或 review-digest"), 2)
	}
	operation := args[0]
	flags := flag.NewFlagSet("evidence "+operation, flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	project := flags.String("project", "", "项目根")
	delivery := flags.String("delivery-root", "", "治理根")
	file := flags.String("file", "", "当前 verification 文件")
	format := flags.String("format", "json", "输出格式")
	var paths pathsFlag
	flags.Var(&paths, "input", "输入文件，可重复")
	if e := flags.Parse(args[1:]); e != nil {
		if e == flag.ErrHelp {
			usage := "ai-delivery evidence fingerprint --input <path> [--input <path> ...]"
			if operation == "review-digest" {
				usage = "ai-delivery evidence review-digest --file <verification-path>"
			}
			return a.commandHelp(flags, usage, []string{"fingerprint 需要可重复 --input，不接受 --file；只计算显式文件/absence 的当前身份。", "review-digest 需要 --file，不接受 --input；只计算 verification v2 声明摘要，不证明执行或独立评审。", "只接受 json 格式；run 已返回 check/inputs，没有 receipt 转换操作。"}, nil)
		}
		return a.checkError(e, 2)
	}
	if flags.NArg() != 0 || *format != "json" || operation == "fingerprint" && (len(paths) == 0 || *file != "") || operation == "review-digest" && (*file == "" || len(paths) > 0) {
		return a.checkError(fmt.Errorf("fingerprint 需要 --input，review-digest 需要 --file"), 2)
	}
	if operation == "review-digest" {
		paths = append(paths, *file)
	}
	ctx := context.Background()
	reader := workspace.NewInstalledReader()
	w, e := reader.Resolve(ctx, *project, *delivery)
	if e != nil {
		return a.checkError(e, 2)
	}
	snapshot, e := workspace.NewSnapshot(w, model.Scope{}, model.ReadRequest{Action: &model.Action{Intent: "analyze"}}, nil, nil, nil)
	if e != nil {
		return a.checkError(e, 3)
	}
	snapshot, e = reader.Extend(ctx, snapshot, paths)
	if e != nil {
		return a.checkError(e, 2)
	}
	if operation == "review-digest" {
		p, e := workspace.NormalizePath(*file)
		if e != nil {
			return a.checkError(e, 2)
		}
		raw, ok := snapshot.Document(p)
		if !ok {
			return a.checkError(fmt.Errorf("缺少当前 verification 文件"), 2)
		}
		data, e := protocol.Object(raw)
		if strings.Contains(string(raw), checks.VerificationStart) {
			data, e = checks.ParseBlock(raw, checks.VerificationStart, checks.VerificationEnd)
		}
		if e != nil {
			return a.checkError(&protocol.FormatError{Path: p, Cause: e}, 2)
		}
		if e = protocol.RequireVersion(data, "version", "verification"); e != nil {
			return a.checkError(&protocol.FormatError{Path: p, Cause: e}, 2)
		}
		digest, e := protocol.ReviewDigest(data)
		if e != nil {
			return a.checkError(e, 2)
		}
		inputs, ok := data["inputs"].([]any)
		if !ok {
			return a.checkError(&protocol.FormatError{Path: p + "#/inputs", Cause: fmt.Errorf("实际类型=%T，实际值=%v；当前要求 inputs 数组", data["inputs"], data["inputs"])}, 2)
		}
		inputDigest, e := protocol.InputDigest(inputs)
		if e != nil {
			return a.checkError(e, 2)
		}
		return a.deliveryJSON(map[string]any{"verification_sha256": digest, "input_sha256": inputDigest, "meaning": "当前合同声明的纯内容摘要；不证明执行或独立评审，不生成批准"}, 0)
	}
	inputs := []any{}
	seen := map[string]bool{}
	for _, p := range paths {
		p, e = workspace.NormalizePath(p)
		if e != nil {
			return a.checkError(e, 2)
		}
		if seen[p] {
			return a.checkError(fmt.Errorf("输入路径重复: %s", p), 2)
		}
		seen[p] = true
		f, ok, e := workspace.Identity(snapshot, p)
		if e != nil || !ok {
			return a.checkError(fmt.Errorf("输入身份未读取: %s", p), 2)
		}
		switch f.Kind {
		case "file":
			if f.SHA256 == nil {
				return a.checkError(fmt.Errorf("输入缺少摘要: %s", p), 2)
			}
			inputs = append(inputs, map[string]any{"path": p, "sha256": *f.SHA256})
		case "absent":
			inputs = append(inputs, map[string]any{"path": p, "sha256": nil, "state": "absent"})
		default:
			return a.checkError(fmt.Errorf("fingerprint 需要文件或明确 absence: %s", p), 2)
		}
	}
	digest, e := protocol.InputDigest(inputs)
	if e != nil {
		return a.checkError(e, 2)
	}
	return a.deliveryJSON(map[string]any{"inputs": inputs, "input_sha256": digest}, 0)
}
