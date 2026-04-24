# ai-team-bundle v0.4.2 版本说明

`v0.4.2` 是基于 `v0.4.1` 的正式稳定发布版本。

如果用一句话概括这次变化：

**`v0.4.2` 主要完成方法论真源重构的正式版本收口，把当前正式 bundle、stable pointer、release note 与发布资产统一切到新版本号，并作为新的稳定公开版本发布。**

## 版本定位

- `v0.4.1` 是上一轮对外稳定版本。
- `v0.4.2` 是承接当前方法论真源重构与发布链收口的正式版本。
- 新安装与后续默认 stable 更新，发布后都以 `v0.4.2` 为准。

## 本次变化

### 1. 正式版本面切到 `v0.4.2`

- `install/default_bundle/manifest.json` 的 `bundle_version` 已切到 `v0.4.2`。
- `install/stable-release.json` 已与 `v0.4.2` 正式 release metadata 对齐。
- `ai-team-bundle-v0.4.2-release-note.md` 已补齐为当前正式 release note carrier。

### 2. 正式发布资产已齐备

- 正式 tag 名称：
  - `ai-team-bundle-v0.4.2`
- 正式发布资产：
  - `ai-team-bundle-v0.4.2.tar.gz`
  - `ai-team-bundle-v0.4.2-installer.tar.gz`
  - `ai-team-bundle-v0.4.2.manifest.json`
  - `ai-team-bundle-v0.4.2.release.json`
  - `ai-team-bundle-v0.4.2.sha256`
  - `stable-release.json`

### 3. 发布前置证据已完成收口

- 当前版本的窄链裁决测试与 freeze snapshot 已同步到 `v0.4.2` 语义。
- 发布与后续复核可直接消费：
  - tracked stable pointer
  - release note
  - 构建产物
  - install materialize 证据
  - freeze snapshot 与冻结 commit 回链

## 影响范围

- 影响：
  - `ai-team install` 的本地默认 bundle 版本语义
  - tracked stable release metadata
  - 正式安装与更新提示词
  - 正式发布资产校验与审查输入包
- 不影响：
  - `v0.4.1` 已对外发布的 GitHub Release 事实
  - 历史 release note 与历史版本目录
  - 非本轮 release-prep 范围内的治理文档结论

## 验证命令与结果

已执行的正式验证命令：

```bash
cd /Users/mac/Documents/Playground-English/dev
python3 -m unittest tests.test_release_bundle -q
python3 -m unittest tests.test_bootstrap_smoke -q
python3 -m unittest tests.test_default_bundle -q
python3 -m unittest tests.test_min_install -q
python3 -m unittest tests.test_version_governance -q
python3 -m unittest tests.test_launch_judgment_narrow_chain -q
```

本轮还执行了正式安装链验证，重点检查：

- `ai-team install` 后 runtime 是否 materialize 到 `<项目根>/.ai-team/runtime/default_bundle/`
- `.ai-team/runtime.json.bundle_root` 是否指向项目本地 runtime
- `.ai-team/` 是否保持本地运行态边界、不进入 git 正式提交边界
- `startup/00-编排-总控.startup.txt` 是否仍由真源 materialize，而不是安装器自造文案

## 不包含内容

- 不包含新的 installer/runtime 架构重设计。
- 不包含超出本轮 `v0.4.2` 真源重构与发布链收口范围之外的额外能力扩面。
- 不把 `dev/docs/`、`PROJECT_MEMORY.md` 或其他 repo-local 治理材料写成已发布 bundle 资产。

## 正式发版结果

- 当前发布阶段：
  - `published`
- 最终正式发布动作：
  - 已执行 `git tag / git push / gh release create`
- GitHub Release：
  - `https://github.com/feng0932/playground-Version/releases/tag/ai-team-bundle-v0.4.2`
- release URL 可访问性：
  - 正式发布后已完成抽样验证

正式远端安装入口（发布后使用）：

- stable pointer：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/stable-release.json`
- macOS 安装入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh`
- Windows 安装入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1`
- release metadata URL：
  - `https://github.com/feng0932/playground-Version/releases/download/ai-team-bundle-v0.4.2/ai-team-bundle-v0.4.2.release.json`

- bundle SHA256：
  - `8f5b95676596d1592615d22d357540817c93d5541822786d158baa3556d33bc4`
- installer archive SHA256：
  - `19cd00507b538e82aa59abe683bd9d6f0e198a5ebf28a12ef1a131ad527077ca`

## 给大模型的继续执行提示

继续接手本轮 `v0.4.2` 正式发版时，先读：

1. `dev/PROJECT_MEMORY.md`
2. `dev/docs/superpowers/memory/active/04-runtime-installer-and-release.md`
3. `dev/docs/superpowers/memory/active/09-release-and-version-governance.md`
4. `dev/install/default_bundle/manifest.json`
5. `dev/install/stable-release.json`
6. `dev/docs/releases/ai-team-bundle-v0.4.2-release-note.md`

不要误判的 truth boundary：

- `dev/install/default_bundle/` 才是当前 bundle 真源
- `dev/docs/releases/` 是 release note carrier，不是 bundle 真源
- `dev/docs/superpowers/`、`PROJECT_MEMORY.md` 是 repo-local 治理层，不是已发布 bundle 资产
- `.ai-team/` 是项目本地运行态，不是正式提交边界

当前版本已进入的正式状态：

- `v0.4.2` 已进入 GitHub Release published 状态
- 正式发布资产已上传
- 正式 stable pointer 已切到 `v0.4.2`
- 安装与更新入口都应按 `v0.4.2` 继续验证

## 给大模型的新安装提示词（v0.4.2）

### macOS

```text
你现在要在本机执行 ai-team v0.4.2 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash -s -- v0.4.2 2>&1 | tee /tmp/ai-team-install-v0.4.2.log

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
- /tmp/ai-team-install-v0.4.2.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.2 的正式新安装，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行安装，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装后继续执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.2.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.2 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.2.log"

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
- $env:TEMP\\ai-team-install-v0.4.2.log 的关键片段
```

## 给大模型的更新提示词（v0.4.2）

### macOS

```text
你现在要在本机执行 ai-team v0.4.2 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 shell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 更新前后都要执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

更新前状态采样：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true

执行命令：
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash -s -- v0.4.2 2>&1 | tee /tmp/ai-team-update-v0.4.2.log

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
- /tmp/ai-team-update-v0.4.2.log 的关键片段
```

### Windows

```text
你现在要在本机执行 ai-team v0.4.2 的正式更新，不要只解释步骤，要实际运行命令并输出完整日志。

要求：
1. 先确认你有 PowerShell、网络、文件写权限；如果没有，直接说明无法执行。
2. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 更新前后都要执行校验命令，并输出结果。
5. 如果任一步失败，立即停止。

更新前状态采样：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team 2>$null
try { ai-team doctor --project-root . } catch {}

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.2.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.2 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.2.log"

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
- $env:TEMP\\ai-team-update-v0.4.2.log 的关键片段
```
