package contextview_test

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/s-charvin/ai-delivery-kit/internal/delivery/contextview"
)

func TestFrozenPythonFnmatchcaseCorpus(t *testing.T) {
	body, err := os.ReadFile("testdata/fnmatchcase.json")
	if err != nil {
		t.Fatal(err)
	}
	var corpus struct {
		Cases []struct {
			Pattern, Name string
			Match         bool
		}
	}
	if err := json.Unmarshal(body, &corpus); err != nil {
		t.Fatal(err)
	}
	for _, row := range corpus.Cases {
		if got := contextview.Match(row.Pattern, row.Name); got != row.Match {
			t.Errorf("Python 差分: %q %q got=%v want=%v", row.Pattern, row.Name, got, row.Match)
		}
	}
}

func TestPythonFnmatchcaseSemantics(t *testing.T) {
	cases := []struct {
		pattern, name string
		want          bool
	}{{"src/*", "src/deep/.hidden.go", true}, {"src/?", "src/中", true}, {"src/?", "src/中文", false}, {"*", ".hidden/file", true}, {"*.GO", "x.go", false}, {"[!a-c]", "中", true}, {"[]]", "]", true}, {"[z-a]", "z", false}, {"[!z-a]", "z", true}, {"[", "[", true}, {"src/**", "src/", true}, {"a\\b", "a\\b", true}, {"[a-c]", "b", true}, {"[a-c]", "d", false}, {"*\n*", "a\nb", true}}
	for _, c := range cases {
		if got := contextview.Match(c.pattern, c.name); got != c.want {
			t.Errorf("Match(%q,%q)=%v", c.pattern, c.name, got)
		}
	}
}
