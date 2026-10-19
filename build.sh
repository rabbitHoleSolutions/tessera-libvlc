#!/bin/sh
# Builds Tessera's LGPL-2.1 libVLC AAR from pinned sources (see PINS), inside
# VideoLAN's own Android CI image, audits it for GPL code, and packages the
# complete corresponding source.
#
#   ./build.sh             fetch (if needed) + build + audit + package
#   ./build.sh --clean     rebuild from scratch (keeps git clones + tarballs)
#   ./build.sh --distclean also re-clone everything
#   ./build.sh --package-only  re-pack the sources tarball for the existing build
#
# To rebuild from a release's sources tarball instead: unpack it into an empty
# directory, `mkdir work && mv libvlcjni work/`, then ./build.sh (no git needed).
#
# Outputs in out/:
#   libvlc-lgpl-$VERSION.aar              the library Tessera links
#   libvlc-lgpl-$VERSION-sources.tar.xz   everything needed to rebuild it
#   linked-packages.txt                   contribs with code in libvlc.so
#   NOTICES-libvlc.txt                    their licenses, for the app's notices
#   gpl-plugins-blacklisted.txt           VLC modules removed for being GPL
#   SHA256SUMS
#
# Changes from VideoLAN's stock build, all applied here and all in the source
# tarball:
#  1. --license a: contribs bootstrapped with --disable-gpl --disable-gnuv3
#     --enable-ad-clauses (VideoLAN's own LGPL mode).
#  2. VLC's GPL-2.0+ modules (lua, rtp, stats, rotate, ...) added to the module
#     blacklist — --license a only covers contribs, not VLC's own modules.
#  3. zvbi disabled: zvbi 0.2.35 links GPLv2-only code (packet-830.c) into
#     libvlc.so even in LGPL mode. VLC's own LGPL telx decoder replaces it.
#  4. patches/ffmpeg-drop-gpl-aarch64.patch: FFmpeg 8.1 builds three aarch64
#     files with GPL headers (ac3dsp NEON, crc.S) even in LGPL mode; the patch
#     drops them in favour of FFmpeg's portable C code.
#  5. VLC's GPL Lua scripts are removed from the AAR.
set -eu
cd "$(dirname "$0")"
. ./PINS

ROOT=$(pwd -P)
WORK=$ROOT/work
OUT=$ROOT/out
J=$WORK/libvlcjni

case "${1:-}" in
    --package-only) PACKAGE_ONLY=1 ;;
    --distclean) rm -rf "$WORK" ;;
    --clean)
        rm -rf "$J"/vlc/build-android-* "$J"/vlc/contrib/contrib-android-* \
               "$J"/vlc/contrib/*-linux-android* "$J"/libvlc/jni/obj \
               "$J"/libvlc/jni/libs "$J"/libvlc/build "$J"/build ;;
esac
mkdir -p "$WORK" "$OUT"
: "${PACKAGE_ONLY:=0}"

if [ "$PACKAGE_ONLY" = 0 ]; then
# --- sources ---------------------------------------------------------------
# Two ways in: a fresh checkout (git clones + the Tessera edits applied below),
# or an unpacked release sources tarball (no .git; the edits are already in it).
if [ -f "$J/.tessera-offline" ] || { [ -d "$J/buildsystem" ] && [ ! -d "$J/.git" ]; }; then
    OFFLINE=1
    echo "building from an unpacked sources tarball (no git)"
    touch "$J/.tessera-offline"
    # libvlcjni's build.gradle reads `git rev-parse HEAD` in both trees for two
    # informational resource strings; give each a placeholder commit so it can.
    for d in "$J" "$J/vlc"; do
        [ -d "$d/.git" ] && continue
        git -C "$d" init -q
        git -C "$d" -c user.name=tessera-libvlc -c user.email=offline@localhost \
            commit -q --allow-empty -m "unpacked from the tessera-libvlc sources tarball"
    done
else
    OFFLINE=0
fi
BUILD_LIBVLC="$J/buildsystem/build-libvlc.sh"

if [ "$OFFLINE" = 0 ]; then
if [ ! -d "$J/.git" ]; then
    git clone "$LIBVLCJNI_REPO" "$J"
fi
git -C "$J" checkout -q "$LIBVLCJNI_HASH"
# get-vlc.sh clones VLC, resets to its pinned hash and applies the patches.
(cd "$J" && ./buildsystem/get-vlc.sh)
test "$(git -C "$J/vlc" rev-parse HEAD~6)" = "$VLC_HASH" ||
    { echo "VLC checkout is not $VLC_HASH + 6 patches" >&2; exit 1; }

# --- Tessera changes (see header) ------------------------------------------
git -C "$J" checkout -q -- buildsystem/build-libvlc.sh
git -C "$J/vlc" checkout -q -- contrib/src/ffmpeg/rules.mak

# (2) GPL VLC modules → blacklist. No comment line inside the variable: the
# script word-splits it into a regex.
GPL_PLUGINS=$(python3 -I "$ROOT/gpl-modules.py" "$J/vlc")
test -n "$GPL_PLUGINS" || { echo "GPL module scan found nothing — scan broken?" >&2; exit 1; }
printf '    %s\n' $GPL_PLUGINS > "$OUT/blacklist.inc"
sed -i "/^VLC_MODULE_BLACKLIST=\"\$/r $OUT/blacklist.inc" "$BUILD_LIBVLC"
rm "$OUT/blacklist.inc"
grep -q "^    $(echo "$GPL_PLUGINS" | head -1)\$" "$BUILD_LIBVLC" ||
    { echo "blacklist injection failed" >&2; exit 1; }
echo "$GPL_PLUGINS" > "$OUT/gpl-plugins-blacklisted.txt"

# (3) zvbi off, in both the contrib and the VLC configure arguments.
sed -i 's/--enable-zvbi/--disable-zvbi/' "$BUILD_LIBVLC"
test "$(grep -c -- '--disable-zvbi' "$BUILD_LIBVLC")" -ge 2 ||
    { echo "zvbi switch failed" >&2; exit 1; }

# (4) FFmpeg patch, applied by VLC's contrib system after its own patches.
cp "$ROOT/patches/ffmpeg-drop-gpl-aarch64.patch" "$J/vlc/contrib/src/ffmpeg/"
sed -i '/h264_early_SAR.patch/a\	$(APPLY) $(SRC)/ffmpeg/ffmpeg-drop-gpl-aarch64.patch' \
    "$J/vlc/contrib/src/ffmpeg/rules.mak"
grep -q 'ffmpeg-drop-gpl-aarch64.patch' "$J/vlc/contrib/src/ffmpeg/rules.mak" ||
    { echo "ffmpeg patch hook failed" >&2; exit 1; }
fi
# Either way, refuse to build unless every Tessera change is in place.
grep -q -- '--disable-zvbi' "$BUILD_LIBVLC" &&
    grep -q '^    lua$' "$BUILD_LIBVLC" &&
    grep -q 'ffmpeg-drop-gpl-aarch64.patch' "$J/vlc/contrib/src/ffmpeg/rules.mak" ||
    { echo "Tessera LGPL changes missing from the sources" >&2; exit 1; }

# --- build -----------------------------------------------------------------
# Runs as the calling user so the work tree stays ours; HOME inside /work so
# Gradle's caches persist between runs. The image's SDK is read-only and lacks
# platform 36, so the AAR step gets a writable symlink overlay of it (/work/.sdk)
# that Gradle can install the platform into.
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/work/.home \
    -v "$WORK:/work" \
    -w /work/libvlcjni \
    "$BUILD_IMAGE" \
    sh -c "./buildsystem/compile-libvlc.sh -a $ABI --release --license $LICENSE_MODE &&
           mkdir -p /work/.sdk && cp -as /sdk/android-sdk-linux/. /work/.sdk/ 2>/dev/null;
           export ANDROID_HOME=/work/.sdk ANDROID_SDK_ROOT=/work/.sdk ANDROID_SDK=/work/.sdk &&
           gradle --no-daemon -p /work/libvlcjni :libvlc:assembleRelease"

AAR=$(find "$J/libvlc/build/outputs/aar" -name '*release*.aar' | head -1)
test -n "$AAR" || { echo "no AAR produced" >&2; exit 1; }
cp "$AAR" "$OUT/libvlc-lgpl-$VERSION.aar"
# (5) VLC's Lua scripts are GPL-2.0+ and useless without the (blacklisted) lua
# module; keep them out of the AAR so they never reach an APK.
zip -qd "$OUT/libvlc-lgpl-$VERSION.aar" 'assets/lua/*' || true

# --- audit -----------------------------------------------------------------
./audit-libvlc.sh "$OUT/libvlc-lgpl-$VERSION.aar" "$J"
python3 -I ./audit-linked-sources.py "$J" "$ABI" "$OUT/linked-packages.txt"

# --- notices ---------------------------------------------------------------
# One notice per library actually linked (from the audit), with its license
# files verbatim. Tessera ships this as licenses/texts/libvlc-components.txt.
python3 -I ./make-notices.py "$J" "$OUT/linked-packages.txt" "$OUT/NOTICES-libvlc.txt"

fi

# --- complete corresponding source -----------------------------------------
# libvlcjni (with the build-script edits), patched VLC including every
# contrib's upstream tarball (vlc/contrib/tarballs), and this repo's scripts.
# Only build products and the install prefix are left out.
(cd "$WORK" && tar --exclude-vcs \
    --exclude='libvlcjni/libvlc/build' --exclude='libvlcjni/build' \
    --exclude='libvlcjni/libvlc/jni/obj' --exclude='libvlcjni/libvlc/jni/libs' \
    --exclude='libvlcjni/vlc/build-android-*' \
    --exclude='libvlcjni/vlc/contrib/contrib-android-*' \
    --exclude='libvlcjni/vlc/contrib/*-linux-android*' \
    --exclude='libvlcjni/.gradle' --exclude='libvlcjni/vlc/contrib/python-venv' \
    --exclude='autom4te.cache' --exclude='libvlcjni/.tessera-offline' \
    -cJf "$OUT/libvlc-lgpl-$VERSION-sources.tar.xz" libvlcjni \
    -C "$ROOT" README.md PINS build.sh gpl-modules.py audit-libvlc.sh \
    audit-linked-sources.py license-exceptions.txt make-notices.py install-maven.sh \
    patches jnode-shim LICENSE)

(cd "$OUT" && sha256sum "libvlc-lgpl-$VERSION.aar" "libvlc-lgpl-$VERSION-sources.tar.xz" \
    NOTICES-libvlc.txt > SHA256SUMS)
echo "done: $OUT"
