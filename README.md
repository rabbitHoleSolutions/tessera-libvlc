# tessera-libvlc

The LGPL-only build of [libVLC](https://www.videolan.org/vlc/libvlc.html) used by
**Tessera**, a multi-stream video player for Meta Quest by Rabbit Hole Solutions.

This repository exists so that anyone who receives Tessera can get the **complete
corresponding source** of the libVLC inside it, rebuild it, and replace it, as
the GNU LGPL v2.1 requires. Every release here contains:

- `libvlc-lgpl-<version>.aar`: the exact library shipped in Tessera.
- `libvlc-lgpl-<version>-sources.tar.xz`: everything needed to rebuild it.
  That covers libvlcjni and VLC at the pinned commits with all patches, the
  upstream source tarball of every bundled third-party library, and these scripts.
- `SHA256SUMS`

## Why a custom build

The `org.videolan.android:libvlc-all` artifact on Maven Central is built with
VideoLAN's default contrib license setting, which is **GPLv3**. Its POM says
LGPL-2.1, but its `libvlc.so` contains x264, libpostproc, libdvdnav/dvdread/dvdcss,
live555 and other GPL-only code. Tessera also ships the proprietary Meta Spatial
SDK, which can't be combined with GPL code, so Tessera needs a libVLC that is
genuinely LGPL.

## What differs from VideoLAN's stock build

All changes are applied by `build.sh` and included in the source tarball:

1. **`--license a`**: VideoLAN's own LGPL mode. Contribs are bootstrapped with
   `--disable-gpl --disable-gnuv3 --enable-ad-clauses`.
2. **GPL VLC modules blacklisted.** `--license a` only covers third-party
   contribs. VLC's own GPL-2.0+ modules (`lua`, `stream_out_rtp`, `stats`,
   `rotate`, ...) are found by `gpl-modules.py` and added to libvlcjni's module
   blacklist. The full list is in `out/gpl-plugins-blacklisted.txt` after a build.
3. **zvbi disabled.** zvbi 0.2.35 links GPLv2-only code (`src/packet-830.c`) into
   libVLC even in LGPL mode. VLC's own LGPL `telx` teletext decoder replaces it.
4. **`patches/ffmpeg-drop-gpl-aarch64.patch`.** FFmpeg 8.1 compiles three
   aarch64 files with GPL license headers (`libavcodec/aarch64/ac3dsp_*`,
   `libavutil/aarch64/crc.S`) even in LGPL mode. The patch drops them in favour
   of FFmpeg's portable C code.
5. **Lua scripts removed** from the AAR. They are GPL-2.0+ and unused without
   the `lua` module.
6. **`patches/vlc-aaudio-fresh-session-on-flush.patch`** (a bug fix, not a
   licensing change). VLC's AAudio output closes and reopens its stream on
   every flush (every seek), reusing the old audio session. On Horizon OS a
   stream reopened on a reused session stays in STARTING for as long as the
   previous stream had been playing, so video froze for seconds after every
   seek. The patch reopens on a freshly allocated session and moves the
   DynamicsProcessing volume effect across to it.

Only the arm64-v8a ABI is built, because Quest headsets are arm64.

## Audits

`build.sh` refuses to finish unless both audits pass:

- `audit-libvlc.sh` scans `libvlc.so` for GPL-only libraries and checks the
  static module table against the GPL module list. As a positive control, it
  **fails** on Maven Central's `libvlc-all-4.0.0-eap28.aar`.
- `audit-linked-sources.py` works out, from the unstripped `libvlc.so`, every
  object file the linker actually pulled from every bundled library. It traces
  each one to its exact source file and fails on any GPL-only license header.
  Reviewed false positives, each with its reasoning, are listed in
  `license-exceptions.txt`.

## Rebuilding

You need Linux, Docker and about 30 GB of disk space.

```sh
./build.sh            # outputs land in out/
./build.sh --clean    # full rebuild, keeping the downloaded sources
```

The build runs in VideoLAN's own Android CI image (pinned in `PINS`) and takes
about 30 minutes on 8 cores.

To rebuild from a release's sources tarball, with no network access to
VideoLAN's git, unpack it into an empty directory and run:

```sh
mkdir work && mv libvlcjni work/ && ./build.sh
```

The tarball already contains every Tessera change, and `build.sh` checks that
they're present. Gradle still needs network access to fetch the Android plugin.

## Replacing the libVLC in Tessera

Tessera loads libVLC as the separate native library
`lib/arm64-v8a/libvlc.so` (together with `libvlcjni.so`). To use a modified
libVLC, put your `libvlc.so` in that location in the APK, re-sign the APK with
your own key, and install it on a Quest in developer mode (for example with
`adb install`). Because the signature changes, uninstall the store build first.

## License

libVLC and this build's output are licensed under the GNU LGPL v2.1 or later.
Bundled libraries keep their own licenses: FFmpeg (LGPL-2.1+), dav1d (BSD-2),
libass (ISC), FreeType (FTL), HarfBuzz (MIT) and others. The scripts in this
repository are also LGPL-2.1-or-later.

Portions of this software are copyright © The FreeType Project
(www.freetype.org). All rights reserved.

## Also here

`jnode-shim/TesseraExFatAccess.java` is a small file that Tessera adds to the
LGPL JNode exFAT implementation (`me.jahnen:java-fs`), published here under the
same license.
