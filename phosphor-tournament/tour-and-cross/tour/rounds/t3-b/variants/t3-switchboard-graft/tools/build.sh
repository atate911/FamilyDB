#!/bin/sh
# Assemble the sheet from its parts (tools/parts), in order, keeping the first comment (the
# design's statement) and dropping the rest, so the sheet stays under its budget.
cd "$(dirname "$0")/.."
P=tools/parts
cat $P/a_frame.css $P/keep_controls.css $P/b_home.css $P/keep_screens.css $P/c_pages.css $P/keep_settings.css $P/keep_other.css $P/keep_signin_motion.css $P/e_graft.css $P/d_end.css $P/f_revise.css $P/g_patch.css $P/h_rev3.css | python3 -c "
import re,sys
s=sys.stdin.read()
first=s.index('*/')+2
head,rest=s[:first],s[first:]
rest=re.sub(r'/\*.*?\*/','',rest,flags=re.S)
rest=re.sub(r'\n\s*\n+','\n',rest)
sys.stdout.write(head+rest)" > sheet.css
wc -c sheet.css
