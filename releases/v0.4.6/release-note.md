# v0.4.6 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.6` 这次不是换一套新话术，而是把 `v0.4.5` 现场继续暴露的问题收回到正式规则、门禁和测试里。

第一，派发后谁接人要清楚。

之前的问题是：`00` 说已经派发，但后续对话容易又回到 `00` 代演，用户看起来还要理解额外控制动作。

这版改完后，规则变成了：

1. `00` 负责总控、判路、显式派发、收回和重判。
2. `01 / 10` 被 `00` 派发后，必须由 Codex 真实创建子 agent 接管，不能再把 child prompt 给 `00` 自己代演。
3. 其他子 agent 仍要显式派发，但不能对人。
4. `01 / 10` 完成后，把结果交回 `00`。

也就是说，`dispatch_allowed` 只表示“可以派发”，不再表示“root 线程已经接人成功”；真正的成功证据要看会话记录里有没有匹配的 `spawn_agent` 调用，以及同一个 `call_id` 后续成功返回的 `function_call_output.agent_id`。

第二，`10` 要先把人的想法问出来。

进入 PRD 正文或原型链前，`10` 必须收齐 4 组信息：

1. 核心问题与成功标准
2. 本轮做什么 / 不做什么
3. 主链 / 分支 / 异常 / 恢复
4. 页面 / 状态 / 字段 / 验收

任何一组没收齐，都不能继续往下收口。

第三，原型设计前要先做轻量低保真确认。

固定顺序是：

> 聊天内低保真预演 -> 人确认 -> 最小正式回执 -> 才能进原型设计

这里的低保真不是完整设计稿，也不是再加一轮重流程。它只是一张或一段在聊天里能看懂的页面雏形，例如页面块图、线框块图、ASCII 页面草图。页面清单、状态清单、文字提纲不能冒充低保真预演。

第四，原型交付要回到“能打开、能看、能对照”的边界。

原型专家交付的东西必须像用户真正要看的页面，而不是说明文、检查清单或内部字段展示。页面结构要跟本轮确认过的主链和低保真一致；如果做不到，就不能把解释型原型说成正式原型。

如果只用一句话概括 `v0.4.6`：

> 这版解决的是“派发后有人接、产品先问清、原型前先确认、交付出来的是可看的原型”。

本版当前是发版前候选说明。只有完成合并、导出、internal/Gitea 远端投影更新，以及 raw install / doctor / runtime 最小验证后，才能把状态改成“已发布”。fresh live transcript 还没有补齐，所以不能说 Mac / Windows 现场问题已经被新 transcript 证明解决。

## 2. 让大模型去安装和更新的提示词

设备选择：

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。

执行命令：
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.6 2>&1 | tee /tmp/ai-team-install-v0.4.6.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true
ls -la .ai-team/state 2>/dev/null || true

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.6.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.6.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.6 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.6.log"

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue
Get-ChildItem .ai-team\\state -Force -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.6.log 的关键片段
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.6 2>&1 | tee /tmp/ai-team-update-v0.4.6.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的完成了更新
- 更新前后的 which ai-team
- 更新前后的 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.6.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root . *>&1
$script = Join-Path $env:TEMP "install-ai-team-v0.4.6.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.6 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.6.log"

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了更新
- 更新前后的 where.exe ai-team
- 更新前后的 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.6.log 的关键片段
```
