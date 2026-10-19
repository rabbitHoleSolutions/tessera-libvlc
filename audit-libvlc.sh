#!/bin/sh
# Fails (exit 1) if a libVLC AAR carries GPL code. Tessera ships next to the
# proprietary Meta Spatial SDK, so its libVLC must be LGPL-only.
#
#   audit-libvlc.sh <libvlc.aar> [libvlcjni work tree]
#
# Checks, per ABI in the AAR:
#  1. GPL-only third-party libraries, by symbols they always export.
#  2. GPL Lua scripts packaged as assets.
#  3. With the libvlcjni work tree: VLC's own GPL-2.0+ modules. Static builds
#     carry no per-module license string to scan for, so this checks the
#     generated static module table (libvlcjni-modules.c) against the plugins
#     gpl-modules.py finds in the VLC sources.
#
# Positive control: the Maven Central libvlc-all 4.0.0-eap28 FAILS this audit.
set -eu

AAR=$1
TREE=${2:-}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$AAR" -d "$TMP"

# Symbols / strings unique to GPL-only libraries VLC can link:
#   x264/x265/x262 encoders (x264's SEI banner; FFmpeg's decoder legitimately
#   contains "x264 - core" to recognise x264 streams, so that can't be used), libpostproc, libdvdnav/libdvdread/libdvdcss, faad2,
#   libmad, liba52, libmpeg2, live555 (GPL via its LGPLv3 + VLC GPL glue),
#   aribb24, libdvbcsa, srt (GNUv3 deps). (librist is BSD-2 and allowed.)
MARKERS='H.264/MPEG-4 AVC codec - Copy
x265_encoder_open
pp_get_context
dvdnav_open
DVDOpen
dvdcss_open
NeAACDecOpen
mad_decoder_init
a52_init
mpeg2_init
RTSPClient
arib_instance_new
dvbcsa_key_alloc
srt_startup'

fail=0
for so in "$TMP"/jni/*/libvlc.so; do
    abi=$(basename "$(dirname "$so")")
    echo "$MARKERS" | while IFS= read -r m; do
        if grep -qaF "$m" "$so"; then
            echo "FAIL [$abi] GPL library marker present: $m"
        fi
    done > "$TMP/markers.txt"
    if [ -s "$TMP/markers.txt" ]; then cat "$TMP/markers.txt"; fail=1; fi
    echo "[$abi] libvlc.so $(wc -c < "$so") bytes, sha256 $(sha256sum "$so" | cut -c1-16)…"
done

if [ -d "$TMP/assets/lua" ]; then
    echo "FAIL GPL Lua scripts packaged under assets/lua"
    fail=1
fi

if [ -n "$TREE" ]; then
    TABLE=$(find "$TREE/vlc" -path '*build-android-*' -name libvlcjni-modules.c | head -1)
    test -n "$TABLE" || { echo "FAIL no libvlcjni-modules.c under $TREE/vlc"; exit 1; }
    grep -o 'vlc_entry__[A-Za-z0-9_]*' "$TABLE" | sed 's/vlc_entry__//' | sort -u > "$TMP/linked"
    python3 -I "$(dirname "$0")/gpl-modules.py" "$TREE/vlc" 2>/dev/null | sort -u > "$TMP/gpl"
    echo "$(wc -l < "$TMP/linked") plugins linked: $(tr '\n' ' ' < "$TMP/linked")"
    if [ -s "$TMP/gpl" ] && comm -12 "$TMP/linked" "$TMP/gpl" | grep -q .; then
        echo "FAIL GPL-2.0+ VLC modules linked: $(comm -12 "$TMP/linked" "$TMP/gpl" | tr '\n' ' ')"
        fail=1
    fi
fi

if [ "$fail" -ne 0 ]; then
    echo "AUDIT FAILED: $AAR"
    exit 1
fi
echo "AUDIT PASSED: $AAR is free of GPL code (by marker scan)"
