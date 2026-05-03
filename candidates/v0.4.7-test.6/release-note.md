# v0.4.7-test.6 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.7-test.6` 是 `v0.4.7` 正式版前的 CR-004 测试候选，不是正式稳定版。

这版只针对 `v0.4.7-test.5` live 里暴露的问题做回执模板再压缩：

1. `01-编排-初始化项目包` 的 `screening_result` 必须按 validator 可直接消费的清单字符串输出。
2. `10-执行-产品专家` 的 `deepening_result` 必须按 validator 可直接消费的清单字符串输出。
3. 禁止第一次回执使用 `field=value`、YAML 对象块、fenced JSON 等会让 `00` 无法直接消费的格式。

这版要验证的是：

- fresh install 后能拿到 `v0.4.7-test.6`。
- `00 -> 01` 后，`01` 第一次终态回执能被 `00 read_receipt` 直接消费，不靠 correction。
- `00 -> 10` 后，`10` 第一次终态回执能被 `00 read_receipt` 直接消费，不靠 correction。

通过本候选后，只能说：

- `v0.4.7-test.6` 作为 CR-004 首次回执直消测试候选已经可安装、可运行、可验收。

不能说：

- `v0.4.7` 已经正式发版。
- `v0.4.7` 已经切 stable。
- `stable-release.json` 已经更新到 `v0.4.7`。

## 2. 让大模型去安装和 live 验收的提示词

### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.6 的测试版 fresh install 和 live 首次回执验收，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 使用内部 Gitea 测试版发布入口，不要手工拼装 bundle。
2. 本版本是 release-candidate，不是 stable。
3. 保留完整 stdout/stderr。
4. 任一步失败都立即停止，不要脑补成功。
5. 重点验证 01 / 10 第一次终态回执能否被 00 直接消费，不允许靠 correction 补过。
6. 不切 stable，不做正式发版，不使用 GitHub。

执行命令：
set -o pipefail
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.6/ai-team-bundle-v0.4.7-test.6.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-install-v0.4.7-test.6.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.7-test.6-live-firstpass
cd /tmp/ai-team-v0.4.7-test.6-live-firstpass
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

live 验收：
- 如果 total_control_entry 返回 host_native_dispatch.required_tool=spawn_agent，则真实派发 01。
- 01 完成后，只取第一次 Terminal Receipt，执行 read_receipt。
- 如果 read_receipt 直接放行到 10，则真实派发 10。
- 10 完成后，只取第一次 Terminal Receipt，执行 read_receipt。
- 不要要求 01 或 10 修正回执；第一次失败就记录失败原因。

最终必须输出：
## ai-team v0.4.7-test.6 首次回执 live 验收摘要
- fresh install 是否完成：是 / 否
- 实际 bundle_version / release_tag：v0.4.7-test.6 / ai-team-bundle-v0.4.7-test.6
- 渠道：release-candidate
- doctor 关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- 01 第一次回执是否被 00 直接消费：是 / 否
- 10 第一次回执是否被 00 直接消费：是 / 否
- 是否使用 correction：否
- 结论：通过 / 未通过，原因是...
```
