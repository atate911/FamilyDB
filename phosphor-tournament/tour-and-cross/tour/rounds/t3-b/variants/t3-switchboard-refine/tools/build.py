# Assemble the sheet: the head (the rules this design keeps, as comments), the inherited parts with
# their comments stripped (they are kept, commented, in tools/parts), then this round's layer.
import re, pathlib
here = pathlib.Path(__file__).parent
P = here / "parts"
order = ["a_frame", "keep_controls", "b_home", "keep_screens", "c_pages", "keep_settings", "keep_other",
         "keep_signin_motion", "e_graft", "d_end", "f_revise", "g_settled", "h_light"]
body = "".join((P / f"{n}.css").read_text() for n in order)
body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
body = re.sub(r"[ \t]+\n", "\n", body)
body = re.sub(r"\n\s*\n+", "\n", body)
out = (P / "0_head.css").read_text() + body
(here.parent / "sheet.css").write_text(out)
print(len(out))
