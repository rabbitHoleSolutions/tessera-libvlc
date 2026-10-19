#!/usr/bin/env python3
"""Print the VLC plugin names whose sources declare a GPL-only license.

VLC modules default to LGPL-2.1+; a module that is GPL says so explicitly with
`#define VLC_MODULE_LICENSE VLC_LICENSE_GPL_2_PLUS`. This finds those source
files, maps each to the plugin(s) that compile it via modules/**/Makefile.am
(`lib<name>_plugin_la_SOURCES = ...`), and prints one plugin name per line —
the form libvlcjni's VLC_MODULE_BLACKLIST matches against lib<name>_plugin.a.

usage: gpl-modules.py <vlc source dir>
"""
import pathlib
import re
import sys

vlc = pathlib.Path(sys.argv[1])
modules = vlc / "modules"

gpl_sources = {
    p.resolve()
    for p in modules.rglob("*")
    if p.suffix in {".c", ".cpp", ".m", ".h"}
    and re.search(r"define\s+VLC_MODULE_LICENSE\s+VLC_LICENSE_GPL",
                  p.read_text(errors="replace"))
}

# lib<name>_plugin_la_SOURCES = a.c b.c \
#     c.c
assign = re.compile(r"^lib(\w+)_plugin_la_SOURCES\s*\+?=\s*(.*)$")
plugins = set()
mapped = set()
for mk in modules.rglob("Makefile.am"):
    lines = mk.read_text(errors="replace").replace("\\\n", " ").splitlines()
    for line in lines:
        m = assign.match(line.strip())
        if not m:
            continue
        for src in m.group(2).split():
            src = src.replace("$(srcdir)/", "")
            # Sub-Makefiles are include()d from modules/Makefile.am, so their
            # paths are relative to modules/, not to their own directory.
            path = (modules / src).resolve()
            if path in gpl_sources:
                plugins.add(m.group(1))
                mapped.add(path)

for p in sorted(gpl_sources - mapped):
    print(f"warning: GPL source not mapped to a plugin: {p.relative_to(vlc.resolve())}",
          file=sys.stderr)
print("\n".join(sorted(plugins)))
