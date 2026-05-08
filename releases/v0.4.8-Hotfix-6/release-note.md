# v0.4.8-Hotfix-6 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8-Hotfix-6` 修复 Hotfix-5 发布后暴露的 `01` 回执合同消费阻断。

Hotfix-5 已经把 `02-编排-安装与运行检查` 从正式 opening 主链降级，最新现场证明这部分已经生效：fresh `/总控` 不再派发 `02`，而是进入 `01-编排-初始化项目包`。新的阻断发生在 `01` 回执返回后：`01` 把目标清单写成 JSON 数组风格的单行文本，并把 `formal_targets_write_authorized` 写成 `true`；旧 validator 无法把这些字段规范化为正式目标清单，于是 `/读取回执` fail-closed，无法进入 `10-执行-产品专家`。

Hotfix-6 修复了这条真实断边：runtime 现在能消费 JSON 数组风格的目标清单，把 `[]` 正确识别为空清单，并且只有在同一回执同时提供完整 `authorized_formal_targets / formal_writable_targets` 明细时，才把 `formal_targets_write_authorized=true` 转换为六个正式宿主的授权目标清单。业务门禁没有放松：项目包六宿主、执行结构和模块 PRD 事实源仍然必须满足后才能派发 `10`。

本版还在 `01` prompt 中明确：`formal_targets_write_authorized` 是目标清单字段，不是布尔字段；后续子 agent 应直接写六个正式宿主路径，避免再把“全部授权”写成 `true`。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-6 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

前置检查：
1. 确认 shell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-6 2>&1 | tee /tmp/ai-team-install-v0.4.8-Hotfix-6.log

安装后继续运行：

which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了新安装。
2. 实际 bundle_version / release_tag。
3. doctor 的 machine_vs_project / risk_level / recommended_action。
4. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
5. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
6. 安装主输出是否对人友好，并贴出安装完成后的主输出片段。
7. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
8. 是否错误派发 02；若派发 02，必须判定失败。
9. 若已经生成 01 回执，继续执行 /读取回执，并核对是否能进入 10-执行-产品专家。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-6 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

前置检查：
1. 确认 PowerShell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-6.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-6 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-install-v0.4.8-Hotfix-6.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续运行：

where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了新安装。
2. 实际 bundle_version / release_tag。
3. doctor 的 machine_vs_project / risk_level / recommended_action。
4. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
5. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
6. 安装主输出是否对人友好，并贴出安装完成后的主输出片段。
7. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
8. 是否错误派发 02；若派发 02，必须判定失败。
9. 若已经生成 01 回执，继续执行 /读取回执，并核对是否能进入 10-执行-产品专家。
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-6 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

前置检查：
1. 确认 shell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

更新前先采集：

which ai-team || true
ai-team doctor --project-root . || true

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-6 2>&1 | tee /tmp/ai-team-update-v0.4.8-Hotfix-6.log

更新后继续运行：

which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了更新，并输出更新前后的 bundle_version / release_tag 对照。
2. 更新后 doctor 的 machine_vs_project / risk_level / recommended_action。
3. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
4. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
5. 更新主输出是否对人友好，并贴出安装完成后的主输出片段。
6. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
7. 是否错误派发 02；若派发 02，必须判定失败。
8. 若已经生成 01 回执，继续执行 /读取回执，并核对是否能进入 10-执行-产品专家。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-6 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

前置检查：
1. 确认 PowerShell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

更新前先采集：

where.exe ai-team
ai-team doctor --project-root .

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-6.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-6 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-update-v0.4.8-Hotfix-6.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

更新后继续运行：

where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了更新，并输出更新前后的 bundle_version / release_tag 对照。
2. 更新后 doctor 的 machine_vs_project / risk_level / recommended_action。
3. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
4. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
5. 更新主输出是否对人友好，并贴出安装完成后的主输出片段。
6. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
7. 是否错误派发 02；若派发 02，必须判定失败。
8. 若已经生成 01 回执，继续执行 /读取回执，并核对是否能进入 10-执行-产品专家。
```
