# ai-team-bundle v0.4.6 版本说明

`v0.4.6` 只做一件事：把 `v0.4.5` 里后加进去的“偷偷激活窗口”那层拿掉，收回到原来要的主链上，同时把安装后的 runtime 和当前版本真正对齐。

## 版本定位

- `v0.4.6` 不是继续给 `01 / 10` 补更多话术，而是把显式派发、真实接管、安装后 runtime 对齐这三件事收回到原来的正式主链上。
- 这一版保留 `00 -> 01 / 10 -> 00` 的主链，保留 `window_continue`，但把它收回到“只负责续轮”的语义。

## 这个版本做了什么

### 1. 派发必须是真的派发

- `00` 还是唯一总入口，但它只负责判断、显式派发、收回回执和重判。
- `01 / 10` 只有收到 `00` 的显式派发后，才算真正接管。
- 不再允许靠 hidden activation / unlock 这一层，在主线程里假装已经切到子窗口。

### 2. `window_continue` 只负责续轮，不再负责偷切窗

- `window_continue` 继续保留，但语义收回到 continuation-only。
- 如果当前窗口没 materialize，或者当前重建出来的窗口和原 snapshot 对不上，就直接回 `/总控` 重新派发。
- 这次要收住的不是“多一层话术”，而是“续轮只能续原来的可信窗口，不能借续轮偷换窗口”。

### 3. 安装后的 runtime 结构真正回到当前版本

- 修掉了“机器 launcher 升了，但项目 runtime 还停在旧版本结构里”的问题。
- 现在 `ai-team runtime --action total_control_entry` 和 `ai-team runtime --action window_continue` 都按当前版本结构落地。
- `ai-team doctor` 能看到 machine launcher 和项目 runtime 都对齐到当前版本链路。

### 4. 这版已经验证到哪里

本轮至少已经通过：

```bash
cd /Users/mac/Documents/Playground-English/dev
python3 -m unittest tests.test_release_bundle -q
python3 -m unittest tests.test_bootstrap_smoke -q
python3 -m unittest tests.test_default_bundle -q
```

结果：

- `tests.test_release_bundle`：`15 / 15` 通过
- `tests.test_bootstrap_smoke`：`5 / 5` 通过
- `tests.test_default_bundle`：`204 / 204` 通过

### 5. 这版暂不包含什么

- 不包含 `historical_project` 正向 classifier 闭环。
- 不包含 live transcript 的最新现场补证。
- 不包含新的 worker 直连对人能力。

## 正式发版结果

- 当前正式目标版本：`v0.4.6`
- 当前验证结果：
  - `tests.test_release_bundle`：`15 / 15` 通过
  - `tests.test_bootstrap_smoke`：`5 / 5` 通过
  - `tests.test_default_bundle`：`204 / 204` 通过

正式远端安装入口：

- stable pointer：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/stable-release.json`
- macOS 安装入口：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh`
- Windows 安装入口：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1`
- release metadata URL：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/releases/v0.4.6/ai-team-bundle-v0.4.6.release.json`

## 给大模型的继续执行提示

- 继续执行前先读：
  - `README.md`
  - `install/stable-release.json`
  - `docs/releases/ai-team-bundle-v0.4.6-release-note.md`
- 不要误判：
  - `install/default_bundle/` 是当前 bundle 真源
  - `install/stable-release.json` 是开发仓跟踪的 stable pointer 真源
  - `/Users/mac/Documents/playground-Version/` 只承接发布投影
- 当前正式状态：
  - `v0.4.6` 的本地构建与回归已转绿
  - 下一步是正式 build、导出 `releases/v0.4.6/`、切 stable pointer、同步 tag 和 release 页面

## 给大模型的新安装提示词（v0.4.6）

### macOS

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

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
- 是否真的执行了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.6.log 的关键片段
```

### Windows

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.6.ps1"
Invoke-WebRequest -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
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
- 是否真的执行了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.6.log 的关键片段
```

## 给大模型的更新提示词（v0.4.6）

### macOS

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 更新前先采集旧状态。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新后继续执行校验命令，并输出结果。
6. 如果任一步失败，立即停止。

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
- 是否真的执行了更新
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.6.log 的关键片段
```

### Windows

```text
你现在要在本机实际执行 ai-team v0.4.6 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 更新前先采集旧状态。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新后继续执行校验命令，并输出结果。
6. 如果任一步失败，立即停止。

更新前先执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root . *>&1

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.6.ps1"
Invoke-WebRequest -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
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
- 是否真的执行了更新
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.6.log 的关键片段
```
