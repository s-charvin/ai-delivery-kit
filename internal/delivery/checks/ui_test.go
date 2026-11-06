package checks

import (
	"context"
	"path/filepath"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/model"
	"github.com/s-charvin/ai-delivery-kit/internal/delivery/workspace"
)

const uiSlice = ".ai-delivery/requirements/REQ-UI/sub-requirements/SR-001/"

func uiFixture(t *testing.T, name string) model.Snapshot {
	t.Helper()
	root, err := filepath.Abs("../../../tests/migration-oracle/fixtures/" + name)
	if err != nil {
		t.Fatal(err)
	}
	s, err := (workspace.Reader{}).Load(context.Background(), model.Workspace{ProjectRoot: root, DeliveryRoot: filepath.Join(root, ".ai-delivery")}, model.Scope{RequirementID: "REQ-UI", SubrequirementID: "SR-001"}, model.ReadRequest{Action: &model.Action{Intent: "verify"}})
	if err != nil {
		t.Fatal(err)
	}
	return s
}
func TestUIFixedFixturesCollect(t *testing.T) {
	for _, name := range []string{"component-only", "host-runtime"} {
		t.Run(name, func(t *testing.T) {
			s := uiFixture(t, name)
			specs := []model.CheckSpec{{ID: "ui_index", InputPaths: []string{uiSlice + "contracts/ui-truth-index.json"}}, {ID: "ui_acceptance", InputPaths: []string{uiSlice + "visual-acceptance.json"}}}
			got, err := (Reader{}).Collect(context.Background(), s, specs)
			if err != nil {
				t.Fatal(err)
			}
			for _, o := range got.Observations {
				if o.Result != "passed" {
					t.Errorf("%s: %s", o.CheckID, o.Details)
				}
			}
			for _, p := range []string{"lib/profile_card.dart", "test/profile_card_golden_test.dart", "test/goldens/profile-card-default.png", "test/motion/profile-card-default.gif"} {
				if _, ok := got.Snapshot.Document(p); !ok {
					t.Errorf("传递证据未登记 %s", p)
				}
			}
		})
	}
}
