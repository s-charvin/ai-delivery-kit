package runner

import (
	"encoding/json"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/protocol"
)

type File struct {
	Path         string  `json:"path"`
	ResolvedPath string  `json:"resolved_path,omitempty"`
	Kind         string  `json:"kind"`
	SHA256       *string `json:"sha256"`
	Mode         *uint32 `json:"mode,omitempty"`
	LinkTarget   *string `json:"link_target,omitempty"`
}
type Method struct {
	ID          string   `json:"id"`
	Argv        []string `json:"argv"`
	Cwd         string   `json:"cwd"`
	ParserID    string   `json:"parser_id"`
	ReportPaths []string `json:"report_paths"`
	SourceRefs  []string `json:"source_refs"`
}
type Spec struct {
	ID            string   `json:"id"`
	Applicability string   `json:"applicability"`
	AcceptanceIDs []string `json:"acceptance_ids"`
	SourceRefs    []string `json:"source_refs"`
	InputPaths    []string `json:"input_paths"`
	Method        Method   `json:"method"`
}
type Receipt struct {
	Version            int               `json:"receipt_version"`
	RunID              string            `json:"run_id"`
	CheckID            string            `json:"check_id"`
	RequirementID      string            `json:"requirement_id"`
	SubrequirementID   string            `json:"subrequirement_id"`
	ProgramID          string            `json:"program_id"`
	ProtocolDigest     string            `json:"protocol_digest"`
	ResourceDigest     string            `json:"resource_digest"`
	SnapshotID         string            `json:"snapshot_id"`
	Spec               Spec              `json:"check_spec"`
	SpecSHA256         string            `json:"check_spec_sha256"`
	MethodSHA256       string            `json:"method_sha256"`
	Argv               []string          `json:"argv"`
	Cwd                string            `json:"cwd"`
	Executable         string            `json:"executable"`
	StartedAt          string            `json:"started_at"`
	EndedAt            string            `json:"ended_at"`
	DurationMS         int64             `json:"duration_ms"`
	Started            bool              `json:"started"`
	ExitCode           *int              `json:"exit_code"`
	Signal             string            `json:"signal"`
	TimedOut           bool              `json:"timed_out"`
	Interrupted        bool              `json:"interrupted"`
	ProcessTreeCleaned bool              `json:"process_tree_cleaned"`
	ForcedTermination  bool              `json:"forced_termination"`
	InputsBefore       []File            `json:"inputs_before"`
	InputsAfter        []File            `json:"inputs_after"`
	InputRoles         map[string]string `json:"input_roles"`
	ExtraInputPaths    []string          `json:"extra_input_paths"`
	InputsStable       bool              `json:"inputs_stable"`
	InputScope         string            `json:"input_scope"`
	ReuseEligible      bool              `json:"reuse_eligible"`
	Stdout             File              `json:"stdout"`
	Stderr             File              `json:"stderr"`
	StdoutCapture      StreamCapture     `json:"stdout_capture"`
	StderrCapture      StreamCapture     `json:"stderr_capture"`
	Reports            []File            `json:"reports"`
	ReportsFresh       bool              `json:"reports_fresh"`
	TestsRun           []string          `json:"tests_run"`
	Complete           bool              `json:"complete"`
	Result             string            `json:"result"`
	Problems           []string          `json:"problems"`
}

func filesDTO(files []model.FileIdentity) []File {
	out := make([]File, 0, len(files))
	for _, f := range files {
		out = append(out, File{f.Path, f.ResolvedPath, f.Kind, f.SHA256, f.Mode, f.LinkTarget})
	}
	return out
}
func specDTO(s model.CheckSpec) Spec {
	m := s.Method
	return Spec{s.ID, s.Applicability, append([]string{}, s.AcceptanceIDs...), append([]string{}, s.SourceRefs...), append([]string{}, s.InputPaths...), Method{m.ID, append([]string{}, m.Argv...), m.Cwd, m.ParserID, append([]string{}, m.ReportPaths...), append([]string{}, m.SourceRefs...)}}
}
func digest(v any) (string, error) {
	b, e := json.Marshal(v)
	if e != nil {
		return "", e
	}
	parsed, e := protocol.ParseJSON(b)
	if e != nil {
		return "", e
	}
	return protocol.CanonicalSHA256(parsed)
}
