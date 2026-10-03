# Assemble the sheet: every part in cascade order, comments stripped, then folded (tools/fold.py:
# each declaration a later rule of the same selector overrides is dropped, empty rules go), with the
# head (the design's rules, as a comment) on top.
import pathlib, sys
here = pathlib.Path(__file__).parent
sys.path.insert(0, str(here))
import fold
P = here / "parts"
order = ["a_frame", "keep_controls", "b_home", "keep_screens", "c_pages", "keep_settings", "keep_other",
         "keep_signin_motion", "e_graft", "d_end", "f_revise", "g_settled", "h_light", "i_cross", "j_rev"]
body = "".join((P / f"{n}.css").read_text() for n in order if (P / f"{n}.css").exists())
items, _ = fold.parse(fold.strip_comments(body))
# Rules whose classes no template, script or view of the page draws any more are dropped.
words, prefixes = fold.alive_words([here.parent / "templates", "/home/user/FamilyDB/src/familydb/web"])
dead = []
items = fold.prune_dead(fold.fold(items), words, prefixes, dead)
(here / "dropped.txt").write_text("\n".join(dead) + "\n")
out = (P / "0_head.css").read_text() + "\n" + fold.emit(items) + "\n"
(here.parent / "sheet.css").write_text(out)
print(len(out))
