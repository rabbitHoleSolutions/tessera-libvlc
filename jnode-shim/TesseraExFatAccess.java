/*
 * Copyright (C) 2026 Rabbit Hole Solutions
 *
 * This file is an addition to JNode's exFAT implementation (as packaged in
 * me.jahnen:java-fs) and is therefore distributed under the same license:
 *
 * This library is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published
 * by the Free Software Foundation; either version 2.1 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
 * License for more details.
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */
/*
 * Tessera shim inside jnode's exfat package: Cluster and DeviceAccess are
 * package-private, and the extent fast-path (ExFatFileExtents) needs cluster
 * validity checks plus raw device reads. Nothing here adds behavior — it only
 * re-exposes what NodeFile itself uses.
 */
package org.jnode.fs.exfat;

import java.io.IOException;
import java.nio.ByteBuffer;

public final class TesseraExFatAccess {

    private TesseraExFatAccess() {}

    public static boolean clusterInvalid(long cluster) {
        return Cluster.invalid(cluster);
    }

    public static void read(ExFatSuperBlock sb, ByteBuffer dest, long offset) throws IOException {
        sb.getDeviceAccess().read(dest, offset);
    }
}
