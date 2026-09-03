#!/usr/bin/env bash
# Use BibTeX (NOT Biber). This project uses \bibliography + .bst, not biblatex.
set -euo pipefail
cd "$(dirname "$0")"
xelatex -interaction=nonstopmode -shell-escape subgroup_main.tex
bibtex subgroup_main
xelatex -interaction=nonstopmode -shell-escape subgroup_main.tex
xelatex -interaction=nonstopmode -shell-escape subgroup_main.tex
echo "Done: subgroup_main.pdf"
