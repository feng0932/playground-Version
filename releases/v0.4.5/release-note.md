# v0.4.5 中文发版说明

## 1. 这个版本做了什么

`v0.4.5` 这次不是什么新功能版，主要就是把两个老问题真正收住。

第一件事，是让派发真的生效。

之前经常出现一种假派发：`00` 总控嘴上说已经把事情派给 `01` 或 `10`，但实际对话还停在 root 窗口里继续演。看起来像切过去了，其实没有。

这版改完后，规则收紧成三句话：

1. `00` 只负责判断和派发。
2. 只有真的切到 `01` 或 `10` 对应窗口后，后续对话才算由它们正式接管。
3. 如果窗口不对，还硬调 `window_continue`，会直接被拦住。

第二件事，是让安装真的能用。

之前新机器上会出现一种很差的情况：表面安装成功了，但一跑 runtime 就因为缺 `yaml` 这类依赖直接崩掉。

这版解决的不是“能不能装上”，而是“装完以后能不能真的跑起来”。

一句话概括就是：

> `v0.4.5` 解决的是“派发必须是真的，安装必须能用”。

## 2. 让大模型去安装和更新的提示词

如果对方设备不明确，先问清楚三件事：

1. 是 `macOS` 还是 `Windows`
2. 用的是 `bash/zsh` 还是 `PowerShell`
3. 当前机器有没有网络和文件写权限

### 新安装

#### macOS

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。

执行命令：
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.5 2>&1 | tee /tmp/ai-team-install-v0.4.5.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true
ls -la .ai-team/state 2>/dev/null || true

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.5.log 的关键片段
```

#### Windows

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.5.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.5 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.5.log"

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue
Get-ChildItem .ai-team\\state -Force -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.5.log 的关键片段
```

### 更新

#### macOS

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

执行命令：
which ai-team || true
ai-team doctor || true
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.5 2>&1 | tee /tmp/ai-team-update-v0.4.5.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team doctor
ai-team install --project-root .
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的完成了更新
- 更新前后的 which ai-team
- 更新前后的 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.5.log 的关键片段
```

#### Windows

```text
你现在要在本机实际执行 ai-team v0.4.5 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

执行命令：
where.exe ai-team
ai-team doctor
$script = Join-Path $env:TEMP "install-ai-team-v0.4.5.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.5 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.5.log"

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor
ai-team install --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了更新
- 更新前后的 where.exe ai-team
- 更新前后的 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.5.log 的关键片段
```
