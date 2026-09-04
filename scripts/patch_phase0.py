#!/usr/bin/env python3
import os
import sys

path = os.path.join(os.environ.get("FREERDP_PHASE0_DIR", os.path.expanduser("~/freerdp-phase0")), "client", "X11", "xf_monitor.c")
with open(path, "r") as f:
    content = f.read()

target = "\tVIRTUAL_SCREEN* vscreen = &xfc->vscreen;\n"
replacement = """\tVIRTUAL_SCREEN* vscreen = &xfc->vscreen;

\tconst char* fake_mon = getenv("BLOU_FAKE_MONITORS");
\tif (fake_mon)
\t{
\t\tUINT32 count = 3;
\t\tUINT32 m_w = 1920;
\t\tUINT32 m_h = 1080;
\t\trdpMonitor* fake_monitors = calloc(count, sizeof(rdpMonitor));
\t\tif (!fake_monitors)
\t\t\treturn FALSE;

\t\tvscreen->nmonitors = count;
\t\tfor (UINT32 i = 0; i < count; i++)
\t\t{
\t\t\tfake_monitors[i].x = (INT32)(i * m_w);
\t\t\tfake_monitors[i].y = 0;
\t\t\tfake_monitors[i].width = (INT32)m_w;
\t\t\tfake_monitors[i].height = (INT32)m_h;
\t\t\tfake_monitors[i].is_primary = (i == 0);
\t\t\tfake_monitors[i].orig_screen = i;
\t\t\tfake_monitors[i].attributes.physicalWidth = m_w;
\t\t\tfake_monitors[i].attributes.physicalHeight = m_h;
\t\t\tfake_monitors[i].attributes.orientation = ORIENTATION_LANDSCAPE;

\t\t\tvscreen->monitors[i].area.left = (UINT16)(i * m_w);
\t\t\tvscreen->monitors[i].area.top = 0;
\t\t\tvscreen->monitors[i].area.right = (UINT16)((i + 1) * m_w - 1);
\t\t\tvscreen->monitors[i].area.bottom = (UINT16)(m_h - 1);
\t\t\tvscreen->monitors[i].primary = (i == 0);
\t\t}

\t\tUINT32 total_w = count * m_w;
\t\tUINT32 total_h = m_h;

\t\tvscreen->area.left = 0;
\t\tvscreen->area.top = 0;
\t\tvscreen->area.right = (UINT16)(total_w - 1);
\t\tvscreen->area.bottom = (UINT16)(total_h - 1);

\t\t*pMaxWidth = total_w;
\t\t*pMaxHeight = total_h;
\t\txfc->workArea.x = 0;
\t\txfc->workArea.y = 0;
\t\txfc->workArea.width = total_w;
\t\txfc->workArea.height = total_h;

\t\tfreerdp_settings_set_bool(settings, FreeRDP_UseMultimon, TRUE);
\t\tfreerdp_settings_set_bool(settings, FreeRDP_ForceMultimon, TRUE);
\t\tfreerdp_settings_set_bool(settings, FreeRDP_SupportMonitorLayoutPdu, TRUE);
\t\tfreerdp_settings_set_uint32(settings, FreeRDP_MonitorCount, count);
\t\tfreerdp_settings_set_uint32(settings, FreeRDP_DesktopWidth, total_w);
\t\tfreerdp_settings_set_uint32(settings, FreeRDP_DesktopHeight, total_h);

\t\tBOOL set_rc = freerdp_settings_set_monitor_def_array_sorted(settings, fake_monitors, count);
\t\tfree(fake_monitors);
\t\tWLog_INFO(TAG, "[BLOU Phase 0] Injected %u fabricated monitors (each %ux%u, bounding box %ux%u), set_rc=%d",
\t\t          count, m_w, m_h, total_w, total_h, set_rc);
\t\treturn set_rc;
\t}
"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open(path, "w") as f:
        f.write(content)
    print("PATCH_APPLIED_OK")
else:
    print("TARGET_NOT_FOUND")
