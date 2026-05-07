from __future__ import annotations

import re
from pathlib import Path


RUNTIME_BUNDLE_ROOT = Path(".ai-team") / "runtime" / "default_bundle"
RUNTIME_BUNDLE_ROOT_POSIX = RUNTIME_BUNDLE_ROOT.as_posix()


def materialize_runtime_surface_text(text: str) -> str:
    materialized = text.replace("../assets/", f"{RUNTIME_BUNDLE_ROOT_POSIX}/assets/")
    materialized = re.sub(
        rf"(?<!{re.escape(RUNTIME_BUNDLE_ROOT_POSIX)}/)install/default_bundle/",
        f"{RUNTIME_BUNDLE_ROOT_POSIX}/",
        materialized,
    )
    materialized = re.sub(
        rf"(?<!{re.escape(RUNTIME_BUNDLE_ROOT_POSIX)}/)assets/",
        f"{RUNTIME_BUNDLE_ROOT_POSIX}/assets/",
        materialized,
    )
    materialized = re.sub(
        rf"(?<!{re.escape(RUNTIME_BUNDLE_ROOT_POSIX)}/)org_skills/",
        f"{RUNTIME_BUNDLE_ROOT_POSIX}/org_skills/",
        materialized,
    )
    return materialized


def materialize_role_prompt_body(body: str) -> str:
    return materialize_runtime_surface_text(body)
