package mutation

import (
	"context"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"testing"
)

func TestInvalidTargetAndMissingIdentityNeverReadOrWrite(t *testing.T) {
	for _, tc := range [][2]string{{"archived", "id"}, {"unknown", "id"}, {"in_dev", ""}, {"blocked_verification_failure", "id"}} {
		_, e := Advance(context.Background(), model.Workspace{}, model.Scope{}, tc[0], tc[1], func(context.Context, model.Workspace, model.Scope, model.Action) (model.CheckReport, error) {
			t.Fatal("非法参数触发动作")
			return model.CheckReport{}, nil
		})
		if e == nil {
			t.Fatal(tc)
		}
	}
}
