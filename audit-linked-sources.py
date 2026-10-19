#!/usr/bin/env python3
"""Find GPL-only source files whose object code is linked into libvlc.so.

A contrib being "LGPL" in VideoLAN's build rules doesn't guarantee every file in
it is: zvbi 0.2.35, for one, carries GPLv2-only files (packet-830.c, pdc.c) in
an otherwise LGPL library. This checks what is actually linked:

  for every static library in the contrib install prefix,
    for every member object defining a global symbol that the UNSTRIPPED
    libvlc.so also defines (i.e. the linker pulled that object in),
      find the exact source it was compiled from (via the object's location in
      the package's build tree) and read its license header;
      FAIL if the header names the GPL without "Lesser"/"Library".

Objects whose source can't be pinned down exactly are matched by file name
within their own package and only reported as WARN. Reviewed false positives
live in license-exceptions.txt.

usage: audit-linked-sources.py <libvlcjni tree> <abi> [linked-packages.txt]

With a third argument, also writes the contrib packages that have code in
libvlc.so (one per line) — the list the third-party notices must cover.
"""
import pathlib
import re
import subprocess
import sys

tree = pathlib.Path(sys.argv[1])
abi = sys.argv[2]
so = tree / "libvlc/jni/obj/local" / abi / "libvlc.so"
contrib = tree / "vlc/contrib"
prefix = next(p for p in contrib.glob("*-linux-android*")
              if not p.name.startswith("contrib-"))  # install prefix
srcroot = next(contrib.glob("contrib-android-*"))  # unpacked + built packages
here = pathlib.Path(__file__).resolve().parent

SRC_EXT = (".c", ".cc", ".cpp", ".cxx", ".S", ".s", ".asm")
TEST_DIRS = {"test", "tests", "testsuite", "examples", "fuzz", "doc", "docs"}
GPL = re.compile(r"GNU General Public License|\bGPL\b", re.I)
NOT_GPL_ONLY = re.compile(
    r"Lesser|Library General|LGPL|GNU Library|Permission is hereby granted|"
    r"Redistribution and use in source|BSD|MIT License|ISC License|"
    r"public domain|zlib License|Apache License", re.I)

exceptions = set()
exc_file = here / "license-exceptions.txt"
if exc_file.exists():
    for line in exc_file.read_text().splitlines():
        path = line.split("#", 1)[0].strip()
        if path:
            exceptions.add(path)


def nm_defined(path, global_only=True):
    args = ["nm", "--defined-only"] + (["-g"] if global_only else []) + [str(path)]
    return subprocess.run(args, capture_output=True, text=True).stdout


def gpl_only(src):
    head = src.read_text(errors="replace")[:4000]
    return bool(GPL.search(head)) and not NOT_GPL_ONLY.search(head)


# ALL defined symbols of the .so, local ones included: libraries built with
# -fvisibility=hidden (libaribcaption, ...) end up as local symbols, and a
# global-only scan would miss that they're linked at all. Matching archive
# globals against locals can only over-include, which is the safe direction.
linked = {parts[2] for parts in map(str.split, nm_defined(so, global_only=False).splitlines())
          if len(parts) >= 3}

# Index each package's files once.
files_by_pkg = {}


def pkg_files(pkg):
    if pkg not in files_by_pkg:
        files_by_pkg[pkg] = [p for p in (srcroot / pkg).rglob("*") if p.is_file()]
    return files_by_pkg[pkg]


def exact_sources(pkg, member):
    """Sources pinned down via the object file's location in the build tree."""
    root = srcroot / pkg
    found = []
    for obj in (p for p in pkg_files(pkg) if p.name == member):
        rel = obj.relative_to(root)
        # cmake: [vlc_build/]<srcdir>/CMakeFiles/<target>.dir/<path/to/src.c>.o
        m = re.match(r"(?:(?:vlc_build|build|_build)/)?(.*?)/?CMakeFiles/[^/]+\.dir/(.+)\.o$",
                     rel.as_posix())
        if m:
            src = root / m.group(1) / m.group(2)
            if src.exists():
                found.append(src)
            continue
        stem = re.sub(r"^lib\w+?_la-", "", pathlib.Path(member).stem)
        d = obj.parent.parent if obj.parent.name == ".libs" else obj.parent
        drel = d.relative_to(root).parts
        dirs = {d}
        if drel and drel[0] in {"vlc_build", "build", "_build"}:  # out-of-tree
            dirs.add(root.joinpath(*drel[1:]))
        for dd in dirs:
            for ext in SRC_EXT:
                if (dd / (stem + ext)).exists():
                    found.append(dd / (stem + ext))
    return found


def loose_sources(pkg, member):
    stem = re.sub(r"^lib\w+?_la-", "", member)
    stem = re.sub(r"(\.(c|cc|cpp|cxx|S|s|asm))?\.o$", "", stem)
    return [p for p in pkg_files(pkg)
            if p.suffix in SRC_EXT and p.stem == stem
            and not TEST_DIRS & set(p.relative_to(srcroot / pkg).parts)]


fails, warns = [], []
linked_pkgs = set()
for lib in sorted(prefix.glob("lib/*.a")):
    built = next((p for p in srcroot.rglob(lib.name) if p.is_file()), None)
    if built is None:
        continue  # not built from a contrib tarball (e.g. generated .a)
    pkg = built.relative_to(srcroot).parts[0]
    member, pulled = None, set()
    for line in nm_defined(lib).splitlines():
        if line.endswith(":") and not line.startswith(" "):
            member = line[:-1]
        else:
            parts = line.split()
            if member and len(parts) >= 3 and parts[2] in linked:
                pulled.add(member)
    if pulled:
        linked_pkgs.add(pkg)
    for obj in sorted(pulled):
        exact = exact_sources(pkg, obj)
        for src in exact or loose_sources(pkg, obj):
            rel = src.relative_to(srcroot).as_posix()
            if rel in exceptions or not gpl_only(src):
                continue
            (fails if exact else warns).append(f"{lib.name}:{obj} <- {rel}")

for w in warns:
    print("WARN possible linked GPL source (name match only):", w)
for f in fails:
    print("FAIL linked GPL source:", f)
print(f"checked {len(linked)} linked symbols: {len(fails)} GPL-only linked sources, "
      f"{len(warns)} unconfirmed")
if len(sys.argv) > 3:
    pathlib.Path(sys.argv[3]).write_text("".join(p + "\n" for p in sorted(linked_pkgs)))
sys.exit(1 if fails else 0)
