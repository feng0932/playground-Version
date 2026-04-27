# ai-team-bundle v0.4.5 版本说明

## 版本定位

`v0.4.5` 不是重开控制面的一版，而是把 `00 -> 01 / 10` 真实接管链和正式安装链一起收住的一版。

这一版重点只有两个：

1. 派发必须是真的，不能再停留在 root 窗口代演。
2. 安装必须能用，不能再出现“装上了，一跑 runtime 就崩”的情况。

## 本次变化

### 1. `00` 只负责判断和派发

- `00` 不再嘴上说“已经切到 `01 / 10`”，但实际还留在当前窗口继续演。
- 只有真的切到 `01-编排-初始化项目包` 或 `10-执行-产品专家` 对应窗口后，后续对话才算由它们正式接管。
- wrong host 硬调 `window_continue` 仍会被固定拦截为：`当前不是对人窗口。`

### 2. `00 -> 01 -> 10` 的最小真实接管链已经打通

- `total_control_entry -> window_continue(01) -> read_receipt -> window_continue(10)` 现在能按正式链路跑通。
- 这次解决的不是“提示词写得更像派发”，而是“系统真的切到了对应窗口”。

### 3. 新装环境现在能直接跑 runtime

- 之前新机器上会有“install 看起来成功，但 runtime 因为缺 `yaml` 直接崩掉”的问题。
- 这一版把 installer/runtime 链补齐了，目标从“能装”提升到“装完真的能跑”。

## 不包含内容

- 不包含新的控制面重设计。
- 不包含新的对人窗口。
- 不包含 worker 直接对人的新能力。
- 不包含 `VSCode / Codex / 宿主 UI` 修改。

## 正式发版结果

- 当前正式对外可用入口仍然是内网版本仓 `playground-Version` 的 raw 地址。
- 当前重新 build 并导出的仍然是同一组 `v0.4.5` 正式产物。
- 当前 release metadata 关键校验值：
  - `bundle SHA256`：
    - `0b6d7719e7bd7d35b255da315934bee4f6a15ec51156fe932abb00baa1fb0453`
  - `installer archive SHA256`：
    - `3bb13fd4100a9a602b2f87b1afa14baaa8585b582e5aca9fb1cc706ce27838a7`

正式远端安装入口：

- stable pointer：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/stable-release.json`
- macOS 安装脚本：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh`
- Windows 安装脚本：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1`
- release metadata：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/releases/v0.4.5/ai-team-bundle-v0.4.5.release.json`

## 给大模型的新安装提示词（v0.4.5）

设备选择：

- `macOS`：用下面的 `macOS` 提示词。
- `Windows`：用下面的 `Windows` 提示词。
- 不确定设备：先问“你现在是 `macOS` 还是 `Windows`？可用的是 `bash/zsh` 还是 `PowerShell`？”，确认后再发对应提示词。

### macOS

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
curl -fsSL \
  http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh \
  | bash -s -- v0.4.5 2>&1 | tee /tmp/ai-team-install-v0.4.5.log

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
- /tmp/ai-team-install-v0.4.5.log 的关键片段
```

### Windows

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.5.ps1"
Invoke-WebRequest -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.5 *>&1 |
  Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.5.log"

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue
Get-ChildItem .ai-team\\state -Force -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的执行了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.5.log 的关键片段
```

## 给大模型的更新提示词（v0.4.5）

设备选择：

- `macOS`：用下面的 `macOS` 更新提示词。
- `Windows`：用下面的 `Windows` 更新提示词。
- 不确定设备：先问“你现在是 `macOS` 还是 `Windows`？可用的是 `bash/zsh` 还是 `PowerShell`？”，确认后再发对应提示词。

### macOS

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态：which ai-team、ai-team doctor || true。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新后继续执行校验命令，并输出更新前后对照。
6. 如果任一步失败，立即停止。

执行命令：
which ai-team || true
ai-team doctor || true
curl -fsSL \
  http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh \
  | bash -s -- v0.4.5 2>&1 | tee /tmp/ai-team-update-v0.4.5.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team doctor
ai-team install --project-root .
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的执行了更新
- 更新前后的 which ai-team
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.5.log 的关键片段
```

### Windows

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态：where.exe ai-team、ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新后继续执行校验命令，并输出更新前后对照。
6. 如果任一步失败，立即停止。

执行命令：
where.exe ai-team
ai-team doctor
$script = Join-Path $env:TEMP "install-ai-team-v0.4.5.ps1"
Invoke-WebRequest -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.5 *>&1 |
  Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.5.log"

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor
ai-team install --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的执行了更新
- 更新前后的 where.exe ai-team
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.5.log 的关键片段
```
