#!/usr/bin/env bash
# Build a COLM 2026 submission package.
#
# Produces:
#   paper/main.pdf       — main paper (8-page body + appendix)
#   paper/supp.pdf       — supplementary material
#   paper/submission.zip — bundle of both + checklist + code archive
#
# Requirements: pdflatex (TeX Live), zip
#
# Usage:
#   bash scripts/build_submission.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAPER_DIR="${PROJECT_ROOT}/paper"
RESULTS_DIR="${PROJECT_ROOT}/results"
FIGURES_DIR="${PROJECT_ROOT}/figures"

echo "=== AgentCompose COLM submission build ==="
echo "PROJECT_ROOT: ${PROJECT_ROOT}"
echo "PAPER_DIR:    ${PAPER_DIR}"

# ---- Step 1: pdflatex main.tex (twice for refs) ----
echo ""
echo "▶ [1/4] Compiling main.tex..."
cd "${PAPER_DIR}"
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
echo "  ✓ main.pdf: $(du -h main.pdf | cut -f1)"

# ---- Step 2: pdflatex supp.tex ----
echo ""
echo "▶ [2/4] Compiling supp.tex..."
pdflatex -interaction=nonstopmode -halt-on-error supp.tex > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error supp.tex > /dev/null
echo "  ✓ supp.pdf: $(du -h supp.pdf | cut -f1)"

# ---- Step 3: Archive code (excluding data/generated/, results/, .git) ----
echo ""
echo "▶ [3/4] Archiving source code..."
cd "${PROJECT_ROOT}"
CODE_ARCHIVE="${PAPER_DIR}/code_archive.zip"
# Avoid paths that depend on absolute location
zip -qr "${CODE_ARCHIVE}" \
    src tests scripts templates tools paper/main.tex paper/supp.tex \
    paper/double_blind_checklist.md \
    README.md pyproject.toml \
    -x "*/__pycache__/*" "*.pyc" "data/generated/*" "results/*" \
       "logs/*" "*.egg-info/*" ".git/*" "figures/*" 2>/dev/null || {
    # zip may not be available on Windows without WSL; fall back to tar
    echo "  ⚠ zip not available; falling back to tar"
    CODE_ARCHIVE="${PAPER_DIR}/code_archive.tar.gz"
    tar -czf "${CODE_ARCHIVE}" \
        --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='data/generated' --exclude='results' \
        --exclude='logs' --exclude='*.egg-info' --exclude='.git' \
        --exclude='figures' \
        src tests scripts templates tools paper/main.tex paper/supp.tex \
        paper/double_blind_checklist.md \
        README.md pyproject.toml
}
echo "  ✓ Code archive: ${CODE_ARCHIVE} ($(du -h "${CODE_ARCHIVE}" | cut -f1))"

# ---- Step 4: Bundle everything ----
echo ""
echo "▶ [4/4] Bundling submission.zip..."
cd "${PAPER_DIR}"
SUBMISSION="${PAPER_DIR}/submission.zip"
# Remove old zip
rm -f "${SUBMISSION}"

if command -v zip > /dev/null 2>&1; then
    zip -q "${SUBMISSION}" main.pdf supp.pdf double_blind_checklist.md code_archive.zip 2>/dev/null \
      || zip -q "${SUBMISSION}" main.pdf supp.pdf double_blind_checklist.md code_archive.tar.gz
    echo "  ✓ submission.zip: $(du -h submission.zip | cut -f1)"
elif command -v powershell > /dev/null 2>&1; then
    # Windows fallback via PowerShell Compress-Archive
    powershell -NoProfile -Command "Compress-Archive -Path 'main.pdf','supp.pdf','double_blind_checklist.md','code_archive.zip' -DestinationPath 'submission.zip' -Force" \
      || powershell -NoProfile -Command "Compress-Archive -Path 'main.pdf','supp.pdf','double_blind_checklist.md','code_archive.tar.gz' -DestinationPath 'submission.zip' -Force"
    echo "  ✓ submission.zip: $(du -h submission.zip | cut -f1)"
else
    echo "  ⚠ neither zip nor powershell available; submission.zip not created"
    exit 1
fi

echo ""
echo "=== Build complete ==="
echo "Files in ${PAPER_DIR}:"
ls -la "${PAPER_DIR}"/main.pdf "${PAPER_DIR}"/supp.pdf "${PAPER_DIR}"/submission.zip 2>/dev/null
echo ""
echo "Page counts:"
echo "  main:  $(pdfinfo main.pdf 2>/dev/null | awk '/^Pages:/{print $2}') pages"
echo "  supp:  $(pdfinfo supp.pdf 2>/dev/null | awk '/^Pages:/{print $2}') pages"
echo ""
echo "Next step: open COLM OpenReview submission portal and upload submission.zip."