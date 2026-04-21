# ai-team-bundle v0.4.1 版本说明

`v0.4.1` 是基于 `v0.4.0` 修复成果整理出的正式 patch 版本。

如果用一句话概括这次变化：

**`v0.4.1` 不是重新设计方法论，而是把已经在 `v0.4.0` 上完成的修复成果挂到新的版本号下，并切到新的公开发布轨。**

## 版本定位

- `v0.4.0` 是上一轮结构升级与修复工作的正式完成版本。
- `v0.4.1` 是在不改变核心方向的前提下，为后续公开发布与版本治理做出的 patch 升版。

## 本次变化

### 1. 修复成果挂载到新版本号

- 当前 bundle 真源已经从 `v0.4.0` 切到 `v0.4.1`。
- 这避免了“内容已变但版本号不变”的发布歧义。

### 2. 开发轨与发布轨正式分离

- 开发仓继续维护唯一真源。
- 公开发布转到新的发布根目录与公开发布仓。

### 3. 发布指针切到 `v0.4.1`

- 后续对外发布、对外导出与公开版本索引，统一以 `v0.4.1` 为基线。

## 对使用者的直接影响

- 若你要使用当前最新公开版本，应以 `v0.4.1` 为准。
- 若你要回溯上一轮修复完成态，可继续参考 `v0.4.0`。

## 本次验证

### 版本切换校验

已完成：

- `dev/install/default_bundle/manifest.json` 的 `bundle_version` 切到 `v0.4.1`
- `dev/version-index.md` 的当前指针切到 `v0.4.1`
- `dev/current.md` 的当前指针切到 `v0.4.1`

### 发布导出校验

执行命令：

```bash
cd /Users/mac/Documents/Playground-English/dev
python3 scripts/build_release_bundle.py \
  --bundle-root install/default_bundle \
  --version v0.4.1 \
  --output-dir /tmp/ai-team-v0.4.1-release-export
```

结果：

- 成功生成 `v0.4.1` release 资产
- `bundle_sha256`：
  - `68bd4d0dc2174834967ed7d1260d8dfba9a8389c679b3c85db2f18a5f978013a`
- `installer_archive_sha256`：
  - `367672e3c9ff73b4ea129bfe93de04870630ffd90a1f88bc0c2a26d29ba8ce74`

## 当前公开发布地址

- 发布仓：
  - `https://github.com/feng0932/playground-Version`
- 对外公开版本目录：
  - `https://github.com/feng0932/playground-Version/tree/main/releases/v0.4.1`
- 对外 bootstrap 入口：
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh`
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1`
  - `https://raw.githubusercontent.com/feng0932/playground-Version/main/stable-release.json`
- 对外 GitHub Release 资产基线：
  - `https://github.com/feng0932/playground-Version/releases/download/ai-team-bundle-v0.4.1/ai-team-bundle-v0.4.1.tar.gz`
  - `https://github.com/feng0932/playground-Version/releases/download/ai-team-bundle-v0.4.1/ai-team-bundle-v0.4.1-installer.tar.gz`
  - `https://github.com/feng0932/playground-Version/releases/download/ai-team-bundle-v0.4.1/ai-team-bundle-v0.4.1.manifest.json`
  - `https://github.com/feng0932/playground-Version/releases/download/ai-team-bundle-v0.4.1/ai-team-bundle-v0.4.1.release.json`

## 当前发布轨

- 开发仓：
  - `Playground-English`
- 发布仓：
  - `playground-Version`

## 一句话结论

- `v0.4.1` 是当前新的公开发布指针版本。
