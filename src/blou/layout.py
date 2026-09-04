"""
Blou Layout Fabrication Engine.

Calculates and validates fabricated multi-monitor topologies for injection into
FreeRDP rdpSettings (MS-RDPBCGR TS_UD_CS_MONITOR / TS_MONITOR_DEF).
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class MonitorArrangement(str, Enum):
    HORIZONTAL_ROW = "horizontal_row"
    GRID_2X2 = "grid_2x2"
    VERTICAL_COLUMN = "vertical_column"


@dataclass(frozen=True)
class VirtualMonitor:
    index: int
    x: int
    y: int
    width: int
    height: int
    is_primary: bool

    @property
    def right(self) -> int:
        return self.x + self.width - 1

    @property
    def bottom(self) -> int:
        return self.y + self.height - 1


@dataclass(frozen=True)
class DesktopLayout:
    monitors: List[VirtualMonitor]
    bounding_width: int
    bounding_height: int

    @property
    def count(self) -> int:
        return len(self.monitors)

    def get_monitor(self, index: int) -> VirtualMonitor:
        if index < 0 or index >= len(self.monitors):
            raise IndexError(f"Monitor index {index} out of bounds (0..{len(self.monitors) - 1})")
        return self.monitors[index]


class LayoutBuilder:
    """Builds and validates fabricated multi-monitor layouts."""

    MAX_MONITORS = 16
    MIN_MONITORS = 1

    @staticmethod
    def create_horizontal_row(
        count: int = 3,
        monitor_width: int = 1920,
        monitor_height: int = 1080
    ) -> DesktopLayout:
        """
        Creates a horizontal strip of identical monitors side-by-side.
        Primary monitor is strictly at index 0 at (0, 0).
        """
        if count < LayoutBuilder.MIN_MONITORS or count > LayoutBuilder.MAX_MONITORS:
            raise ValueError(f"Monitor count must be between {LayoutBuilder.MIN_MONITORS} and {LayoutBuilder.MAX_MONITORS}")
        if monitor_width <= 0 or monitor_height <= 0:
            raise ValueError("Monitor width and height must be strictly positive")

        monitors = []
        for i in range(count):
            monitors.append(
                VirtualMonitor(
                    index=i,
                    x=i * monitor_width,
                    y=0,
                    width=monitor_width,
                    height=monitor_height,
                    is_primary=(i == 0),
                )
            )

        bounding_width = count * monitor_width
        bounding_height = monitor_height
        layout = DesktopLayout(
            monitors=monitors,
            bounding_width=bounding_width,
            bounding_height=bounding_height
        )
        LayoutBuilder.validate_layout(layout)
        return layout

    @staticmethod
    def create_grid_2x2(
        monitor_width: int = 1920,
        monitor_height: int = 1080
    ) -> DesktopLayout:
        """
        Creates a 2x2 grid layout (4 monitors):
          [0: (0,0)]       [1: (W,0)]
          [2: (0,H)]       [3: (W,H)]
        """
        monitors = [
            VirtualMonitor(0, 0, 0, monitor_width, monitor_height, is_primary=True),
            VirtualMonitor(1, monitor_width, 0, monitor_width, monitor_height, is_primary=False),
            VirtualMonitor(2, 0, monitor_height, monitor_width, monitor_height, is_primary=False),
            VirtualMonitor(3, monitor_width, monitor_height, monitor_width, monitor_height, is_primary=False),
        ]
        layout = DesktopLayout(
            monitors=monitors,
            bounding_width=monitor_width * 2,
            bounding_height=monitor_height * 2
        )
        LayoutBuilder.validate_layout(layout)
        return layout

    @staticmethod
    def validate_layout(layout: DesktopLayout) -> None:
        """
        Validates RDP and FreeRDP architectural invariants:
        1. At least one monitor, no more than MAX_MONITORS.
        2. Exactly one primary monitor.
        3. Primary monitor must be at (0, 0).
        4. All coordinates must be non-negative (unsigned 16/32-bit compliance).
        5. Monitors must not overlap.
        6. Bounding dimensions must enclose all monitors.
        """
        if not (LayoutBuilder.MIN_MONITORS <= layout.count <= LayoutBuilder.MAX_MONITORS):
            raise ValueError(f"Invalid monitor count: {layout.count}")

        primary_monitors = [m for m in layout.monitors if m.is_primary]
        if len(primary_monitors) != 1:
            raise ValueError(f"Layout must contain exactly 1 primary monitor, found {len(primary_monitors)}")

        primary = primary_monitors[0]
        if primary.x != 0 or primary.y != 0:
            raise ValueError(f"Primary monitor MUST be positioned at (0, 0), was at ({primary.x}, {primary.y})")

        # Non-negative coordinates
        for m in layout.monitors:
            if m.x < 0 or m.y < 0:
                raise ValueError(f"Monitor {m.index} has negative coordinate: ({m.x}, {m.y})")
            if m.width <= 0 or m.height <= 0:
                raise ValueError(f"Monitor {m.index} has invalid dimensions: {m.width}x{m.height}")

        # Overlap check
        for i in range(len(layout.monitors)):
            m1 = layout.monitors[i]
            for j in range(i + 1, len(layout.monitors)):
                m2 = layout.monitors[j]
                if LayoutBuilder._rects_overlap(m1, m2):
                    raise ValueError(f"Monitors {m1.index} and {m2.index} overlap in coordinate space")

        # Enclosure check
        for m in layout.monitors:
            if m.right >= layout.bounding_width:
                raise ValueError(f"Monitor {m.index} exceeds bounding width {layout.bounding_width}")
            if m.bottom >= layout.bounding_height:
                raise ValueError(f"Monitor {m.index} exceeds bounding height {layout.bounding_height}")

    @staticmethod
    def _rects_overlap(m1: VirtualMonitor, m2: VirtualMonitor) -> bool:
        """Checks if two rectangles intersect."""
        if m1.x + m1.width <= m2.x or m2.x + m2.width <= m1.x:
            return False
        if m1.y + m1.height <= m2.y or m2.y + m2.height <= m1.y:
            return False
        return True
