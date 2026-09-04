# 📡 RDP Protocol Deep-Dive & The Multi-Monitor Insight

## 1. The Core Insight: Client-Declared Display Geometry

In the Microsoft Remote Desktop Protocol (MS-RDPBCGR / [MS-RDPEDISP]):
The monitor topology of a remote session is **declared unilaterally by the client** during the connection sequence. The RDP server does not query physical display hardware attached to the client machine; it blindly accepts the client's monitor specification.

### Connection Sequence (MS-RDPBCGR §2.2.1.3.6)
1. **Client Core Data (`TS_UD_CS_CORE`)**:
   Sends initial width and height (typically covering the entire bounding rectangle of all monitors).
2. **Client Monitor Data (`TS_UD_CS_MONITOR`)**:
   Specifies:
   - `monitorCount`: Number of displays (1 to 16).
   - `monitorDefArray`: Array of `TS_MONITOR_DEF` structures containing:
     - `left`, `top`, `right`, `bottom` (in virtual desktop coordinates).
     - `flags`: `TS_MONITOR_PRIMARY` (0x00000001) for primary monitor.
3. **Server Initialization (IddCx / Indirect Display Driver)**:
   The Windows Terminal Services graphics subsystem initializes `monitorCount` logical display devices inside the user session.
   - Each display gets its own DPI, taskbar, desktop space, and display index.
   - Standard Windows hotkeys (`Win + Shift + Left/Right`) move application windows between virtual displays.
   - The server composites all displays into a single wide framebuffer matching the bounding box (e.g., `5760x1080`).

---

## 2. Geometric Constraints & Rules

When crafting a fabricated monitor array:
1. **Primary Monitor Position**:
   - The primary monitor **MUST** be placed at `(0, 0)`.
   - Windows session initialization requires `(0, 0)` to belong to the primary display.
2. **Unsigned Coordinate Boundary**:
   - FreeRDP and RDP clients represent coordinates as unsigned 32-bit or 16-bit integers in many structures.
   - All secondary virtual displays must be positioned **to the right of** (`x >= primary.width`) or **below** (`y >= primary.height`) the primary monitor to avoid negative coordinate underflow.
3. **Bounding Box**:
   - Total width = sum of monitor widths (for horizontal strip) = `3 * 1920 = 5760`.
   - Total height = `1080`.
   - Desktop bounding box announced in `FreeRDP_DesktopWidth` and `FreeRDP_DesktopHeight` must match the outer bounds of all `rdpMonitor` rects.

---

## 3. Dynamic Reconfiguration via DISPLAYCONTROL (DVC)

Under [MS-RDPEDISP] (Display Update Virtual Channel Extension):
- Channel name: `Microsoft::Windows::RDS::DisplayControl`
- Allows client to send `DISPLAYCONTROL_MONITOR_LAYOUT` PDUs mid-session without disconnecting.
- FreeRDP supports dynamic resolution and display control channels via `/dynamic-resolution`.
- In Blou Phase 4, users can dynamically switch from 1 monitor to 3 monitors or change resolutions on the fly through this channel.
