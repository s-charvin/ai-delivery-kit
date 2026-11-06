package cli

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/s-charvin/ai-delivery-kit/internal/bootstrap"
	"github.com/s-charvin/ai-delivery-kit/internal/initflow"
	"github.com/s-charvin/ai-delivery-kit/internal/repo"
	"github.com/s-charvin/ai-delivery-kit/internal/version"
)

type initRunner interface {
	Run(ctx context.Context, input initflow.Input) (initflow.Result, error)
}

type App struct {
	stdin      io.Reader
	stdout     io.Writer
	stderr     io.Writer
	initRunner initRunner
}

func New(stdout, stderr io.Writer) *App {
	return &App{
		stdin:  os.Stdin,
		stdout: stdout,
		stderr: stderr,
	}
}

func (a *App) Run(args []string) int {
	if len(args) == 0 {
		a.printUsage()
		return 2
	}

	switch args[0] {
	case "help", "--help", "-h":
		a.printUsage()
		return 0
	case "validate":
		return a.runValidate(args[1:])
	case "hook":
		return a.runHook(args[1:])
	case "context":
		return a.runContext(args[1:])
	case "check":
		return a.runCheck(args[1:])
	case "advance":
		return a.runAdvance(args[1:])
	case "archive":
		return a.runArchive(args[1:])
	case "run":
		return a.runNative(args[1:])
	case "evidence":
		return a.runEvidence(args[1:])
	case "info":
		return a.runInfo(args[1:])
	case "version":
		if len(args) != 1 {
			return a.checkError(fmt.Errorf("version 不接受参数"), 2)
		}
		_, _ = fmt.Fprintln(a.stdout, version.String())
		return 0
	case "init":
		return a.runInit(args[1:])
	case "upgrade":
		if len(args) != 1 {
			return a.checkError(fmt.Errorf("upgrade 仅提供更新指引；项目刷新使用 init --upgrade"), 2)
		}
		return a.runUpgrade()
	case "ide-gates":
		return a.runIDEGates(args[1:])
	default:
		a.printUsage()
		return 2
	}
}

// ---------------------------------------------------------------------------
// init
// ---------------------------------------------------------------------------

func (a *App) runInit(args []string) int {
	targetPath := ""
	upgrade := false
	resetData := ""

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--upgrade":
			upgrade = true
		case "--upgrade-policy":
			_, _ = fmt.Fprintln(a.stderr, "--upgrade-policy 已移除；当前版本不执行自动迁移。\n"+bootstrap.UpgradeInstructions())
			return 2
		case "--reset-data":
			resetData = ".ai-delivery"
		default:
			if strings.HasPrefix(args[i], "--reset-data=") {
				resetData = strings.TrimPrefix(args[i], "--reset-data=")
				if resetData == "" {
					_, _ = fmt.Fprintln(a.stderr, "--reset-data 目录不能为空")
					return 2
				}
				continue
			}
			if strings.HasPrefix(args[i], "-") {
				_, _ = fmt.Fprintf(a.stderr, "Unknown argument: %s\n", args[i])
				return 2
			}
			if targetPath == "" {
				targetPath = args[i]
			} else {
				_, _ = fmt.Fprintf(a.stderr, "Unknown argument: %s\n", args[i])
				return 2
			}
		}
	}
	if resetData != "" && !upgrade {
		_, _ = fmt.Fprintln(a.stderr, "--reset-data requires --upgrade")
		return 2
	}

	if targetPath == "" {
		var err error
		targetPath, err = os.Getwd()
		if err != nil {
			_, _ = fmt.Fprintln(a.stderr, err)
			return 2
		}
	}

	runner := a.initRunner
	if runner == nil {
		runner = initflow.Service{
			Bootstrapper: bootstrap.Engine{},
			Discover:     repo.Discover,
			Progress:     a.stdout,
		}
	}

	result, err := runner.Run(context.Background(), initflow.Input{
		TargetPath: targetPath,
		Upgrade:    upgrade,
		ResetData:  resetData,
	})
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 2
	}

	if result.Upgraded {
		_, _ = fmt.Fprintf(a.stdout, "Upgraded ai-delivery managed assets in %s\n", result.RepoRoot)
	} else {
		_, _ = fmt.Fprintf(a.stdout, "Initialized ai-delivery in %s\n", result.RepoRoot)
	}
	a.printIDEGateAmendHint(result.IDEGateAmend)
	if resetData != "" {
		_, _ = fmt.Fprintf(a.stdout, "备份重建完成（未迁移旧任务）。\n旧根：%s\n新根：%s\n完整备份：%s\n旧原件：%s\n受管目标：%s\n恢复：查看备份 manifest.json；将 files/ 内路径恢复到项目根。type=absent 表示原先不存在，请核对后自行撤回。备份不会自动清理。\n", result.DataReset.SourceRoot, result.DataReset.TargetRoot, result.DataReset.BackupDir, result.DataReset.OriginalDir, strings.Join(result.DataReset.Targets, ", "))
	}
	return 0
}

func (a *App) printIDEGateAmendHint(report bootstrap.AmendReport) {
	if report.Empty() {
		return
	}
	_, _ = fmt.Fprintf(a.stdout, "Amended IDE gate config(s): %s\n", strings.Join(report.Files, ", "))
	_, _ = fmt.Fprintf(a.stdout, "Backup: %s\n", report.BackupDir)
	_, _ = fmt.Fprintf(a.stdout, "Restore: ai-delivery ide-gates restore --to %s %s\n", report.BackupStamp, shellArgument(filepath.Dir(filepath.Dir(filepath.Dir(report.BackupDir)))))
}

// ---------------------------------------------------------------------------
// upgrade
// ---------------------------------------------------------------------------

func (a *App) runUpgrade() int {
	_, _ = fmt.Fprintln(a.stdout, "请下载并替换所选发行的 ai-delivery 程序（或运行可选安装脚本指定版本）。程序更新不改项目；需要刷新项目资源时显式运行 ai-delivery init --upgrade <项目路径>。")
	return 0
}

// ---------------------------------------------------------------------------
// ide-gates
// ---------------------------------------------------------------------------

func (a *App) runIDEGates(args []string) int {
	if len(args) == 0 {
		a.printIDEGatesUsage()
		return 1
	}
	switch args[0] {
	case "list":
		return a.runIDEGatesList(args[1:])
	case "restore":
		return a.runIDEGatesRestore(args[1:])
	default:
		a.printIDEGatesUsage()
		return 1
	}
}

func (a *App) runIDEGatesList(args []string) int {
	repoRoot, err := a.resolveRepoRoot(args)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}
	hint, hintErr := a.deliveryHint(repoRoot, args)
	if hintErr != nil {
		fmt.Fprintln(a.stderr, hintErr)
		return 1
	}
	stamps, err := bootstrap.ListIDEGateBackups(repoRoot, hint)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}
	if len(stamps) == 0 {
		_, _ = fmt.Fprintln(a.stdout, "No IDE gate backups found.")
		return 0
	}
	for _, stamp := range stamps {
		_, _ = fmt.Fprintln(a.stdout, stamp)
	}
	return 0
}

func (a *App) runIDEGatesRestore(args []string) int {
	stamp := ""
	var positional []string
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--to":
			if i+1 >= len(args) {
				_, _ = fmt.Fprintln(a.stderr, "Missing value for --to")
				return 1
			}
			i++
			stamp = args[i]
		default:
			positional = append(positional, args[i])
		}
	}

	repoRoot, err := a.resolveRepoRoot(positional)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}

	hint, hintErr := a.deliveryHint(repoRoot, positional)
	if hintErr != nil {
		fmt.Fprintln(a.stderr, hintErr)
		return 1
	}
	if stamp == "" {
		stamps, listErr := bootstrap.ListIDEGateBackups(repoRoot, hint)
		if listErr != nil {
			_, _ = fmt.Fprintln(a.stderr, listErr)
			return 1
		}
		if len(stamps) == 0 {
			_, _ = fmt.Fprintln(a.stderr, "No IDE gate backups found.")
			return 1
		}
		stamp = stamps[0]
	}

	report, err := bootstrap.RestoreIDEGateBackup(repoRoot, stamp, nil, hint)
	if err != nil {
		_, _ = fmt.Fprintln(a.stderr, err)
		return 1
	}
	_, _ = fmt.Fprintf(a.stdout, "Restored IDE gate config from %s\n", stamp)
	if !report.Empty() {
		_, _ = fmt.Fprintf(a.stdout, "Pre-restore backup: %s\n", report.BackupDir)
		_, _ = fmt.Fprintf(a.stdout, "Undo restore: ai-delivery ide-gates restore --to %s %s\n", report.BackupStamp, shellArgument(filepath.Dir(filepath.Dir(filepath.Dir(report.BackupDir)))))
	}
	return 0
}

func (a *App) resolveRepoRoot(args []string) (string, error) {
	target := ""
	if len(args) > 0 {
		target = args[0]
	}
	if target == "" {
		cwd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		target = cwd
	}
	info, err := repo.Discover(target)
	if err != nil {
		return "", err
	}
	return info.Root, nil
}

func (a *App) printIDEGatesUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery ide-gates <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  list                 List IDE gate backup timestamps (newest first)")
	_, _ = fmt.Fprintln(a.stderr, "  restore [--to <ts>]  Restore amendable IDE gate JSON from a backup")
	_, _ = fmt.Fprintln(a.stderr, "                       Defaults to the newest backup when --to is omitted.")
}

func (a *App) printUsage() {
	_, _ = fmt.Fprintln(a.stderr, "Usage: ai-delivery <command>")
	_, _ = fmt.Fprintln(a.stderr, "")
	_, _ = fmt.Fprintln(a.stderr, "Commands:")
	_, _ = fmt.Fprintln(a.stderr, "  version     Print the CLI version")
	_, _ = fmt.Fprintln(a.stderr, "  validate    校验 status/layout/skills/sources/api-policy")
	_, _ = fmt.Fprintln(a.stderr, "  hook        默认复用 check；--host codex --event SessionStart|PreToolUse 使用原生 stdin/JSON")
	_, _ = fmt.Fprintln(a.stderr, "  context     读取角色与范围所需正文（不授予动作权限）")
	_, _ = fmt.Fprintln(a.stderr, "  check       只读检查当前动作与完整证据闭包")
	_, _ = fmt.Fprintln(a.stderr, "  advance     重评当前门禁并受控推进切片状态")
	_, _ = fmt.Fprintln(a.stderr, "  archive     明确用户确认后归档；必要输出成功后才发布终态")
	_, _ = fmt.Fprintln(a.stderr, "  run         执行当前设计绑定的原生命令并保存真实收据")
	_, _ = fmt.Fprintln(a.stderr, "  evidence    计算输入 fingerprint 或 verification review-digest")
	_, _ = fmt.Fprintln(a.stderr, "  info        查询当前程序、资源身份与可用能力")
	_, _ = fmt.Fprintln(a.stderr, "  init        Initialize ai-delivery in a target repository")
	_, _ = fmt.Fprintln(a.stderr, "              Use: ai-delivery init [--upgrade [--reset-data[=relative/old-root]]] [/path/to/repo]")
	_, _ = fmt.Fprintln(a.stderr, "              Defaults to current directory if no path is given.")
	_, _ = fmt.Fprintln(a.stderr, "  upgrade     Show separate program update and explicit project resource refresh instructions")
	_, _ = fmt.Fprintln(a.stderr, "  ide-gates   List/restore IDE gate config backups")
}

func (a *App) deliveryHint(root string, args []string) (string, error) {
	target := ""
	if len(args) > 0 {
		target = args[0]
	}
	return bootstrap.DeliveryPathHint(root, target)
}

func shellArgument(text string) string { return "'" + strings.ReplaceAll(text, "'", "'\"'\"'") + "'" }
