@echo off
REM Use BibTeX (NOT Biber). This project uses \bibliography + .bst, not biblatex.
cd /d "%~dp0"
xelatex -interaction=nonstopmode -shell-escape QS&QA_Fundation_Main.tex
bibtex QS&QA_Fundation_Main
xelatex -interaction=nonstopmode -shell-escape QS&QA_Fundation_Main.tex
xelatex -interaction=nonstopmode -shell-escape QS&QA_Fundation_Main.tex
echo Done: QS&QA_Fundation_Main.pdf
