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

if [[ -n "${AI_TEAM_RELEASE_METADATA_URL:-}" ]]; then
  RELEASE_METADATA_URL="${AI_TEAM_RELEASE_METADATA_URL}"
elif [[ -n "${VERSION}" ]]; then
  TAG="ai-team-bundle-${VERSION}"
  RELEASE_METADATA_URL="${REPO_WEB_BASE_URL}/raw/branch/${REPO_BRANCH}/releases/${VERSION}/${TAG}.release.json"
else
  RELEASE_METADATA_URL="${AI_TEAM_STABLE_RELEASE_URL:-${DEFAULT_STABLE_RELEASE_URL}}"
fi

mkdir -p "${BIN_DIR}" "${RELEASES_DIR}" "${STATE_DIR}"
TMP_RELEASE_METADATA_PATH="$(mktemp "${INSTALL_BASE}/release-metadata.XXXXXX.json")"
trap 'rm -f "${TMP_RELEASE_METADATA_PATH}"' EXIT

curl -fsSL "${RELEASE_METADATA_URL}" -o "${TMP_RELEASE_METADATA_PATH}"
IFS=$'\t' read -r TAG RESOLVED_VERSION ARCHIVE_URL EXPECTED_ARCHIVE_SHA256 <<< "$(python3 - "${TMP_RELEASE_METADATA_PATH}" <<'PY'
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
)"
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

curl -fsSL "${ARCHIVE_URL}" -o "${ARCHIVE_PATH}"
python3 - "${ARCHIVE_PATH}" "${EXPECTED_ARCHIVE_SHA256}" <<'PY'
import hashlib
import sys
from pathlib import Path

archive_path = Path(sys.argv[1])
expected = sys.argv[2].strip()
actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit(f"checksum mismatch: expected {expected}, got {actual}")
PY
tar -xzf "${ARCHIVE_PATH}" -C "${EXTRACT_ROOT}"

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

echo "installed ai-team launcher:"
echo "- version: ${RESOLVED_VERSION}"
echo "- release metadata: ${RELEASE_METADATA_URL}"
echo "- archive: ${ARCHIVE_URL}"
echo "- launcher: ${LAUNCHER_PATH}"
echo
echo "PATH entry ensured in: ${TARGET_RC_FILE}"
echo "for the current shell, run:"
echo "  export PATH=\"\$HOME/.ai-team/bin:\$PATH\""
echo "or restart your terminal, then run:"
echo "  ai-team install"
