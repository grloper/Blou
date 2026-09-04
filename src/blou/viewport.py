"""
Blou Viewport & Coordinate Translation Engine.

Handles viewport cropping, coordinate transformation between phone screen
and remote multi-monitor canvas, and swipe navigation state.
"""
from dataclasses import dataclass
from typing import Optional, Tuple
from .layout import DesktopLayout, VirtualMonitor


@dataclass(frozen=True)
class ViewportDimensions:
    width: float
    height: float


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


class CoordinateMapper:
    """
    Translates input coordinates between:
    1. Phone touch display (pixel coordinates [0..phone_w, 0..phone_h])
    2. Active virtual monitor viewport (scaled/letterboxed rect)
    3. Full composite remote framebuffer (absolute coordinates [0..total_w, 0..total_h])
    """

    def __init__(
        self,
        layout: DesktopLayout,
        phone_screen: ViewportDimensions,
        initial_monitor: int = 0
    ):
        self.layout = layout
        self.phone_screen = phone_screen
        self.active_monitor_index = initial_monitor
        self._update_transform()

    @property
    def active_monitor(self) -> VirtualMonitor:
        return self.layout.get_monitor(self.active_monitor_index)

    def set_active_monitor(self, index: int) -> None:
        if index < 0 or index >= self.layout.count:
            raise IndexError(f"Monitor index {index} out of range [0..{self.layout.count - 1}]")
        self.active_monitor_index = index
        self._update_transform()

    def _update_transform(self) -> None:
        """Computes uniform aspect ratio scaling and letterbox/pillarbox offsets."""
        mon = self.active_monitor
        scale_x = self.phone_screen.width / float(mon.width)
        scale_y = self.phone_screen.height / float(mon.height)
        # Uniform fit (contain mode)
        self.scale = min(scale_x, scale_y)

        rendered_w = mon.width * self.scale
        rendered_h = mon.height * self.scale

        # Centering offsets on phone screen
        self.offset_x = (self.phone_screen.width - rendered_w) / 2.0
        self.offset_y = (self.phone_screen.height - rendered_h) / 2.0

    def screen_to_server(self, screen_x: float, screen_y: float) -> Optional[Tuple[int, int]]:
        """
        Maps a touch event on the phone screen to absolute remote framebuffer coordinates.
        Returns None if touch lands in pillarbox/letterbox margin.
        """
        mon = self.active_monitor

        # Subtract viewport centering offset
        local_x = screen_x - self.offset_x
        local_y = screen_y - self.offset_y

        # Check inside rendered monitor bounds
        rendered_w = mon.width * self.scale
        rendered_h = mon.height * self.scale

        if local_x < 0 or local_x >= rendered_w or local_y < 0 or local_y >= rendered_h:
            return None  # Touched letterbox margin

        # Unscale to monitor-relative pixels
        monitor_rel_x = int(local_x / self.scale)
        monitor_rel_y = int(local_y / self.scale)

        # Clamp to monitor bounds
        monitor_rel_x = max(0, min(mon.width - 1, monitor_rel_x))
        monitor_rel_y = max(0, min(mon.height - 1, monitor_rel_y))

        # Add absolute monitor origin in composite framebuffer
        abs_x = mon.x + monitor_rel_x
        abs_y = mon.y + monitor_rel_y
        return (abs_x, abs_y)

    def server_to_screen(self, server_x: int, server_y: int) -> Optional[Tuple[float, float]]:
        """
        Maps an absolute remote framebuffer coordinate to phone screen coordinates.
        Returns None if the coordinate belongs to a monitor not currently in viewport.
        """
        mon = self.active_monitor

        # Check if point lies within active monitor
        if not (mon.x <= server_x < mon.x + mon.width and mon.y <= server_y < mon.y + mon.height):
            return None  # Point is on another virtual monitor

        monitor_rel_x = server_x - mon.x
        monitor_rel_y = server_y - mon.y

        screen_x = self.offset_x + (monitor_rel_x * self.scale)
        screen_y = self.offset_y + (monitor_rel_y * self.scale)
        return (screen_x, screen_y)

    def clip_damage_rect(self, damage: Rect) -> Optional[Rect]:
        """
        Clips a server framebuffer damage rectangle to the active monitor viewport.
        Returns clipped local rect for rendering, or None if damage is offscreen.
        """
        mon = self.active_monitor
        mon_rect = Rect(mon.x, mon.y, mon.width, mon.height)

        # Compute intersection
        ix1 = max(damage.x, mon_rect.x)
        iy1 = max(damage.y, mon_rect.y)
        ix2 = min(damage.right, mon_rect.right)
        iy2 = min(damage.bottom, mon_rect.bottom)

        if ix1 >= ix2 or iy1 >= iy2:
            return None  # No overlap with active monitor

        # Convert to active monitor local coordinates
        return Rect(
            x=ix1 - mon.x,
            y=iy1 - mon.y,
            width=ix2 - ix1,
            height=iy2 - iy1
        )


class SwipeNavigationController:
    """
    Manages horizontal swipe gesture state machine for monitor switching.
    Enforces minimum drag distance and velocity thresholds.
    """

    DEFAULT_THRESHOLD_RATIO = 0.20  # 20% screen width to trigger switch

    def __init__(self, coordinate_mapper: CoordinateMapper):
        self.mapper = coordinate_mapper
        self._touch_start_x: Optional[float] = None
        self._touch_start_y: Optional[float] = None
        self._is_swiping = False

    def on_touch_down(self, x: float, y: float) -> None:
        self._touch_start_x = x
        self._touch_start_y = y
        self._is_swiping = False

    def on_touch_move(self, x: float, y: float) -> Optional[float]:
        """Returns current drag delta for visual bounce/slide animation."""
        if self._touch_start_x is None:
            return None
        delta_x = x - self._touch_start_x
        delta_y = y - (self._touch_start_y or y)

        # Detect intentional horizontal swipe vs vertical scroll
        if abs(delta_x) > 30 and abs(delta_x) > abs(delta_y) * 1.5:
            self._is_swiping = True
        return delta_x

    def on_touch_up(self, x: float, y: float) -> bool:
        """
        Completes gesture. If delta exceeds threshold, switches monitor.
        Returns True if a monitor switch occurred.
        """
        if self._touch_start_x is None:
            return False

        delta_x = x - self._touch_start_x
        threshold = self.mapper.phone_screen.width * self.DEFAULT_THRESHOLD_RATIO

        switched = False
        if delta_x < -threshold:
            # Swipe left -> go to next monitor
            if self.mapper.active_monitor_index < self.mapper.layout.count - 1:
                self.mapper.set_active_monitor(self.mapper.active_monitor_index + 1)
                switched = True
        elif delta_x > threshold:
            # Swipe right -> go to previous monitor
            if self.mapper.active_monitor_index > 0:
                self.mapper.set_active_monitor(self.mapper.active_monitor_index - 1)
                switched = True

        self._touch_start_x = None
        self._touch_start_y = None
        self._is_swiping = False
        return switched
