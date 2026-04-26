package prereq

type Status string

const (
	StatusPresent    Status = "present"
	StatusMissing    Status = "missing"
	StatusManualOnly Status = "manual-only"
)

type StatusInput struct {
	HasSpecify bool
	HasUV      bool
	HasPipx    bool
}

type ToolPlan struct {
	Name            string
	Status          Status
	DocsURLs        []string
	InstallCommands [][]string
	Notes           []string
}
