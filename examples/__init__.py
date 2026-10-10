"""Example sites to explore before going live: a believable household, rendered page by page.

`python -m examples` builds a fictional family's FamilyDB at a fixed moment (household.py) and
writes the pages each of them would see as static HTML with links between them (export.py), so
the site can be walked through in a browser with nothing installed and no model called. `--serve`
runs the same household live instead. Nothing here is the product: it reads through the same
stores, renders through the same views, and writes only to its own temporary databases.
"""
