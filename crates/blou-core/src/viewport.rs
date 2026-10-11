//! Uniform contain-mode transforms and swipe navigation. Pixels never pass through this API.
use crate::{
    layout::{DesktopLayout, VirtualMonitor},
    CoreError,
};

#[derive(Debug, Clone, Copy)]
pub struct ViewportDimensions {
    pub width: f64,
    pub height: f64,
}
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rect {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

pub struct CoordinateMapper {
    layout: DesktopLayout,
    phone: ViewportDimensions,
    active: usize,
    scale: f64,
    offset_x: f64,
    offset_y: f64,
}
impl CoordinateMapper {
    pub fn new(
        layout: DesktopLayout,
        phone: ViewportDimensions,
        initial: usize,
    ) -> Result<Self, CoreError> {
        if !phone.width.is_finite()
            || !phone.height.is_finite()
            || phone.width <= 0.0
            || phone.height <= 0.0
        {
            return Err(CoreError("Viewport dimensions must be finite and positive"));
        }
        let mut mapper = Self {
            layout,
            phone,
            active: 0,
            scale: 1.0,
            offset_x: 0.0,
            offset_y: 0.0,
        };
        mapper.set_active_monitor(initial)?;
        Ok(mapper)
    }
    pub fn active_monitor_index(&self) -> usize {
        self.active
    }
    pub fn active_monitor(&self) -> &VirtualMonitor {
        &self.layout.monitors()[self.active]
    }
    pub fn set_active_monitor(&mut self, index: usize) -> Result<(), CoreError> {
        let m = self
            .layout
            .monitors()
            .get(index)
            .ok_or(CoreError("Monitor index out of range"))?;
        let scale =
            (self.phone.width / f64::from(m.width)).min(self.phone.height / f64::from(m.height));
        if !scale.is_finite() || scale <= 0.0 {
            return Err(CoreError("Viewport scale out of range"));
        }
        self.scale = scale;
        self.offset_x = (self.phone.width - f64::from(m.width) * scale) / 2.0;
        self.offset_y = (self.phone.height - f64::from(m.height) * scale) / 2.0;
        self.active = index;
        Ok(())
    }
    pub fn scale(&self) -> f64 {
        self.scale
    }
    pub fn offset_x(&self) -> f64 {
        self.offset_x
    }
    pub fn offset_y(&self) -> f64 {
        self.offset_y
    }
    pub fn screen_to_server(&self, x: f64, y: f64) -> Option<(i32, i32)> {
        if !x.is_finite() || !y.is_finite() {
            return None;
        }
        let m = self.active_monitor();
        let lx = x - self.offset_x;
        let ly = y - self.offset_y;
        if lx < 0.0
            || ly < 0.0
            || lx >= f64::from(m.width) * self.scale
            || ly >= f64::from(m.height) * self.scale
        {
            return None;
        }
        let rx = ((lx / self.scale) as i32).clamp(0, m.width - 1);
        let ry = ((ly / self.scale) as i32).clamp(0, m.height - 1);
        Some((m.x + rx, m.y + ry))
    }
    pub fn server_to_screen(&self, x: i32, y: i32) -> Option<(f64, f64)> {
        let m = self.active_monitor();
        if x < m.x || y < m.y || i64::from(x) > m.right() || i64::from(y) > m.bottom() {
            return None;
        }
        Some((
            self.offset_x + f64::from(x - m.x) * self.scale,
            self.offset_y + f64::from(y - m.y) * self.scale,
        ))
    }
    pub fn clip_damage_rect(&self, damage: Rect) -> Option<Rect> {
        if ![damage.x, damage.y, damage.width, damage.height]
            .iter()
            .all(|v| v.is_finite())
            || damage.width <= 0.0
            || damage.height <= 0.0
        {
            return None;
        }
        let m = self.active_monitor();
        let mx = f64::from(m.x);
        let my = f64::from(m.y);
        let x1 = damage.x.max(mx);
        let y1 = damage.y.max(my);
        let x2 = (damage.x + damage.width).min(mx + f64::from(m.width));
        let y2 = (damage.y + damage.height).min(my + f64::from(m.height));
        if x1 >= x2 || y1 >= y2 {
            return None;
        }
        Some(Rect {
            x: x1 - mx,
            y: y1 - my,
            width: x2 - x1,
            height: y2 - y1,
        })
    }
}

#[derive(Default)]
pub struct SwipeNavigationController {
    start: Option<(f64, f64)>,
}
impl SwipeNavigationController {
    pub fn on_touch_down(&mut self, x: f64, y: f64) {
        self.start = if x.is_finite() && y.is_finite() {
            Some((x, y))
        } else {
            None
        };
    }
    pub fn on_touch_move(&mut self, x: f64, y: f64) -> Option<f64> {
        if !x.is_finite() || !y.is_finite() {
            self.start = None;
            return None;
        }
        self.start.map(|(sx, _)| x - sx)
    }
    pub fn on_touch_up(
        &mut self,
        mapper: &mut CoordinateMapper,
        x: f64,
        y: f64,
    ) -> Result<bool, CoreError> {
        let Some((sx, _)) = self.start.take() else {
            return Ok(false);
        };
        if !x.is_finite() || !y.is_finite() {
            return Ok(false);
        }
        let delta = x - sx;
        let threshold = mapper.phone.width * 0.20;
        let index = mapper.active_monitor_index();
        let next = if delta < -threshold && index + 1 < mapper.layout.count() {
            Some(index + 1)
        } else if delta > threshold && index > 0 {
            Some(index - 1)
        } else {
            None
        };
        match next {
            Some(i) => {
                mapper.set_active_monitor(i)?;
                Ok(true)
            }
            None => Ok(false),
        }
    }
}
