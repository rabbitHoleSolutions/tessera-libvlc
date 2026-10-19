#!/usr/bin/env python3
"""Write the third-party notices for the libraries linked into libvlc.so.

Reads out/linked-packages.txt (written by audit-linked-sources.py: the contrib
packages with object code in libvlc.so) and emits one plain-text notice file
with, for each package: name, version, license, and its license file(s) taken
verbatim from that package's source. Long standard texts (the GNU licenses) are
printed once at the end instead of once per package.

usage: make-notices.py <libvlcjni tree> <linked-packages.txt> <output.txt>
Fails if a linked package has no entry in TABLE, so a new contrib can't ship
without a reviewed notice.
"""
import pathlib
import re
import sys

tree, linked_txt, out_path = map(pathlib.Path, sys.argv[1:4])
contrib = tree / "vlc/contrib"
srcroot = next(contrib.glob("contrib-android-*"))
tarballs = sorted(p.name for p in (contrib / "tarballs").iterdir())

# dir -> (display name, tarball prefix for the version, license, [license files])
# A license file of "" means the notice is given inline in NOTES instead.
TABLE = {
    "aom": ("libaom", "libaom-", "BSD-2-Clause + AOM Patent License 1.0", ["LICENSE", "PATENTS"]),
    "bluray": ("libbluray", "libbluray-", "LGPL-2.1-or-later", ["COPYING"]),
    "dav1d": ("dav1d", "dav1d-", "BSD-2-Clause", ["COPYING"]),
    "ebml": ("libebml", "libebml-", "LGPL-2.1-or-later", ["LICENSE.LGPL"]),
    "ffmpeg": ("FFmpeg", "ffmpeg-", "LGPL-2.1-or-later (built without --enable-gpl)", ["LICENSE.md", "COPYING.LGPLv2.1"]),
    "flac": ("libFLAC", "flac-", "BSD-3-Clause (Xiph)", ["COPYING.Xiph"]),
    "fluidlite": ("FluidLite", "fluidlite-", "LGPL-2.1-or-later", ["LICENSE"]),
    "freetype": ("FreeType", "freetype-", "FreeType License (FTL)", ["docs/FTL.TXT"]),
    "fribidi": ("GNU FriBidi", "fribidi-", "LGPL-2.1-or-later", ["COPYING"]),
    "game-music-emu": ("Game_Music_Emu", "game-music-emu-", "LGPL-2.1-or-later", ["license.txt"]),
    "gcrypt": ("Libgcrypt", "libgcrypt-", "LGPL-2.1-or-later", ["COPYING.LIB", "LICENSES"]),
    "ggml": ("ggml", "ggml-", "MIT", ["LICENSE"]),
    "glslang": ("glslang", "glslang-", "BSD-3-Clause / BSD-2-Clause / MIT / Apache-2.0", ["LICENSE.txt"]),
    "gsm": ("libgsm", "gsm-", "TU Berlin GSM license (permissive)", ["COPYRIGHT"]),
    "harfbuzz": ("HarfBuzz", "harfbuzz-", "MIT (Old MIT)", ["COPYING"]),
    "iconv": ("GNU libiconv", "libiconv-", "LGPL-2.1-or-later", ["COPYING.LIB"]),
    "jpeg": ("libjpeg-turbo", "libjpeg-turbo-", "IJG + BSD-3-Clause + Zlib", ["LICENSE.md"]),
    "lame": ("LAME", "lame-", "LGPL-2.0-or-later", ["COPYING", "LICENSE", ""]),
    "libarchive": ("libarchive", "libarchive-", "BSD-2-Clause", ["COPYING"]),
    "libaribcaption": ("libaribcaption", "libaribcaption-", "MIT", ["LICENSE"]),
    "libass": ("libass", "libass-", "ISC", ["COPYING"]),
    "libdsm": ("libdsm", "libdsm-", "LGPL-2.1-or-later", ["COPYING"]),
    "libdvbpsi": ("libdvbpsi", "libdvbpsi-", "LGPL-2.1-or-later", ["COPYING"]),
    "libebur128": ("libebur128", "libebur128-", "MIT", ["COPYING"]),
    "libgpg-error": ("libgpg-error", "libgpg-error-", "LGPL-2.1-or-later", ["COPYING.LIB"]),
    "libmodplug": ("libmodplug", "libmodplug-", "Public domain", ["COPYING"]),
    "libogg": ("libogg", "libogg-", "BSD-3-Clause (Xiph)", ["COPYING"]),
    "libplacebo": ("libplacebo", "libplacebo-", "LGPL-2.1-or-later", ["LICENSE"]),
    "librist": ("librist", "librist-", "BSD-2-Clause", ["COPYING"]),
    "libshout": ("libshout", "libshout-", "LGPL-2.0-or-later", ["COPYING"]),
    "libtasn1": ("GNU Libtasn1", "libtasn1-", "LGPL-2.1-or-later", ["COPYING"]),
    "libtheora": ("libtheora", "libtheora-", "BSD-3-Clause (Xiph)", ["COPYING"]),
    "libvorbis": ("libvorbis", "libvorbis-", "BSD-3-Clause (Xiph)", ["COPYING"]),
    "libvpx": ("libvpx", "libvpx-", "BSD-3-Clause", ["LICENSE", "PATENTS"]),
    "libxml2": ("libxml2", "libxml2-", "MIT", ["Copyright"]),
    "lua": ("Lua", "lua-", "MIT", [""]),
    "matroska": ("libmatroska", "libmatroska-", "LGPL-2.1-or-later", ["LICENSE.LGPL"]),
    "microdns": ("libmicrodns", "microdns-", "LGPL-2.1-or-later", ["COPYING"]),
    "mpg123": ("mpg123", "mpg123-", "LGPL-2.1-or-later", ["COPYING"]),
    "mysofa": ("libmysofa", "libmysofa-", "BSD-3-Clause", ["LICENSE"]),
    "nfs": ("libnfs", "libnfs-", "LGPL-2.1-or-later (library)", ["COPYING", "LICENCE-LGPL-2.1.txt", "LICENCE-BSD.txt"]),
    "openapv": ("OpenAPV", "openapv-", "BSD-3-Clause", ["LICENSE"]),
    "openjpeg": ("OpenJPEG", "openjpeg-", "BSD-2-Clause", ["LICENSE"]),
    "opus": ("Opus", "opus-", "BSD-3-Clause", ["COPYING"]),
    "png": ("libpng", "libpng-", "libpng License", ["LICENSE"]),
    "protobuf": ("Protocol Buffers", "protobuf-", "BSD-3-Clause", ["LICENSE"]),
    "rnnoise": ("RNNoise", "rnnoise-", "BSD-3-Clause", ["COPYING"]),
    "sam3": ("sam3.cpp", "sam3.cpp-", "MIT", ["LICENSE"]),
    "smb2": ("libsmb2", "libsmb2-", "LGPL-2.1-or-later", ["COPYING", "LICENCE-LGPL-2.1.txt"]),
    "soxr": ("SoX Resampler (libsoxr)", "soxr-", "LGPL-2.1-or-later", ["LICENCE", "COPYING.LGPL"]),
    "spatialaudio": ("libspatialaudio", "spatialaudio-", "LGPL-2.1-or-later", ["LICENSE"]),
    "speex": ("Speex", "speex-", "BSD-3-Clause (Xiph)", ["COPYING"]),
    "speexdsp": ("SpeexDSP", "speexdsp-", "BSD-3-Clause (Xiph)", ["COPYING"]),
    "sqlite": ("SQLite", "sqlite-", "Public domain", [""]),
    "ssh2": ("libssh2", "libssh2-", "BSD-3-Clause", ["COPYING"]),
    "taglib": ("TagLib", "taglib-", "LGPL-2.1 or MPL-1.1", ["COPYING.LGPL"]),
    "twolame": ("TwoLAME", "twolame-", "LGPL-2.1-or-later", ["COPYING"]),
    "upnp": ("pupnp (libupnp)", "pupnp-", "BSD-3-Clause", ["COPYING"]),
    "zlib": ("zlib", "zlib-", "Zlib", ["LICENSE"]),
}

NOTES = {
    "lame": "LAME's FFT/FHT routine (libmp3lame/fft.c) is by Ron Mayer (1988, 1993) and\n"
            "Takehiro Tominaga (1999-2000), who ask that credit be given to: Euler (the\n"
            "Fourier transform), Gauss (the FFT), Hartley (the Hartley transform), Buneman\n"
            "(the trig generator), and Ron Mayer for this version and its optimizations;\n"
            "with further optimization by Mather and Takehiro.",
    "lua": "Copyright (C) 1994-2022 Lua.org, PUC-Rio. Licensed under the MIT license:\n"
           "Permission is hereby granted, free of charge, to any person obtaining a copy of this "
           "software and associated documentation files (the \"Software\"), to deal in the Software "
           "without restriction, including without limitation the rights to use, copy, modify, merge, "
           "publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons "
           "to whom the Software is furnished to do so, subject to the following conditions: The above "
           "copyright notice and this permission notice shall be included in all copies or substantial "
           "portions of the Software. THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, "
           "EXPRESS OR IMPLIED.",
    "sqlite": "The SQLite source code is in the public domain (https://sqlite.org/copyright.html).",
}

# Full GNU texts appear once, at the end; per-package copies are replaced by a pointer.
GNU_TEXTS = {
    "GNU LESSER GENERAL PUBLIC LICENSE\n                       Version 2.1": "GNU LGPL 2.1",
    "GNU LIBRARY GENERAL PUBLIC LICENSE": "GNU LGPL 2 (Library GPL)",
    "GNU GENERAL PUBLIC LICENSE": None,  # never expected in a notice — flag it
}


def version(prefix):
    for t in tarballs:
        if t.startswith(prefix):
            v = re.sub(r"\.(tar\.\w+|githash)$", "", t[len(prefix):])
            v = re.sub(r"-Source$", "", v)
            return v
    return "?"


linked = [l.strip() for l in linked_txt.read_text().splitlines() if l.strip()]
missing = [p for p in linked if p not in TABLE]
if missing:
    sys.exit(f"no notice entry for linked packages: {missing} — add them to TABLE")

used_gnu = set()
parts = [
    "libVLC third-party components\n"
    "=============================\n\n"
    "Tessera's libVLC (LGPL-2.1-or-later, (C) VideoLAN and the VLC authors) is built\n"
    "with the libraries below, each under its own license. Their complete source is\n"
    "in the libvlc-lgpl sources tarball at\n"
    "https://github.com/rabbitHoleSolutions/tessera-libvlc/releases\n\n"
    "Portions of this software are copyright (C) The FreeType Project\n"
    "(www.freetype.org). All rights reserved.\n\n"
    "This software is based in part on the work of the Independent JPEG Group.\n\n"
    "libVLC also uses the LLVM libc++ runtime (libc++_shared.so; Apache-2.0 WITH\n"
    "LLVM-exception) from the Android NDK.\n"
]
for pkg in sorted(linked, key=lambda p: TABLE[p][0].lower()):
    name, prefix, lic, files = TABLE[pkg]
    block = [f"\n{'-' * 72}\n{name} {version(prefix)} — {lic}\n{'-' * 72}\n"]
    for f in files:
        if not f:
            block.append(NOTES[pkg] + "\n")
            continue
        text = (srcroot / pkg / f).read_text(errors="replace").strip()
        head = " ".join(text[:400].split()).upper()
        gnu = next((v for k, v in GNU_TEXTS.items() if " ".join(k.split()).upper() in head), "")
        if gnu is None and "LESSER" not in head and "LIBRARY" not in head:
            sys.exit(f"{pkg}/{f} is a GPL text — review the license entry")
        if gnu:
            used_gnu.add(gnu)
            block.append(f"[{f}: the standard {gnu} text, reproduced at the end of this file]\n")
        else:
            block.append(f"[{f}]\n{text}\n")
    parts.append("".join(block))

common = pathlib.Path("/usr/share/common-licenses")
for gnu in sorted(used_gnu):
    src = {"GNU LGPL 2.1": "LGPL-2.1", "GNU LGPL 2 (Library GPL)": "LGPL-2"}[gnu]
    parts.append(f"\n{'=' * 72}\n{gnu}\n{'=' * 72}\n{(common / src).read_text()}")

out_path.write_text("".join(parts))
print(f"wrote {out_path}: {len(linked)} packages")
