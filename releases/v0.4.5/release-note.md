# ai-team-bundle v0.4.5 版本说明

`v0.4.5` 是承接 `v0.4.4` 的当前正式发布链版本宿主；这一版不重开控制链，而是在既有 `v0.4.5` 发布面上继续收口当前脚本消费版本、stable pointer、版本仓导出面，以及这轮 `00` 只能派发、`01 / 10` 必须真实接管的运行时修复。

如果用一句话概括这次变化：

**`v0.4.5` 的目标不是新增一套发布规则，而是把当前已经验证过的 installer/runtime 主链、`01 / 10` 不漂移目标、真实接管链和内网优先发布面收成同一版本语义，避免继续由旧载体代演。**

## 版本定位

- `v0.4.4` 是上一轮原型前后意图提取增强与 repo-local 发布面收口版本。
- `v0.4.5` 是承接该能力面的正式发布收口版本，重点是把当前分支真实变化与正式发布载体统一到同一版本。
- 这次不新增新的对人窗口，不重开 `00 / 01 / 10 / worker` 控制链，不新增第二条治理链。
- 当前目标是把 bundle 真源、tracked stable pointer、release note、版本仓导出目录与安装入口全部对齐到 `v0.4.5`。

## 本次变化

### 1. 本地 bundle 真源版本升到 `v0.4.5`

- `install/default_bundle/manifest.json` 的 `bundle_version` 切到 `v0.4.5`。
- 本地源码安装语义仍保持 `local-default-bundle`，不把 release 安装身份误写回本地真源。

### 2. 发布窄链从 `v0.4.4` carrier 切到 `v0.4.5`

- tracked `install/stable-release.json` 将以 `v0.4.5` build 产物反写，不再继续由 `v0.4.4` 版本目录代演。
- `tests/test_launch_judgment_narrow_chain.py`、`release note`、`freeze snapshot` 与版本宿主统一切到 `v0.4.5`。
- `dev/current.md`、`dev/version-index.md` 与 `dev/v0.4.5/` 目录一起承接当前开发消费入口。

### 3. 正式发布顺序固定为“内网优先，GitHub 辅助”

- 正式 push 顺序以 `internal` 为主，`github` 为辅。
- 正式安装入口优先使用内网版本仓原始下载 URL。
- GitHub 保留为辅助镜像与外部补充可达性入口，不再作为当前版本唯一发布面。

### 4. `00 -> 01 / 10` 的真实接管链继续收口到当前版本

- 当前修复不再接受“总控嘴上派发了，但还在当前 root 窗口代演 `01 / 10`”。
- `ai-team runtime --action total_control_entry` / `read_receipt` 命中 `01 / 10` 时，现在只允许登记派发，不再直接吐出 live role prompt。
- 只有在真实主窗口执行 `ai-team runtime --action window_continue --current-host "<01|10>"` 后，`01 / 10` 才算正式接管。
- 错误 host 调 `window_continue` 必须 fixed block 为 `当前不是对人窗口。`

## 影响范围

- 影响：
  - 当前 bundle 本地真源版本号
  - tracked stable release metadata
  - release note carrier
  - 开发版本入口指针
  - 版本仓 `releases/v0.4.5/` 导出目录
- 不影响：
  - `00 / 01 / 10 / worker` 的控制面所有权
  - `01 / 10` 的对人职责边界
  - worker 不直接对人这一条边界
  - `VSCode / Codex / 宿主 UI`

## 验证命令与结果

正式执行时至少运行以下命令：

```bash
cd /Users/mac/Documents/Playground-English
PYTHONPATH=dev python3 -m unittest tests.test_release_bundle -q
PYTHONPATH=dev python3 -m unittest tests.test_bootstrap_smoke -q
PYTHONPATH=dev python3 -m unittest tests.test_default_bundle -q
PYTHONPATH=dev python3 -m unittest tests.test_min_install -q
PYTHONPATH=dev python3 -m unittest tests.test_version_governance -q
PYTHONPATH=dev python3 -m unittest tests.test_launch_judgment_narrow_chain -q
```

当前这轮已真实确认的结果是：

- 当前 runtime staged activation 定向验证：
  - `PYTHONPATH=dev python3 -m unittest tests.test_route_and_window_state_resolver tests.test_runtime_entry tests.test_min_install -q`
  - `63 / 63` 通过
- 当前 release/runtime 窄链验证：
  - `PYTHONPATH=dev python3 -m unittest tests.test_default_bundle.DefaultBundleContractTest.test_startup_template_requires_total_control_loading_before_any_other_chain tests.test_release_bundle.ReleaseBundleBuilderTest.test_builder_can_sync_tracked_stable_pointer_file_from_generated_release_metadata tests.test_launch_judgment_narrow_chain tests.test_bootstrap_scripts -q`
  - `14 / 14` 通过
- 真实 live proof：
  - `total_control_entry -> window_continue(01) -> read_receipt -> window_continue(10)` 全链通过
  - wrong host 调 `window_continue` 被固定拦截为 `当前不是对人窗口。`
- 当前 tracked `stable-release.json`：
  - 已与当前 repo-local `v0.4.5` bundle 内容重新对齐
- 当前 tracked `bundle SHA256`：
  - `0b6d7719e7bd7d35b255da315934bee4f6a15ec51156fe932abb00baa1fb0453`
- 当前 tracked `installer archive SHA256`：
  - `f4a738d7644e45275e195a7561f1720bf6f5ca693d91e352680dbcb4e8edd8a9`

但这还不等于：

- 已基于当前修复重新 build 正式五件套
- 已把新一轮 `v0.4.5` 产物重新导出到 `/Users/mac/Documents/playground-Version/releases/v0.4.5/`
- 已完成当前修复对应的远端安装 smoke

## 不包含内容

- 不包含新的控制面重设计。
- 不包含新的对人窗口名。
- 不包含新的 worker 直连对人能力。
- 不包含把 repo-local `docs/`、`PROJECT_MEMORY.md` 写成已发布 bundle 资产。

## 正式发版结果

- 当前发布阶段：
  - `ready-to-repackage-on-internal`
- 当前已完成：
  - 当前修复 commit `f33f108` 已进入本地 `main`
  - `internal/main` 已更新到 `f33f108`
  - repo-local carrier、提示词、tracked stable pointer 和 runtime/live proof 已对齐
- 当前未完成：
  - 尚未基于 `f33f108` 重新 build `v0.4.5` 正式五件套
  - 尚未把这轮产物重新导出到 `/Users/mac/Documents/playground-Version/releases/v0.4.5/`
  - 尚未回写这一轮的 `source.json` / `release-index.md`
  - `github` 辅助镜像本轮已暂停，不计入当前完成态
- 因此当前准确口径是：
  - 上一轮 `v0.4.5` internal release 仍是已发布基线
  - 但当前这次 runtime 修复，对应的新一轮正式打包发版还没有完成

正式远端安装入口（发版后使用）：

- stable pointer：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/stable-release.json`
- macOS 安装入口：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh`
- Windows 安装入口：
  - `http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1`
- GitHub 辅助镜像入口：
  - 当前机器未完成镜像 push，暂不作为本轮正式可用入口

## 给大模型的继续执行提示

继续接手本轮 `v0.4.5` 正式发版时，先读：

1. `dev/PROJECT_MEMORY.md`
2. `dev/docs/superpowers/memory/active/04-runtime-installer-and-release.md`
3. `dev/docs/superpowers/memory/active/09-release-and-version-governance.md`
4. `dev/install/default_bundle/manifest.json`
5. `dev/install/stable-release.json`
6. `dev/docs/releases/ai-team-bundle-v0.4.5-release-note.md`
7. `dev/tests/test_launch_judgment_narrow_chain.py`
8. `dev/v0.4.5/140-v0.4.5-中文发版执行说明书.md`

不要误判的 truth boundary：

- `dev/install/default_bundle/` 才是当前 bundle 真源
- `dev/install/stable-release.json` 是 tracked stable release pointer 真源
- `dev/docs/releases/` 是 release note carrier，不是 bundle 真源
- `/Users/mac/Documents/playground-Version` 只承接导出结果，不回写 bundle 真源
- `.ai-team/` 是项目本地运行态，不是正式提交边界

当前版本已经进入的正式状态：

- `v0.4.5` 的 repo-local 发布面、版本仓导出面、tracked pointer 与真实内网安装入口已经统一到同一版本语义。
- 当前正式可用入口是内网版本仓 raw URL。
- GitHub 辅助镜像仍需在可达网络或可用 SSH key 条件下补推。

## 给大模型的新安装提示词（v0.4.5）

设备选择：

- `macOS`：用下面的 `macOS` 提示词。
- `Windows`：用下面的 `Windows` 提示词。
- 不确定设备：先问“你现在是 `macOS` 还是 `Windows`？可用的是 `bash/zsh` 还是 `PowerShell`？”，确认后再发对应提示词。

### macOS

```text
你现在要在本机执行 ai-team v0.4.5 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

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
- 是否真的执行了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- 是否写入 governance-log.jsonl / governance-latest.json
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.5.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.5 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.5.ps1"
Invoke-WebRequest -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
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
- 不确定设备：先问“你现在是 `macOS` 还是 `Windows`？可用的是 `bash/zsh` 还是 `PowerShell`？”，确认后再发对应更新提示词。

### macOS

```text
你现在要在本机执行 ai-team v0.4.5 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 先采集更新前状态：which ai-team、ai-team doctor || true。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新后继续执行校验命令，并输出更新前后对照。
6. 如果任一步失败，立即停止。

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
你现在要在本机执行 ai-team v0.4.5 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 先采集更新前状态：where.exe ai-team、ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新后继续执行校验命令，并输出更新前后对照。
6. 如果任一步失败，立即停止。

执行命令：
where.exe ai-team
ai-team doctor
$script = Join-Path $env:TEMP "install-ai-team-v0.4.5.ps1"
Invoke-WebRequest -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.5 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.5.log"

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
