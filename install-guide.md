# Digital Pipeline Installation & Setup Guide

This guide details the prerequisites and step-by-step setup instructions for installing and configuring the Digital Pipeline in your development environment.

---

## 1. Prerequisites & Python 3.12 Setup

The pipeline requires **Python 3.12+**, the GitHub CLI (`gh`), and `git`.

### Installing Python 3.12

#### macOS (Homebrew)
```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Ubuntu / Debian
```bash
sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Turnkey One-Line Installation Workflow (Recommended)

Run the turnkey automated installer directly in your project root:

```bash
curl -sSL https://raw.githubusercontent.com/gintatkinson/DEAP-spec-core/main/scripts/install_pipeline.sh | bash
```

### Manual / Direct Copy Installation Workflow

Alternatively, copy the pipeline directories manually into your active project repository workspace:

```bash
# Refuse to run inside the pipeline repository itself. The cleanup steps below are
# written for a downstream project: here they delete the upstream-only profile this
# repo owns and concatenate .gitignore onto itself. `test -e` is used rather than
# `find -type f` because rules/document-references.md requires existence checks to
# observe symlinks.
if [ -e ./.pipeline/upstream ]; then
  echo "REFUSING: this is the pipeline repository, not a downstream project." >&2
  exit 1
fi

git clone https://github.com/gintatkinson/DEAP-spec-core.git ./.tmp-pipeline
rm -rf ./skills ./rules ./.pipeline ./.agents ./scripts ./app_flutter ./web_react
cp -RP ./.tmp-pipeline/skills ./
cp -RP ./.tmp-pipeline/rules ./
cp -RP ./.tmp-pipeline/.pipeline ./
rm -rf ./.pipeline/upstream   # upstream-only tooling profile; not for downstream projects
cp -RP ./.tmp-pipeline/.agents ./
cp -RP ./.tmp-pipeline/scripts ./
cp -RP ./.tmp-pipeline/app_flutter ./
cp -RP ./.tmp-pipeline/web_react ./
if [ -f ./.gitignore ]; then
  cat ./.tmp-pipeline/.gitignore >> ./.gitignore
else
  cp ./.tmp-pipeline/.gitignore ./
fi
rm -rf ./.tmp-pipeline
python3 scripts/setup_git_hooks.py
python3 skills/spec-orchestrator/scripts/bootstrap_tracker_labels.py
```

---

## 3. Verification

After installation, verify that the environment is fully operational:

```bash
.venv/bin/pytest tests/
python3 scripts/verify_downstream_baseline.py --no-domain
```
