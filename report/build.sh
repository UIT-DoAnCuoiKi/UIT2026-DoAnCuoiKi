#!/usr/bin/env bash
# Sinh PDF proof (XeLaTeX+biber) và DOCX khớp BieuMau (pandoc + postprocess.py).
# Xem docs/superpowers/specs/2026-09-10-hinh-thuc-docx-design.md.
set -euo pipefail
cd "$(dirname "$0")"

echo "== reference.docx từ BieuMau =="
python3 make_reference.py

echo "== PDF proof =="
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex || \
  echo "PDF stage skipped/failed (biber/latexmk optional); tiếp tục DOCX."

echo "== body.docx (pandoc) =="
# ieee-vi-en.csl xếp mục tiếng Việt trước tiếng Anh (theo trường langid), đánh
# số [n] liên tục; postprocess.py bóc marker và chèn hai heading nhóm.
pandoc main.tex \
  --from=latex --output=body.docx \
  --citeproc --bibliography=refs.bib --csl=ieee-vi-en.csl \
  --resource-path=.:figures --reference-doc=reference.docx

echo "== main.docx (postprocess) =="
python3 postprocess.py body.docx main.tex main.docx

echo "== Xong =="
ls -la main.docx
