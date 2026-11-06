package workspace

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"sort"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

const FactPrefix = model.FactPrefix
const ContextFact = model.ContextFact

// Fact 访问逻辑材料别名，避免与项目内同名文件冲突。
func Fact(s model.Snapshot, name string) ([]byte, bool) { return model.Fact(s, name) }

type snapshot struct {
	id          string
	workspace   model.Workspace
	scope       model.Scope
	request     model.ReadRequest
	documents   map[string][]byte
	files       []model.FileIdentity
	diagnostics []model.Diagnostic
}

// NewSnapshot 固定一次消费结果；输入和访问器均复制，调用方不能修改共享事实。
func NewSnapshot(w model.Workspace, scope model.Scope, req model.ReadRequest, docs map[string][]byte, files []model.FileIdentity, diagnostics []model.Diagnostic) (model.Snapshot, error) {
	if err := req.Validate(); err != nil {
		return nil, err
	}
	s := &snapshot{workspace: w, scope: scope, request: model.CloneReadRequest(req), documents: map[string][]byte{}, files: model.CloneFileIdentities(files), diagnostics: model.CloneDiagnostics(diagnostics)}
	hashes := map[string]any{}
	for name, body := range docs {
		s.documents[name] = append([]byte(nil), body...)
		hashes[name] = fmt.Sprintf("%x", sha256.Sum256(body))
	}
	sort.Slice(s.files, func(i, j int) bool { return s.files[i].Path < s.files[j].Path })
	for i := 1; i < len(s.files); i++ {
		if s.files[i-1].Path == s.files[i].Path {
			return nil, fmt.Errorf("消费身份重复: %s", s.files[i].Path)
		}
	}
	// JSON 结构转换后仍由 protocol 的唯一 canonical 算法生成摘要。
	encoded, err := json.Marshal(struct {
		Workspace   model.Workspace
		Scope       model.Scope
		Request     model.ReadRequest
		Files       []model.FileIdentity
		Documents   map[string]any
		Diagnostics []model.Diagnostic
	}{w, scope, s.request, s.files, hashes, s.diagnostics})
	if err != nil {
		return nil, err
	}
	value, err := protocol.ParseJSON(encoded)
	if err != nil {
		return nil, err
	}
	s.id, err = protocol.CanonicalSHA256(value)
	return s, err
}
func (s *snapshot) ID() string                 { return s.id }
func (s *snapshot) Workspace() model.Workspace { return s.workspace }
func (s *snapshot) Scope() model.Scope         { return s.scope }
func (s *snapshot) Request() model.ReadRequest { return model.CloneReadRequest(s.request) }
func (s *snapshot) Document(name string) ([]byte, bool) {
	b, ok := s.documents[name]
	return append([]byte(nil), b...), ok
}
func (s *snapshot) Files() []model.FileIdentity     { return model.CloneFileIdentities(s.files) }
func (s *snapshot) Diagnostics() []model.Diagnostic { return model.CloneDiagnostics(s.diagnostics) }

func Diagnose(s model.Snapshot, ds ...model.Diagnostic) (model.Snapshot, error) {
	v, ok := s.(*snapshot)
	if !ok {
		return nil, fmt.Errorf("需要 workspace 快照")
	}
	return NewSnapshot(v.workspace, v.scope, v.request, v.documents, v.files, append(v.Diagnostics(), ds...))
}
func inputDiagnostic(path, code, scope string, err error) model.Diagnostic {
	d := model.Diagnostic{Code: code, Path: path, Category: "context_input", Scope: scope, Message: err.Error(), Recovery: "修复具体输入或补读正文后重新生成上下文；材料齐全不代表动作授权"}
	var format *protocol.FormatError
	if errors.As(err, &format) {
		d.Path = format.Path
		d.Recovery = protocol.FormatRecovery(format.Path)
	}
	return d
}
