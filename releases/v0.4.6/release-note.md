# v0.4.6 中文发版说明

## 0. 版本定位

`v0.4.6` 是 `v0.4.5` 之后的稳定线候选，目标是把现场暴露出的控制链和原型交付边界问题收回到 published truth、runtime gate 和测试里。

这份 release note 是发版说明主编辑源。远端资产上传、公开 stable pointer 同步、install / doctor / runtime 验证完成前，它只能作为发版准备说明，不能单独证明正式发布完成。

## 1. 这个版本做了什么 / 本次变化

`v0.4.6` 这次先收住三件事：

第一件事，是把 `v0.4.5` 后加进正式链路的 hidden activation / unlock / window 私加层退掉。

这版冻结后的主链重新回到人原来要的口径：

1. `00` 只负责总控、判路、显式派发、收回和重判。
2. `01 / 10` 被 `00` 显式派发后，直接对人。
3. 除了 `01 / 10`，其他子 agent 仍要显式派发，但不能对人。
4. `01 / 10` 结束后，把结果交回 `00`。

第二件事，是把 `10` 的主问职责做成硬门。

进入模块正文或原型链前，`10` 必须收齐 4 组信息：

1. 核心问题与成功标准
2. 本轮做什么 / 不做什么
3. 主链 / 分支 / 异常 / 恢复
4. 页面 / 状态 / 字段 / 验收

任何一组没收齐，都不能进入 PRD 正文收口，也不能进入原型前确认。

第三件事，是把原型前低保真做成确认门。

固定顺序是：

> 聊天内低保真预演 -> 人确认 -> 最小正式回执 -> 才能进原型设计

低保真必须是更像页面的粗稿，例如页面块图、线框块图、ASCII 页面草图；只给页面清单、状态清单、文字提纲不算完成。

本次冻结候选合并还审掉了旧 `stable-release.json` 的包 hash。旧 hash 不能继续代表当前冻结候选内容。

旧 hash：

- `bundle_sha256`
  - `8154233f2d92cb44c8c49dae8c2d9820c529d850048a3dd85ea54ab7e5ee3de0`
- `installer_archive_sha256`
  - `bffe6e919e0526b94f30945f205a06b722698d89dad73b0bd99494a296cbe78d`

当前本地重新构建后的 hash：

- `bundle SHA256`
  - `e2228479d1b0241d920e01d00d22355c4ce551a6c13d682258ee5eb3121fb2af`
- `installer archive SHA256`
  - `bfcd7cdaf8d64bec05dcdecb47f0842295a8300fa35c1b924d707dab5a6a4372`

当前准确口径：

- `v0.4.6` 已形成 repo-local 冻结候选。
- tracked `stable-release.json` 已按当前本地构建重算 hash。
- 远端 release 资产还没有在本轮被上传验证。
- fresh live transcript 还没有在本轮补齐。

不能把这份文件说成：

> `v0.4.6` 已正式远端发布，或者已经 `live-thread verified`。

## 2. 让大模型去安装和更新的提示词

### 不包含内容

本版本说明不包含下面结论：

1. 不声明 fresh live transcript 已通过。
2. 不声明 Mac / Windows 现场问题已经被真实新包证明解决。
3. 不把仓内 published truth 合入说成远端正式发布完成。
4. 不把 release note 当成 bundle 真源；bundle 真源仍是 `dev/install/default_bundle/`。

### 正式发版结果

当前发版准备结果：

1. 开发仓 `main` 已包含 `v0.4.6` 包 A 和包 B 的源码状态。
2. 本地 release 五件套已重新构建。
3. tracked `stable-release.json` 已由 builder 反写为当前 hash。

仍需完成后才能宣称正式发版完成：

1. 发布仓远端 `releases/v0.4.6/` 资产可访问。
2. 发布仓远端根级 `stable-release.json` 可访问且指向当前 hash。
3. install / doctor / runtime 最小验证通过。

下面提示词只能在远端 `releases/v0.4.6/` 资产上传、公开 `stable-release.json` 同步、远端抽样验证通过后使用。

如果对方设备不明确，先问清楚三件事：

1. 是 `macOS` 还是 `Windows`
2. 用的是 `bash/zsh` 还是 `PowerShell`
3. 当前机器有没有网络和文件写权限

### 给大模型的新安装提示词

#### macOS

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

### 给大模型的更新提示词

#### macOS

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式更新，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

更新前先执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true

执行命令：
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

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式更新，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

更新前先执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root . *>&1

执行命令：
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
