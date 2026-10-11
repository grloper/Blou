//! Validated virtual monitor geometry. Inclusive right/bottom match the GCC convention.
use crate::CoreError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct VirtualMonitor {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
    pub is_primary: bool,
}
impl VirtualMonitor {
    pub fn right(&self) -> i64 {
        i64::from(self.x) + i64::from(self.width) - 1
    }
    pub fn bottom(&self) -> i64 {
        i64::from(self.y) + i64::from(self.height) - 1
    }
}

#[derive(Debug, Clone)]
pub struct DesktopLayout {
    monitors: Vec<VirtualMonitor>,
    bounding_width: i32,
    bounding_height: i32,
}
impl DesktopLayout {
    pub fn new(
        monitors: Vec<VirtualMonitor>,
        bounding_width: i32,
        bounding_height: i32,
    ) -> Result<Self, CoreError> {
        if !(1..=16).contains(&monitors.len()) {
            return Err(CoreError("Invalid monitor count"));
        }
        let mut primaries = monitors.iter().filter(|m| m.is_primary);
        let primary = primaries
            .next()
            .ok_or(CoreError("Layout must contain exactly 1 primary monitor"))?;
        if primaries.next().is_some() {
            return Err(CoreError("Layout must contain exactly 1 primary monitor"));
        }
        if primary.x != 0 || primary.y != 0 {
            return Err(CoreError("Primary monitor MUST be positioned at (0, 0)"));
        }
        for m in &monitors {
            if m.x < 0 || m.y < 0 {
                return Err(CoreError("Monitor has negative coordinate"));
            }
            if m.width <= 0 || m.height <= 0 {
                return Err(CoreError("Monitor has invalid dimensions"));
            }
            if m.right() >= i64::from(bounding_width) || m.bottom() >= i64::from(bounding_height) {
                return Err(CoreError("Monitor exceeds bounding dimensions"));
            }
        }
        for (i, a) in monitors.iter().enumerate() {
            for b in &monitors[i + 1..] {
                if i64::from(a.x) <= b.right()
                    && i64::from(b.x) <= a.right()
                    && i64::from(a.y) <= b.bottom()
                    && i64::from(b.y) <= a.bottom()
                {
                    return Err(CoreError("Monitors overlap in coordinate space"));
                }
            }
        }
        Ok(Self {
            monitors,
            bounding_width,
            bounding_height,
        })
    }
    pub fn count(&self) -> usize {
        self.monitors.len()
    }
    pub fn monitors(&self) -> &[VirtualMonitor] {
        &self.monitors
    }
    pub fn bounding_width(&self) -> i32 {
        self.bounding_width
    }
    pub fn bounding_height(&self) -> i32 {
        self.bounding_height
    }
}

pub struct LayoutBuilder;
impl LayoutBuilder {
    pub fn horizontal_row(
        count: usize,
        width: i32,
        height: i32,
    ) -> Result<DesktopLayout, CoreError> {
        if !(1..=16).contains(&count) {
            return Err(CoreError("Invalid monitor count"));
        }
        let count_i32 = i32::try_from(count).map_err(|_| CoreError("Invalid monitor count"))?;
        let bounding_width = width
            .checked_mul(count_i32)
            .ok_or(CoreError("Bounding width overflow"))?;
        let monitors = (0..count_i32)
            .map(|i| VirtualMonitor {
                x: i * width,
                y: 0,
                width,
                height,
                is_primary: i == 0,
            })
            .collect();
        DesktopLayout::new(monitors, bounding_width, height)
    }
    pub fn grid_2x2(width: i32, height: i32) -> Result<DesktopLayout, CoreError> {
        let bw = width
            .checked_mul(2)
            .ok_or(CoreError("Bounding width overflow"))?;
        let bh = height
            .checked_mul(2)
            .ok_or(CoreError("Bounding height overflow"))?;
        let monitors = [(0, 0), (width, 0), (0, height), (width, height)]
            .into_iter()
            .enumerate()
            .map(|(i, (x, y))| VirtualMonitor {
                x,
                y,
                width,
                height,
                is_primary: i == 0,
            })
            .collect();
        DesktopLayout::new(monitors, bw, bh)
    }
}
