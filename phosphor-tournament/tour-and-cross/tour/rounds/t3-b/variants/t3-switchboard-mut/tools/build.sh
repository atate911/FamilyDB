#!/bin/sh
# Assemble the sheet from its parts (tools/parts), in order.
cd "$(dirname "$0")/.."
P=tools/parts
cat $P/a_frame.css $P/keep_controls.css $P/b_home.css $P/keep_screens.css $P/c_pages.css $P/keep_settings.css $P/keep_other.css $P/keep_signin_motion.css $P/e_graft.css $P/d_end.css $P/f_revise.css $P/g_mutant.css > sheet.css
wc -c sheet.css
