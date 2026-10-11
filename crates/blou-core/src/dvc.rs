//! Validated display-control serialization, cross-checked against pinned upstream PDUs.
//! Product layouts contain 1..=4 monitors. Odd widths are errors, never rounded.
use crate::{layout::DesktopLayout, CoreError};

pub fn validate_display_layout(layout: &DesktopLayout) -> Result<(), CoreError> {
    if !(1..=4).contains(&layout.count()) {
        return Err(CoreError("Display-control layouts require 1..=4 monitors"));
    }
    for m in layout.monitors() {
        if !(200..=8192).contains(&m.width) || !(200..=8192).contains(&m.height) {
            return Err(CoreError(
                "Display-control dimensions must be within 200..=8192",
            ));
        }
        if m.width & 1 != 0 {
            return Err(CoreError("Odd monitor widths are rejected; no rounding"));
        }
    }
    Ok(())
}

pub fn encode_caps_pdu(max_monitors: u32, area_factor: u32) -> Vec<u8> {
    [5, 20, max_monitors, area_factor, 1]
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect()
}
pub fn encode_monitor_layout_pdu(layout: &DesktopLayout) -> Result<Vec<u8>, CoreError> {
    validate_display_layout(layout)?;
    let count = u32::try_from(layout.count()).map_err(|_| CoreError("Invalid monitor count"))?;
    let mut bytes: Vec<u8> = [2, 16 + count * 40, 40, count]
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
            // Unknown physical millimetres are zero (ignored), never pixel dimensions.
            [width, height, 0, 0, 0, 100, 100]
                .into_iter()
                .flat_map(u32::to_le_bytes),
        );
    }
    Ok(bytes)
}
