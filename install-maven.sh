#!/bin/sh
# Installs out/libvlc-lgpl-$VERSION.aar into a Maven repository directory (for
# Tessera: <tessera>/third_party/maven) as
# ca.rabbitholesolutions.thirdparty:libvlc-lgpl:$VERSION, with the same
# dependencies as VideoLAN's libvlc-all.
#
#   ./install-maven.sh <maven repo dir>
set -eu
mkdir -p "$1"
REPO=$(cd "$1" && pwd -P)
cd "$(dirname "$0")"
. ./PINS

DIR="$REPO/ca/rabbitholesolutions/thirdparty/libvlc-lgpl/$VERSION"
AAR="out/libvlc-lgpl-$VERSION.aar"
test -f "$AAR" || { echo "build first: $AAR missing" >&2; exit 1; }
mkdir -p "$DIR"
cp "$AAR" "$DIR/libvlc-lgpl-$VERSION.aar"
cat > "$DIR/libvlc-lgpl-$VERSION.pom" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>ca.rabbitholesolutions.thirdparty</groupId>
  <artifactId>libvlc-lgpl</artifactId>
  <version>$VERSION</version>
  <packaging>aar</packaging>
  <name>libVLC (LGPL-only build for Tessera)</name>
  <description>libvlcjni $LIBVLCJNI_HASH / VLC $VLC_HASH, LGPL-only: see https://github.com/rabbitHoleSolutions/tessera-libvlc</description>
  <url>https://github.com/rabbitHoleSolutions/tessera-libvlc</url>
  <licenses>
    <license>
      <name>GNU Lesser General Public License, version 2.1 or later</name>
      <url>https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>androidx.annotation</groupId>
      <artifactId>annotation</artifactId>
      <version>1.3.0</version>
      <scope>compile</scope>
    </dependency>
    <dependency>
      <groupId>androidx.legacy</groupId>
      <artifactId>legacy-support-v4</artifactId>
      <version>1.0.0</version>
      <scope>compile</scope>
    </dependency>
  </dependencies>
</project>
EOF
echo "installed $DIR"
