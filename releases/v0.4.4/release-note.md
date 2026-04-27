# ai-team-bundle v0.4.4 版本说明

`v0.4.4` 是基于 `v0.4.3` 的正式候选发布版本；这一版一边收口 `10-执行-产品专家` 在原型前 / 原型后的更深一层意图提取能力，一边把当前 release 窄链正式对齐到 `v0.4.4`。

如果用一句话概括这次变化：

**`v0.4.4` 的目标不是重开控制面，而是在保持 `00 / 01 / 10 / worker` 主链不变的前提下，把产品专家“继续把人的原型想法掏出来”的能力做深，并把发布指针、release carrier、freeze snapshot 一起收口到当前版本。**

## 版本定位

- `v0.4.3` 是上一轮运行时与 primary window 控制面收口版本。
- `v0.4.4` 是承接 `v0.4.3` 的功能增强版本，重点在 `10-执行-产品专家` 的原型前 / 原型后意图提取深化。
- 这次不重开控制链，不新增新的对人窗口，不新增第二条治理链。
- 当前 repo-local 候选发布面、tracked stable pointer 与 release note 已统一以 `v0.4.4` 为准。

## 本次变化

### 1. 原型前增强正式进入 `prototype_preconfirmation`

- `10-执行-产品专家` 在原型前不再只确认页面、状态和保真规则。
- 本轮新增固定提取的 4 组判断基线：
  - `绝对不能错的体验点`
  - `可以退让的表达点`
  - `当前最在意的判断维度`
  - `会直接否决原型的触发条件`
- 这些内容的判断目标不是文字是否一致，而是功能表达、交互逻辑、信息节奏和体验底线是否偏了。

### 2. 原型后增强正式进入 `uiue_reclaim_confirmation`

- `10-执行-产品专家` 在原型交回后不再只停留在“收到包”和“列差异”。
- 当前轮继续产出 `产品确认清单`，同时新增“新意图分层”吸收：
  - `当前轮吸收`
  - `当前轮回修`
  - `下轮再开`
- 这条增强的目标不是多写点评，而是把“本轮必须消化的”和“下轮再开的”正式分开，避免污染当前回修单。

### 3. 对人回执与发布窄链一起收口到当前版本

- tracked `install/stable-release.json` 已切到 `v0.4.4`。
- `ai-team-bundle-v0.4.4-release-note.md` 已补齐为当前正式 release carrier。
- 发布窄链的测试基线、release builder 默认版本和 freeze snapshot 已统一切到 `v0.4.4`。
- 当前版本不再维持“bundle 已到 `v0.4.4`，但 stable pointer / release carrier 还停在旧版本”的半收口状态。

## 影响范围

- 影响：
  - `10-执行-产品专家` 的原型前确认深度
  - `10-执行-产品专家` 的原型后继续掏人想法能力
  - `dispatch_contract_registry.json` 中对应的 snapshot / reclaim 字段承载
  - tracked stable release metadata
  - release note carrier
  - 发布窄链证明面
- 不影响：
  - `00 / 01 / 10 / worker` 的控制面所有权
  - `00 /读取回执`、`/返回总控`、`/总控` 的既有职责边界
  - `VSCode / Codex / 宿主 UI`
  - worker 不直接对人这一条边界

## 验证命令与结果

本轮候选发布面按下面几类验证收口：

```bash
cd /Users/mac/Documents/Playground-English
PYTHONPATH=dev python3 -m unittest tests.test_launch_judgment_narrow_chain
PYTHONPATH=dev python3 -m unittest tests.test_release_bundle
PYTHONPATH=dev python3 -m unittest tests.test_bootstrap_smoke
PYTHONPATH=dev python3 -m unittest tests.test_min_install
PYTHONPATH=dev python3 -m unittest tests.test_version_governance
PYTHONPATH=dev python3 -m unittest \
  tests.test_anti_sycophancy_behavior_eval \
  tests.test_anti_sycophancy_prompt_rules \
  tests.test_bootstrap_scripts \
  tests.test_bootstrap_smoke \
  tests.test_default_bundle \
  tests.test_dispatch_prompt_builder \
  tests.test_final_delivery_gate_runtime \
  tests.test_human_visible_surface_linter \
  tests.test_install_total_control_repair \
  tests.test_launch_judgment_narrow_chain \
  tests.test_methodology_hardening_rules \
  tests.test_min_install \
  tests.test_primary_window_receipt_validator \
  tests.test_product_handoff_gate \
  tests.test_release_bundle \
  tests.test_route_and_window_state_resolver \
  tests.test_submission_status_runtime \
  tests.test_total_control_contracts \
  tests.test_total_control_receipt_consumer \
  tests.test_version_governance \
  install.default_bundle.org_skills.03-submission-status-governance.tests.test_engineering_handoff_readiness \
  install.default_bundle.org_skills.03-submission-status-governance.tests.test_final_delivery_gate \
  install.default_bundle.org_skills.03-submission-status-governance.tests.test_publish_boundary \
  install.default_bundle.org_skills.03-submission-status-governance.tests.test_publish_to_project_template \
  install.default_bundle.org_skills.03-submission-status-governance.tests.test_submission_status_governance
```

当前已完成并通过的结果：

- `tests.test_launch_judgment_narrow_chain`：`5 / 5` 通过
- `tests.test_release_bundle + tests.test_bootstrap_smoke + tests.test_version_governance + tests.test_default_bundle`：`231 / 231` 通过
- 全仓正式模块回归：`714 / 714` 通过
- 本机真实安装 smoke：
  - `install` 成功
  - `doctor` 成功
  - 项目侧 `ai-team.lock.json`、`.ai-team/runtime.json`、`.ai-team/install.json` 都对齐到 `v0.4.4`

本轮还执行了正式 release builder 对齐，重点检查：

- tracked `install/stable-release.json` 是否由 release builder 反写，而不是手工维护 checksum
- `stable-release.json` 是否与本地生成的 `v0.4.4` release metadata 完全一致
- `bundle SHA256` 与 `installer archive SHA256` 是否都来自当前 build 产物
- 发布窄链 freeze snapshot 是否还能回链到当前测试基线

## 不包含内容

- 不包含新的控制面重设计。
- 不包含新的对人窗口名。
- 不包含新的 worker 直连对人能力。
- 不包含 `VSCode / Codex / 宿主 UI` 修改。
- 不把 `dev/docs/`、`PROJECT_MEMORY.md` 或其他 repo-local 治理材料写成已发布 bundle 资产。

## 正式发版结果

- 当前发布阶段：
  - `publish-ready`
- 当前结论：
  - `v0.4.4` 的 repo-local 候选发布面、tracked stable pointer、release carrier 与窄链证明面已对齐到同一版本语义。
- 尚未发生的动作：
  - 远端 GitHub tag / release 上传
  - 公开发布仓 `stable-release.json` 投影更新
- 因此当前口径是：
  - 已到“可提交发布 / 可执行远端发版动作”
  - 还不是“远端已经 published”

正式远端安装入口（发版后使用）：

- stable pointer：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/stable-release.json`
- macOS 安装入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh`
- Windows 安装入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1`
- release metadata URL：
  - `https://github.com/feng0932/playground-Version/releases/download/ai-team-bundle-v0.4.4/ai-team-bundle-v0.4.4.release.json`

- bundle SHA256：
  - `f086352e42b3d230315bf95e08529a72260c8361686a48f1bdc3139abf077d21`
- installer archive SHA256：
  - `680a08c8461a9360dddc714dd8b8a4a5ebe739b3c522792fe61af8cff0c8324e`

## 给大模型的继续执行提示

继续接手本轮 `v0.4.4` 候选发版时，先读：

1. `dev/PROJECT_MEMORY.md`
2. `dev/docs/superpowers/memory/active/04-runtime-installer-and-release.md`
3. `dev/docs/superpowers/memory/active/09-release-and-version-governance.md`
4. `dev/install/default_bundle/manifest.json`
5. `dev/install/stable-release.json`
6. `dev/docs/releases/ai-team-bundle-v0.4.4-release-note.md`
7. `dev/tests/test_launch_judgment_narrow_chain.py`

不要误判的 truth boundary：

- `dev/install/default_bundle/` 才是当前 bundle 真源
- `dev/install/stable-release.json` 是 tracked stable release pointer 真源
- `dev/docs/releases/` 是 release note carrier，不是 bundle 真源
- `.ai-team/` 是项目本地运行态，不是正式提交边界

当前版本已进入的正式状态：

- 当前目标状态是：在不再混用旧版本 carrier 的前提下，把 `v0.4.4` 的 repo-local 发布面收成单一版本语义。
- 下一步远端发版时，只允许基于当前 `v0.4.4` tracked pointer 和当前 build 产物执行。

## 给大模型的新安装提示词（v0.4.4）

### macOS

```text
你现在要在本机执行 ai-team v0.4.4 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash -s -- v0.4.4 2>&1 | tee /tmp/ai-team-install-v0.4.4.log

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
- /tmp/ai-team-install-v0.4.4.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.4 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.4.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.4 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.4.log"

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
- $env:TEMP\\ai-team-install-v0.4.4.log 的关键片段
```

## 给大模型的更新提示词（v0.4.4）

### macOS

```text
你现在要在本机执行 ai-team v0.4.4 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

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
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash -s -- v0.4.4 2>&1 | tee /tmp/ai-team-update-v0.4.4.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的执行了更新
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.4.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.4 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

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
$script = Join-Path $env:TEMP "install-ai-team-v0.4.4.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.4 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.4.log"

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team/runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的执行了更新
- 更新前后的 ai-team 命令可用性与 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.4.log 的关键片段
```
