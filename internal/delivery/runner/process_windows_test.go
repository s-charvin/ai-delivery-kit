//go:build windows

package runner_test

import (
	"context"
	"encoding/json"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/runner"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestWindowsNativeArgumentQuoting(t *testing.T) {
	args := []string{"echo", `a b\`, `a\"b`, `"quoted"`, `C:\path with spaces\`, "$HOME & exit 7", ""}
	s, spec, req := setup(t, args, "exit-code", nil)
	r, e := (runner.Runner{}).Run(context.Background(), s, spec, req)
	if e != nil || r.Observation.Result != "passed" {
		t.Fatal(e, string(r.Observation.Details))
	}
	d := receipt(t, r)
	b, e := os.ReadFile(filepath.Join(s.Workspace().ProjectRoot, d["stdout"].(map[string]any)["path"].(string)))
	if e != nil {
		t.Fatal(e)
	}
	var value struct {
		Args []string `json:"args"`
	}
	if e = json.Unmarshal(b, &value); e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(value.Args, args[1:]) {
		t.Fatal(value.Args)
	}
}
