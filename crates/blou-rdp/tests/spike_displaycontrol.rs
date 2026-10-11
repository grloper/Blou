//! MS-RDPEDISP DISPLAYCONTROL_MONITOR_LAYOUT_PDU for 3x1920x1080 via ironrdp-displaycontrol.
//! Offline byte check; whether Windows applies it mid-session is UNVERIFIED.
use ironrdp_core::encode_vec;
use ironrdp_displaycontrol::pdu::{
    DisplayControlMonitorLayout, DisplayControlPdu, MonitorLayoutEntry,
};

fn layout() -> DisplayControlMonitorLayout {
    let e = |left: i32, primary: bool| {
        let m = if primary {
            MonitorLayoutEntry::new_primary(1920, 1080)
        } else {
            MonitorLayoutEntry::new_secondary(1920, 1080)
        }
        .unwrap();
        m.with_position(left, 0).unwrap()
    };
    DisplayControlMonitorLayout::new(&[e(0, true), e(1920, false), e(3840, false)]).unwrap()
}

fn u32_at(b: &[u8], off: usize) -> u32 {
    u32::from_le_bytes(b[off..off + 4].try_into().unwrap())
}

#[test]
fn three_monitor_layout_pdu_bytes() {
    let b = encode_vec(&DisplayControlPdu::MonitorLayout(layout())).unwrap();
    // header: Type=DISPLAYCONTROL_PDU_TYPE_MONITOR_LAYOUT (2), Length
    assert_eq!(u32_at(&b, 0), 2);
    assert_eq!(u32_at(&b, 4) as usize, b.len());
    assert_eq!(u32_at(&b, 8), 40, "MonitorLayoutSize");
    assert_eq!(u32_at(&b, 12), 3, "NumMonitors");
    assert_eq!(b.len(), 16 + 3 * 40);
    // entries: Flags, Left, Top, Width, Height, ...
    for (i, left) in [0u32, 1920, 3840].into_iter().enumerate() {
        let o = 16 + i * 40;
        assert_eq!(u32_at(&b, o), if i == 0 { 1 } else { 0 }, "flags (primary)");
        assert_eq!(u32_at(&b, o + 4), left);
        assert_eq!(u32_at(&b, o + 8), 0);
        assert_eq!(u32_at(&b, o + 12), 1920);
        assert_eq!(u32_at(&b, o + 16), 1080);
    }
}

#[test]
fn rejects_two_primaries_and_adjusts_odd_width() {
    let p = MonitorLayoutEntry::new_primary(1920, 1080).unwrap();
    assert!(DisplayControlMonitorLayout::new(&[p.clone(), p]).is_err());
    // Odd widths are NOT rejected: IronRDP silently rounds down (and logs a warning).
    // Blou must pre-adjust sizes itself so the declared layout is what it believes.
    let adj = MonitorLayoutEntry::new_secondary(1921, 1080).unwrap();
    assert_eq!(adj.dimensions(), (1920, 1080));
    assert!(
        MonitorLayoutEntry::new_secondary(100, 1080).is_err(),
        "min 200"
    );
}
