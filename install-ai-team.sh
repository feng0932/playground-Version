#!/usr/bin/env bash

set -euo pipefail

VERSION="${1:-}"
REPO_NAME="${REPO_NAME:-playground-Version}"
REPO_BRANCH="${REPO_BRANCH:-main}"
REPO_WEB_BASE_URL="${REPO_WEB_BASE_URL:-http://192.168.1.152/yuhua/playground-Version}"
REPO_WEB_BASE_URL="${REPO_WEB_BASE_URL%/}"
DEFAULT_STABLE_RELEASE_URL="${REPO_WEB_BASE_URL}/raw/branch/${REPO_BRANCH}/stable-release.json"

INSTALL_BASE="${HOME}/.ai-team"
BIN_DIR="${INSTALL_BASE}/bin"
PATH_EXPORT_LINE='export PATH="$HOME/.ai-team/bin:$PATH"'
TARGET_RC_FILE="${HOME}/.zshrc"
RELEASES_DIR="${INSTALL_BASE}/releases"
LAUNCHER_PATH="${BIN_DIR}/ai-team"
STATE_DIR="${INSTALL_BASE}/state"
MACHINE_STATE_PATH="${STATE_DIR}/machine-install.json"
INSTALL_HISTORY_PATH="${STATE_DIR}/install-history.jsonl"
LOG_PATH="${STATE_DIR}/install-ai-team-bootstrap.log"
PROJECT_ROOT="${AI_TEAM_PROJECT_ROOT:-${PWD}}"
HUMAN_OUTPUT_DONE=0

human_failure() {
  local category="$1"
  local reason="$2"
  local next_step="$3"
  HUMAN_OUTPUT_DONE=1
  {
    echo "安装未完成：${category}"
    echo "原因：${reason}"
    echo "下一步：${next_step}"
    echo "日志：${LOG_PATH}"
  } >&3
}

human_success() {
  HUMAN_OUTPUT_DONE=1
  {
    echo "安装完成：ai-team ${RESOLVED_VERSION} 已接入当前项目。"
    echo "项目 runtime：ready"
    echo "下一步：在项目根目录打开 Codex，输入："
    echo "/总控 请接管当前项目，并授权派发子agent"
    echo "日志：${LOG_PATH}"
  } >&3
}

on_error() {
  local status="$1"
  if [[ "${HUMAN_OUTPUT_DONE}" != "1" ]]; then
    human_failure "unknown" "安装入口执行失败，详细错误已写入日志。" "检查网络、权限和发布入口后重试。"
  fi
  exit "${status}"
}

if [[ -n "${AI_TEAM_RELEASE_METADATA_URL:-}" ]]; then
  RELEASE_METADATA_URL="${AI_TEAM_RELEASE_METADATA_URL}"
elif [[ -n "${VERSION}" ]]; then
  TAG="ai-team-bundle-${VERSION}"
  RELEASE_METADATA_URL="${REPO_WEB_BASE_URL}/raw/branch/${REPO_BRANCH}/releases/${VERSION}/${TAG}.release.json"
else
  RELEASE_METADATA_URL="${AI_TEAM_STABLE_RELEASE_URL:-${DEFAULT_STABLE_RELEASE_URL}}"
fi

mkdir -p "${BIN_DIR}" "${RELEASES_DIR}" "${STATE_DIR}"
: > "${LOG_PATH}"
exec 3>&1 >>"${LOG_PATH}" 2>&1
trap 'on_error $?' ERR
TMP_RELEASE_METADATA_PATH="$(mktemp "${INSTALL_BASE}/release-metadata.XXXXXX.json")"
trap 'rm -f "${TMP_RELEASE_METADATA_PATH}"' EXIT

if ! curl -fsSL "${RELEASE_METADATA_URL}" -o "${TMP_RELEASE_METADATA_PATH}"; then
  human_failure "metadata" "发布元数据获取失败。" "检查内网发布入口、网络或版本号后重试。"
  exit 1
fi
if ! METADATA_FIELDS="$(python3 - "${TMP_RELEASE_METADATA_PATH}" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
payload = json.loads(metadata_path.read_text(encoding="utf-8"))
print(
    "\t".join(
        [
            payload["tag"],
            payload["bundle_version"],
            payload["installer_archive_url"],
            payload["installer_archive_sha256"],
        ]
    )
)
PY
)"; then
  human_failure "metadata" "发布元数据不是有效 JSON 或字段不完整。" "检查发布元数据后重试，或等待重新发布。"
  exit 1
fi
IFS=$'\t' read -r TAG RESOLVED_VERSION ARCHIVE_URL EXPECTED_ARCHIVE_SHA256 <<< "${METADATA_FIELDS}"
RELEASE_STATUS_URL="${REPO_WEB_BASE_URL}/raw/branch/${REPO_BRANCH}/releases/${RESOLVED_VERSION}/release-status.json"
TMP_RELEASE_STATUS_PATH="$(mktemp "${INSTALL_BASE}/release-status.XXXXXX.json")"
if curl -fsSL "${RELEASE_STATUS_URL}" -o "${TMP_RELEASE_STATUS_PATH}"; then
  STATUS_VERDICT="$(python3 - "${TMP_RELEASE_STATUS_PATH}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
allowed = payload.get("default_install_allowed", True)
status = payload.get("release_status", "")
print("blocked" if allowed is False or status == "postrelease_failed" else "allowed")
PY
)"
  if [[ "${STATUS_VERDICT}" == "blocked" ]]; then
    human_failure "metadata" "该版本发布后现场失败，不能作为默认安装版本。" "使用默认 stable 入口安装回退版本，或等待下一热修版本。"
    exit 1
  fi
fi
rm -f "${TMP_RELEASE_STATUS_PATH}"
TARGET_DIR="${RELEASES_DIR}/${TAG}"
RELEASE_METADATA_PATH="${TARGET_DIR}/${TAG}.release.json"
ARCHIVE_PATH="${TARGET_DIR}/${TAG}.tar.gz"
EXTRACT_ROOT="${TARGET_DIR}/source"
ARCHIVE_DIR_NAME="${REPO_NAME}-${TAG}"
ENTRYPOINT_PATH="${EXTRACT_ROOT}/${ARCHIVE_DIR_NAME}/ai_team_installer.py"

mkdir -p "${TARGET_DIR}" "${EXTRACT_ROOT}"
rm -f "${ARCHIVE_PATH}"
rm -f "${RELEASE_METADATA_PATH}"
rm -rf "${EXTRACT_ROOT:?}"/*
cp "${TMP_RELEASE_METADATA_PATH}" "${RELEASE_METADATA_PATH}"

if ! curl -fsSL "${ARCHIVE_URL}" -o "${ARCHIVE_PATH}"; then
  human_failure "network" "安装包下载失败。" "检查网络、发布入口或版本号后重试。"
  exit 1
fi
if ! CHECKSUM_OUTPUT="$(python3 - "${ARCHIVE_PATH}" "${EXPECTED_ARCHIVE_SHA256}" <<'PY'
import hashlib
import sys
from pathlib import Path

archive_path = Path(sys.argv[1])
expected = sys.argv[2].strip()
actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit(f"checksum mismatch: expected {expected}, got {actual}")
PY
)"; then
  printf "%s\n" "${CHECKSUM_OUTPUT}"
  human_failure "checksum" "安装包校验失败。" "确认发布包未损坏后重试，或等待重新发布。"
  exit 1
fi
if ! tar -xzf "${ARCHIVE_PATH}" -C "${EXTRACT_ROOT}"; then
  human_failure "unknown" "安装包解压失败。" "检查日志后重新运行安装入口。"
  exit 1
fi

cat > "${LAUNCHER_PATH}" <<EOF
#!/usr/bin/env bash
export AI_TEAM_RELEASE_METADATA_PATH="${RELEASE_METADATA_PATH}"
exec python3 "${ENTRYPOINT_PATH}" "\$@"
EOF

chmod +x "${LAUNCHER_PATH}"

python3 - "${RELEASE_METADATA_PATH}" "${MACHINE_STATE_PATH}" "${INSTALL_HISTORY_PATH}" "${RELEASE_METADATA_URL}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

metadata_path = Path(sys.argv[1])
machine_state_path = Path(sys.argv[2])
history_path = Path(sys.argv[3])
install_source = sys.argv[4]
payload = json.loads(metadata_path.read_text(encoding="utf-8"))
previous_payload = None
if machine_state_path.exists():
    try:
        previous_payload = json.loads(machine_state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        previous_payload = None
snapshot = {
    "schema_version": 1,
    "installed_at": datetime.now(timezone.utc).isoformat(),
    "bundle_version": payload["bundle_version"],
    "bundle_source": payload["bundle_source"],
    "release_tag": payload["tag"],
    "install_source": install_source,
    "release_metadata_url": install_source,
    "release_metadata_path": str(metadata_path),
    "installer_archive_url": payload["installer_archive_url"],
    "installer_archive_sha256": payload["installer_archive_sha256"],
}
previous_bundle_version = None
if isinstance(previous_payload, dict):
    value = previous_payload.get("bundle_version")
    if isinstance(value, str) and value:
        previous_bundle_version = value
if previous_bundle_version is not None:
    snapshot["previous_bundle_version"] = previous_bundle_version
machine_state_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
with history_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
PY

touch "${TARGET_RC_FILE}"
if ! grep -Fqs "${PATH_EXPORT_LINE}" "${TARGET_RC_FILE}"; then
  {
    printf "\n# Added by ai-team\n"
    printf "%s\n" "${PATH_EXPORT_LINE}"
  } >> "${TARGET_RC_FILE}"
fi

if ! AI_TEAM_RELEASE_METADATA_PATH="${RELEASE_METADATA_PATH}" python3 "${ENTRYPOINT_PATH}" install --project-root "${PROJECT_ROOT}"; then
  human_failure "project_runtime" "项目 runtime 接入失败。" "在项目根目录重新运行 ai-team install --project-root \"${PROJECT_ROOT}\" 或 repair。"
  exit 1
fi

human_success
