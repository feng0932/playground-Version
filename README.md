# playground-Version

产品经理工具包发布仓

## File Position

- This repository is the release-track root for Playground methodology bundles.
- It is not the authoring source-of-truth repository.
- The authoring source of truth remains:
  - `/Users/mac/Documents/Playground-English`

## Current Scope

- Accept exported release candidates
- Accept exported formal releases
- Maintain release-track index files

## Not Allowed

- Do not edit `default_bundle` truth directly in this repository.
- Do not treat this repository as the development workspace.
- Do not hand-fix release artifacts here; fix in the development repository first, then export again.

## Initial Structure

- `release-index.md`
- `candidates/`
- `releases/`
- `install-ai-team.sh`
- `install-ai-team.ps1`
- `stable-release.json`

## Public Entry

macOS:

```bash
curl -fsSL https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.sh | bash
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -Command "iwr https://raw.githubusercontent.com/feng0932/playground-Version/main/install-ai-team.ps1 -UseBasicParsing | iex"
```

Stable pointer:

- `https://raw.githubusercontent.com/feng0932/playground-Version/main/stable-release.json`
