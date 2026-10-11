use blou_core::{dvc, layout::LayoutBuilder};
use blou_rdp::display_control::encode_layout;
use ironrdp_core::encode_vec;
use ironrdp_displaycontrol::pdu::{
    DeviceScaleFactor, DisplayControlCapabilities, DisplayControlMonitorLayout, DisplayControlPdu,
    MonitorLayoutEntry,
};

fn oracle(layout: &blou_core::layout::DesktopLayout) -> Vec<u8> {
    let entries: Vec<_> = layout
        .monitors()
        .iter()
        .map(|m| {
            let entry = if m.is_primary {
                MonitorLayoutEntry::new_primary(m.width as u32, m.height as u32)
            } else {
                MonitorLayoutEntry::new_secondary(m.width as u32, m.height as u32)
            }
            .unwrap();
            entry
                .with_position(m.x, m.y)
                .unwrap()
                .with_desktop_scale_factor(100)
                .unwrap()
                .with_device_scale_factor(DeviceScaleFactor::Scale100Percent)
        })
        .collect();
    encode_vec(&DisplayControlPdu::MonitorLayout(
        DisplayControlMonitorLayout::new(&entries).unwrap(),
    ))
    .unwrap()
}

#[test]
fn one_to_four_monitor_bytes_equal_unmodified_upstream() {
    for count in 1..=4 {
        for (w, h) in [(1920, 1080), (200, 200), (8192, 8192), (1920, 1081)] {
            let layout = LayoutBuilder::horizontal_row(count, w, h).unwrap();
            let expected = oracle(&layout);
            assert_eq!(dvc::encode_monitor_layout_pdu(&layout).unwrap(), expected);
            assert_eq!(encode_layout(&layout).unwrap(), expected);
        }
    }
    let grid = LayoutBuilder::grid_2x2(1920, 1080).unwrap();
    assert_eq!(
        dvc::encode_monitor_layout_pdu(&grid).unwrap(),
        oracle(&grid)
    );
    assert_eq!(encode_layout(&grid).unwrap(), oracle(&grid));
}

#[test]
fn caps_bytes_equal_unmodified_upstream() {
    for count in 1..=4 {
        let caps = DisplayControlCapabilities::new(count, 1, 1).unwrap();
        assert_eq!(
            dvc::encode_caps_pdu(count, 1),
            encode_vec(&DisplayControlPdu::Caps(caps)).unwrap()
        );
    }
}

#[test]
fn adapter_rejects_odd_width_before_upstream_can_adjust_it() {
    assert_eq!(
        MonitorLayoutEntry::new_secondary(1921, 1080)
            .unwrap()
            .dimensions(),
        (1920, 1080),
        "control: upstream rounds odd width"
    );
    let layout = LayoutBuilder::horizontal_row(3, 1921, 1080).unwrap();
    assert!(encode_layout(&layout).is_err());
    assert_eq!(layout.monitors()[1].x, 1921);
}

#[test]
fn adapter_rejects_more_than_four_monitors() {
    assert!(encode_layout(&LayoutBuilder::horizontal_row(5, 1920, 1080).unwrap()).is_err());
}
