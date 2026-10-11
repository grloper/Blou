use blou_core::layout::{DesktopLayout, LayoutBuilder, VirtualMonitor};

fn mon(x: i32, y: i32, primary: bool) -> VirtualMonitor {
    VirtualMonitor {
        x,
        y,
        width: 1920,
        height: 1080,
        is_primary: primary,
    }
}

#[test]
fn create_horizontal_row_defaults() {
    let layout = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    assert_eq!(layout.count(), 3);
    assert_eq!(
        (layout.bounding_width(), layout.bounding_height()),
        (5760, 1080)
    );
    assert_eq!(
        layout.monitors(),
        &[mon(0, 0, true), mon(1920, 0, false), mon(3840, 0, false)]
    );
}

#[test]
fn create_grid_2x2() {
    let layout = LayoutBuilder::grid_2x2(1920, 1080).unwrap();
    assert_eq!(layout.count(), 4);
    assert_eq!(
        (layout.bounding_width(), layout.bounding_height()),
        (3840, 2160)
    );
    assert_eq!(
        layout.monitors(),
        &[
            mon(0, 0, true),
            mon(1920, 0, false),
            mon(0, 1080, false),
            mon(1920, 1080, false)
        ]
    );
}

#[test]
fn reject_primary_not_at_origin() {
    assert!(
        DesktopLayout::new(vec![mon(100, 0, true), mon(2020, 0, false)], 4000, 1080)
            .unwrap_err()
            .to_string()
            .contains("Primary monitor MUST be positioned at (0, 0)")
    );
}

#[test]
fn reject_multiple_primary_monitors() {
    assert!(
        DesktopLayout::new(vec![mon(0, 0, true), mon(1920, 0, true)], 3840, 1080)
            .unwrap_err()
            .to_string()
            .contains("Layout must contain exactly 1 primary monitor")
    );
}

#[test]
fn reject_overlapping_monitors() {
    assert!(
        DesktopLayout::new(vec![mon(0, 0, true), mon(1000, 0, false)], 3840, 1080)
            .unwrap_err()
            .to_string()
            .contains("overlap in coordinate space")
    );
}

#[test]
fn reject_negative_coordinates() {
    assert!(
        DesktopLayout::new(vec![mon(0, 0, true), mon(-1920, 0, false)], 3840, 1080)
            .unwrap_err()
            .to_string()
            .contains("negative coordinate")
    );
}

#[test]
fn three_monitor_bounding_box() {
    let layout = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    assert_eq!((layout.monitors()[0].x, layout.monitors()[0].y), (0, 0));
    assert!(layout.monitors()[0].is_primary);
    for m in layout.monitors() {
        assert!(m.x >= 0 && m.y >= 0 && m.width > 0 && m.height > 0);
    }
    assert_eq!(
        (layout.bounding_width(), layout.bounding_height()),
        (5760, 1080)
    );
}

#[test]
fn non_overlapping_contiguous_span() {
    let layout = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    for pair in layout.monitors().windows(2) {
        assert_eq!(pair[0].right() + 1, i64::from(pair[1].x));
    }
    assert_eq!(
        layout
            .monitors()
            .iter()
            .map(|m| (m.right() - i64::from(m.x) + 1) * (m.bottom() - i64::from(m.y) + 1))
            .sum::<i64>(),
        5760 * 1080
    );
}

#[test]
fn reject_invalid_counts_dimensions_enclosure_and_overflow() {
    for count in [0, 17, usize::MAX] {
        assert!(LayoutBuilder::horizontal_row(count, 1920, 1080).is_err());
    }
    for (w, h) in [
        (0, 1080),
        (-1, 1080),
        (1920, 0),
        (1920, -1),
        (i32::MAX, 1080),
    ] {
        assert!(LayoutBuilder::horizontal_row(3, w, h).is_err());
    }
    assert!(DesktopLayout::new(vec![mon(0, 0, false)], 1920, 1080).is_err());
    assert!(DesktopLayout::new(vec![mon(0, 0, true)], 1919, 1080).is_err());
    assert!(DesktopLayout::new(vec![mon(0, 0, true)], 1920, 1079).is_err());
}
