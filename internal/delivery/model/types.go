package model

import "context"

type Workspace struct {
	ProjectRoot    string
	DeliveryRoot   string
	ProgramPath    string
	ProgramID      string
	ProtocolDigest string
	ResourceDigest string
}
type Scope struct{ RequirementID, SubrequirementID string }
type Intent string // analyze/design/ui/implement/verify/merge/archive；解析时拒绝未知值

type Action struct {
	Intent       Intent
	TargetStatus string
}
type ContextRequest struct {
	Role          string
	DeclaredPaths []string
	BudgetChars   int
}
type ReadRequest struct {
	Action  *Action
	Context *ContextRequest // 两者恰有一个非nil，定义动作/只读身份域
}
type FileIdentity struct {
	Path         string // 项目相对 POSIX 路径；非 Git 也适用
	ResolvedPath string // 解析链接后的项目相对路径，保留既有证据身份语义
	Kind         string // file/directory/symlink/absent
	SHA256       *string
	Mode         *uint32
	LinkTarget   *string
}
type Diagnostic struct {
	Code, Path, Category, Scope, Message, Recovery string
	SourceRefs                                     []string
}
type Snapshot interface {
	ID() string
	Workspace() Workspace
	Scope() Scope
	Request() ReadRequest
	Document(name string) ([]byte, bool)
	Files() []FileIdentity
	Diagnostics() []Diagnostic
}
type ContextSource struct {
	Path     string
	SHA256   *string
	Kind     string
	Required bool
	Delivery string // provided/needs_read/missing
	Reason   string
	Body     *string
}
type ContextView struct {
	ContextComplete bool
	Sources         []ContextSource
	Diagnostics     []Diagnostic
}
type CheckMethod struct {
	ID          string
	Argv        []string
	Cwd         string
	ParserID    string
	ReportPaths []string
	SourceRefs  []string
}
type CheckSpec struct {
	ID                                    string
	Applicability                         string // required/not_applicable/unknown
	AcceptanceIDs, SourceRefs, InputPaths []string
	Method                                *CheckMethod
}
type CheckObservation struct {
	CheckID    string
	Result     string // passed/failed/invalid/not_run/blocked/not_applicable/waived
	Provenance string // runner/external/declaration
	Evidence   []FileIdentity
	Details    []byte // 验证过的JSON字节；构造/访问均复制
}
type Decision struct {
	Allowed     bool
	Action      Action
	Checks      []CheckSpec
	Diagnostics []Diagnostic
}
type ObservationSet struct {
	Snapshot     Snapshot
	Observations []CheckObservation
}
type CheckReport struct {
	Snapshot Snapshot
	Decision Decision
}
type ContextReport struct {
	Snapshot Snapshot
	View     ContextView
}
type RunRequest struct {
	CheckID        string
	Argv           []string
	Cwd            string
	TimeoutSeconds int
	InputPaths     []string
}
type RunReceipt struct {
	Path        string
	Observation CheckObservation
}
type MutationResult struct {
	Decision         Decision
	BeforeSnapshotID string
	AfterSnapshotID  *string
	WrittenPaths     []string
}

// Confirmed 是调用方已取得此次 CP-ARCHIVE 用户确认的明确声明；不是身份认证。
type ArchiveRequest struct {
	ExpectedSnapshot           string
	Confirmed                  bool
	DeliveryReportTemplate     string
	RetrospectiveIndexTemplate string
}

// 接口签名按实现责任分配到相应包；核心纯规则不接收IO对象。
type WorkspaceReader interface {
	Resolve(ctx context.Context, project, deliveryRoot string) (Workspace, error)
	Load(ctx context.Context, w Workspace, scope Scope, req ReadRequest) (Snapshot, error)
}
type ContextSelector interface {
	Select(s Snapshot, req ContextRequest) ContextView
}
type Policy interface {
	PlanChecks(s Snapshot, a Action) []CheckSpec
	Evaluate(s Snapshot, a Action, checks []CheckSpec, obs []CheckObservation) Decision
}
type ContractReader interface {
	Collect(ctx context.Context, s Snapshot, checks []CheckSpec) (ObservationSet, error)
}
type Services interface {
	PrepareContext(ctx context.Context, w Workspace, scope Scope, req ContextRequest) (ContextReport, error)
	CheckAction(ctx context.Context, w Workspace, scope Scope, a Action) (CheckReport, error)
	RunCheck(ctx context.Context, w Workspace, scope Scope, req RunRequest) (RunReceipt, error)
	Advance(ctx context.Context, w Workspace, scope Scope, target, expectedSnapshot string) (MutationResult, error)
	Archive(ctx context.Context, w Workspace, scope Scope, req ArchiveRequest) (MutationResult, error)
}
