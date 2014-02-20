#!/usr/bin/env bash
# FiXME: This needs work - not ready to run
# Update the man file
cd /Users/dag/etm-tk
echo Making the man file
vinfo=`cat etmTk/v.py | head -1 | sed 's/\"//g' | sed 's/^.*= *//g'`
txt2man -t etm -s 1 -r "version $vinfo" -v "Unix user's manual" etmtk_man.text | sed '1 s/\.\"/\.\\\"/' > etm.1
# tar -cvzf etm_qt.1.gz etm_qt.1
cp etm.1 etmTk/

echo Creating ps version of man file
groff -t -e -mandoc -Tps etm.1 > etm-man.ps

echo Creating pdf version of man file
ps2pdf etm-man.ps etm-man.pdf

cd /Users/dag/etm-tk/etmTk/help
pwd
#for file in HEADER overview data views reports shortcuts preferences using_mercurial; do
#    pandoc -s --toc --toc-depth=4 -B style-before -f markdown -t html5 -o $file.html $file.md
#done

quotes='"""'
echo "" > ../help.py
for file in ATKEYS DATES ITEMTYPES OVERVIEW PREFERENCES REPORTS; do
    pandoc -o $file.text -t plain --no-wrap $file.md
    echo "$file = $quotes\\" >> ../help.py
    cat $file.text >> ../help.py
    echo '"""' >> ../help.py
    echo '' >> ../help.py
done

exit

echo "% ETM Users Manual" > help.md
for file in overview.md data.md views.md reports.md shortcuts.md preferences.md; do
    echo "" >> help.md
    sed '1 s/%/##/' <$file >> help.md
done
pandoc -s --toc --toc-depth=3 -f markdown -t html5 -o help.html  help.md

pandoc -s --toc --toc-depth=3 -f markdown -t latex -o help.tex help.md
pdflatex help.tex

# pandoc -s --toc --toc-depth=3 -f markdown -t html5 -o help.html  help.md overview.md data.md views.md reports.md shortcuts.md preferences.md
# pdflatex help.tex

cd /Users/dag/etm-tk/etmTk/language
for file in HEADER README; do
    pandoc -s --toc -B style-before -f markdown -t html5 -o $file.html $file.md
done

cd /Users/dag/etm-tk/etmTk
file=HEADER
pandoc -s -B style-before -H KEYWORDS -f markdown -t html5 -o $file.html $file.md

file=README
pandoc -s -B style-before -f markdown -t html5 -o $file.html $file.md

file=INSTALL
pandoc -s --toc -B style-before -f markdown -t html5 -o $file.html $file.md

rm -fR *.ps

cd /Users/dag/etm-tk
pdflatex cheatsheet.tex

rm -fR *.ps
rm -fR *.log *.aux *.fdb_latexmk *.fls
rm -fR *.synctex.gz *.out *.toc

cd /Users/dag/etm-tk
