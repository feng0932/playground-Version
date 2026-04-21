# ai-team-bundle v0.4.1 版本说明

`v0.4.1` 是基于 `v0.4.0` 的正式 patch 版本。

如果用一句话概括这次变化：

**`v0.4.1` 主要把 `v0.4.0` 已完成的修复成果挂到新的正式版本号，并作为当前稳定公开版本发布。**

## 版本定位

- `v0.4.0` 是上一轮结构升级后的正式基线版本。
- `v0.4.1` 是承接该基线修复成果的 patch 版本。
- 新安装与后续更新，默认以 `v0.4.1` 为准。

## 本次变化

### 1. 版本号正式升为 `v0.4.1`

- 当前正式 bundle 版本从 `v0.4.0` 升为 `v0.4.1`。
- 这避免了“内容已变但版本号不变”的发布歧义。

### 2. 稳定安装与更新入口统一切到 `v0.4.1`

- 新安装和更新都应显式使用 `v0.4.1` 的正式 release metadata 与 installer 资产。
- 后续如需校验当前公开稳定版本，也应以 `v0.4.1` 为准。

### 3. `v0.4.1` 正式发布资产已齐备

- tag：`ai-team-bundle-v0.4.1`
- 发布资产：
  - `ai-team-bundle-v0.4.1.tar.gz`
  - `ai-team-bundle-v0.4.1-installer.tar.gz`
  - `ai-team-bundle-v0.4.1.manifest.json`
  - `ai-team-bundle-v0.4.1.release.json`
  - `ai-team-bundle-v0.4.1.sha256`

## 不包含内容

- 不包含新一轮规则、模板、角色边界或流程结构重设计。
- 不包含超出 `v0.4.0` 已确认修复范围的新能力扩面。
- 若需要回看上一轮正式结构升级基线，参考 `v0.4.0`。
- 若需要回查旧稳定线安装、升级与修复行为，参考 `v0.3.11`。

## 正式发版结果

- GitHub Release：
  - `https://github.com/feng0932/playground-Version/releases/tag/ai-team-bundle-v0.4.1`
- 稳定入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/stable-release.json`
- macOS 安装入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh`
- Windows 安装入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1`
- bundle SHA256：
  - `68bd4d0dc2174834967ed7d1260d8dfba9a8389c679b3c85db2f18a5f978013a`
- installer archive SHA256：
  - `367672e3c9ff73b4ea129bfe93de04870630ffd90a1f88bc0c2a26d29ba8ce74`

## 给大模型的新安装提示词

### macOS

```text
你现在要在本机执行 ai-team v0.4.1 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，停止并报告失败点，不要脑补成功。

执行命令：
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash -s -- v0.4.1 2>&1 | tee /tmp/ai-team-install-v0.4.1.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true
ls -la .ai-team/state 2>/dev/null || true

最终必须输出：
- 是否真的执行了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.1.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.1 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，停止并报告失败点，不要脑补成功。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.1.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.1 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.1.log"

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team/runtime.json -ErrorAction SilentlyContinue
Get-ChildItem .ai-team/state -Force -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的执行了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.1.log 的关键片段
```

## 给大模型的更新提示词

### macOS

```text
你现在要在本机执行 ai-team v0.4.1 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 更新前后都要执行校验命令，并输出结果。
5. 如果任一步失败，停止并报告失败点，不要脑补成功。

更新前状态采样：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true

执行命令：
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash -s -- v0.4.1 2>&1 | tee /tmp/ai-team-update-v0.4.1.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true
ls -la .ai-team/state 2>/dev/null || true

最终必须输出：
- 是否真的执行了更新
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际更新到的 bundle_version / release_tag
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.1.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.1 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 更新前后都要执行校验命令，并输出结果。
5. 如果任一步失败，停止并报告失败点，不要脑补成功。

更新前状态采样：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team 2>$null
try { ai-team doctor --project-root . } catch {}

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.1.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.1 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.1.log"

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team/runtime.json -ErrorAction SilentlyContinue
Get-ChildItem .ai-team/state -Force -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的执行了更新
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际更新到的 bundle_version / release_tag
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.1.log 的关键片段
```
