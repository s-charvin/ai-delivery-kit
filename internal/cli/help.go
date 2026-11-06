package cli

import "flag"

// 帮助只投影当前 FlagSet，不读取项目或产生动作判断。
func (a *App) commandHelp(flags *flag.FlagSet, usage string, notes []string, choices map[string][]string) int {
	type option struct {
		Name    string   `json:"name"`
		Usage   string   `json:"usage"`
		Default string   `json:"default"`
		Choices []string `json:"choices,omitempty"`
	}
	options := []option{}
	flags.VisitAll(func(f *flag.Flag) {
		options = append(options, option{f.Name, f.Usage, f.DefValue, choices[f.Name]})
	})
	return a.deliveryJSON(struct {
		Command string   `json:"command"`
		Usage   string   `json:"usage"`
		Options []option `json:"options"`
		Notes   []string `json:"notes"`
	}{flags.Name(), usage, options, notes}, 0)
}
