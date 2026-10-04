# Concept viewer

`index.html` is a single page (published as an artifact) for browsing sixteen looks for the
web page: an overview grid for any page, one design at full size on desktop or phone, and two
side by side. Open it from a folder with `img/` beside it (any static file server works).
Keys: left/right design, 1-7 page, P phone, O overview. The address carries the state, as
`#team-a.todo.phone.b2`.

`img/<id>/<page>.webp` is the full-page desktop shot (1280 wide, cut at 3800 px),
`<page>-phone.webp` the phone shot (585 wide, 1.5x), and `<page>-t.webp` the overview thumbnail.
The nine designs built on the real app were rendered by `run_full.sh` and `render_full.js`
(the harness's own scripts, changed to shoot every page at both sizes); the six from-scratch
mockups come from `../fresh/kit/final.js`.
