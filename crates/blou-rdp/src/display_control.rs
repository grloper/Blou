//! Convert validated product geometry to unmodified upstream display-control PDUs.
use blou_core::{dvc::validate_display_layout, layout::DesktopLayout};
use ironrdp_core::encode_vec;
use ironrdp_displaycontrol::pdu::{
    DeviceScaleFactor, DisplayControlMonitorLayout, DisplayControlPdu, MonitorLayoutEntry,
};

pub fn encode_layout(
    layout: &DesktopLayout,
) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
    validate_display_layout(layout)?;
    let entries = layout
        .monitors()
        .iter()
        .map(|m| {
            let width = u32::try_from(m.width)?;
            let height = u32::try_from(m.height)?;
            let entry = if m.is_primary {
                MonitorLayoutEntry::new_primary(width, height)?
            } else {
                MonitorLayoutEntry::new_secondary(width, height)?
            };
            Ok(entry
                .with_position(m.x, m.y)?
                .with_desktop_scale_factor(100)?
                .with_device_scale_factor(DeviceScaleFactor::Scale100Percent))
        })
        .collect::<Result<Vec<_>, Box<dyn std::error::Error + Send + Sync>>>()?;
    Ok(encode_vec(&DisplayControlPdu::MonitorLayout(
        DisplayControlMonitorLayout::new(&entries)?,
    ))?)
}
