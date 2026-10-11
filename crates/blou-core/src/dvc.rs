//! Python-reference serialization for offline parity only.
//!
//! The Python reference uses zero in the MonitorLayoutSize field and placeholder physical
//! dimensions. These known discrepancies are preserved for this port and must be corrected
//! and cross-checked against upstream in N5 before any session uses these bytes.
use crate::{layout::DesktopLayout, CoreError};

pub fn encode_caps_pdu(max_monitors: u32, area_factor: u32) -> Vec<u8> {
    [5, 20, max_monitors, area_factor, 1]
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect()
}
pub fn encode_monitor_layout_pdu(layout: &DesktopLayout) -> Result<Vec<u8>, CoreError> {
    let count = u32::try_from(layout.count()).map_err(|_| CoreError("Invalid monitor count"))?;
    let mut bytes: Vec<u8> = [2, 16 + count * 40, 0, count]
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect();
    for m in layout.monitors() {
        let width = u32::try_from(m.width).map_err(|_| CoreError("Invalid width"))?;
        let height = u32::try_from(m.height).map_err(|_| CoreError("Invalid height"))?;
        bytes.extend(u32::from(m.is_primary).to_le_bytes());
        bytes.extend(m.x.to_le_bytes());
        bytes.extend(m.y.to_le_bytes());
        bytes.extend(
            [width, height, width, height, 0, 100, 100]
                .into_iter()
                .flat_map(u32::to_le_bytes),
        );
    }
    Ok(bytes)
}
