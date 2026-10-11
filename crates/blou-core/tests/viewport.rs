use blou_core::layout::LayoutBuilder;
use blou_core::viewport::{CoordinateMapper, Rect, SwipeNavigationController, ViewportDimensions};

fn mapper(width: f64, height: f64) -> CoordinateMapper {
    CoordinateMapper::new(
        LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap(),
        ViewportDimensions { width, height },
        0,
    )
    .unwrap()
}

#[test]
fn initial_state_on_monitor_zero() {
    let m = mapper(2340.0, 1080.0);
    assert_eq!(m.active_monitor_index(), 0);
    let mon = m.active_monitor();
    assert_eq!((mon.x, mon.y, mon.width, mon.height), (0, 0, 1920, 1080));
}

#[test]
fn screen_to_server_monitor_zero() {
    let m = mapper(2340.0, 1080.0);
    assert_eq!((m.scale(), m.offset_x(), m.offset_y()), (1.0, 210.0, 0.0));
    assert_eq!(m.screen_to_server(210.0, 0.0), Some((0, 0)));
    assert_eq!(m.screen_to_server(1170.0, 540.0), Some((960, 540)));
    assert_eq!(m.screen_to_server(50.0, 540.0), None);
}

#[test]
fn screen_to_server_monitor_one() {
    let mut m = mapper(2340.0, 1080.0);
    m.set_active_monitor(1).unwrap();
    assert_eq!(m.active_monitor_index(), 1);
    assert_eq!(m.screen_to_server(210.0, 0.0), Some((1920, 0)));
    assert_eq!(m.screen_to_server(1170.0, 540.0), Some((2880, 540)));
}

#[test]
fn screen_to_server_monitor_two() {
    let mut m = mapper(2340.0, 1080.0);
    m.set_active_monitor(2).unwrap();
    assert_eq!(m.screen_to_server(210.0, 0.0), Some((3840, 0)));
}

#[test]
fn server_to_screen_mapping() {
    let mut m = mapper(2340.0, 1080.0);
    assert_eq!(m.server_to_screen(960, 540), Some((1170.0, 540.0)));
    assert_eq!(m.server_to_screen(2000, 500), None);
    m.set_active_monitor(1).unwrap();
    assert!(m.server_to_screen(2000, 500).is_some());
}

#[test]
fn damage_rect_clipping() {
    let mut m = mapper(2340.0, 1080.0);
    m.set_active_monitor(1).unwrap();
    assert_eq!(
        m.clip_damage_rect(Rect {
            x: 2000.0,
            y: 100.0,
            width: 500.0,
            height: 300.0
        }),
        Some(Rect {
            x: 80.0,
            y: 100.0,
            width: 500.0,
            height: 300.0
        })
    );
    assert_eq!(
        m.clip_damage_rect(Rect {
            x: 100.0,
            y: 100.0,
            width: 500.0,
            height: 300.0
        }),
        None
    );
    let clipped = m
        .clip_damage_rect(Rect {
            x: 1500.0,
            y: 0.0,
            width: 1000.0,
            height: 500.0,
        })
        .unwrap();
    assert_eq!((clipped.x, clipped.width), (0.0, 580.0));
}

#[test]
fn swipe_left_switches_to_next_monitor() {
    let mut m = mapper(1000.0, 500.0);
    let mut s = SwipeNavigationController::default();
    s.on_touch_down(500.0, 250.0);
    assert_eq!(s.on_touch_move(200.0, 250.0), Some(-300.0));
    assert!(s.on_touch_up(&mut m, 200.0, 250.0).unwrap());
    assert_eq!(m.active_monitor_index(), 1);
}

#[test]
fn small_drag_does_not_switch() {
    let mut m = mapper(1000.0, 500.0);
    let mut s = SwipeNavigationController::default();
    s.on_touch_down(500.0, 250.0);
    s.on_touch_move(450.0, 250.0);
    assert!(!s.on_touch_up(&mut m, 450.0, 250.0).unwrap());
    assert_eq!(m.active_monitor_index(), 0);
}

#[test]
fn swipe_right_switches_to_previous_monitor() {
    let mut m = mapper(1000.0, 500.0);
    m.set_active_monitor(2).unwrap();
    let mut s = SwipeNavigationController::default();
    s.on_touch_down(200.0, 250.0);
    s.on_touch_move(600.0, 250.0);
    assert!(s.on_touch_up(&mut m, 600.0, 250.0).unwrap());
    assert_eq!(m.active_monitor_index(), 1);
}

#[test]
fn cannot_swipe_past_boundaries() {
    let mut m = mapper(1000.0, 500.0);
    let mut s = SwipeNavigationController::default();
    s.on_touch_down(200.0, 250.0);
    assert!(!s.on_touch_up(&mut m, 600.0, 250.0).unwrap());
    assert_eq!(m.active_monitor_index(), 0);
    m.set_active_monitor(2).unwrap();
    s.on_touch_down(800.0, 250.0);
    assert!(!s.on_touch_up(&mut m, 200.0, 250.0).unwrap());
    assert_eq!(m.active_monitor_index(), 2);
}

#[test]
fn reject_invalid_viewports_indices_and_nonfinite_input() {
    for (width, height) in [
        (0.0, 1080.0),
        (2340.0, -1.0),
        (f64::NAN, 1080.0),
        (f64::INFINITY, 1080.0),
    ] {
        assert!(CoordinateMapper::new(
            LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap(),
            ViewportDimensions { width, height },
            0
        )
        .is_err());
    }
    let mut m = mapper(2340.0, 1080.0);
    assert!(m.set_active_monitor(3).is_err());
    assert_eq!(m.active_monitor_index(), 0);
    assert_eq!(m.screen_to_server(f64::NAN, 540.0), None);
    assert_eq!(m.screen_to_server(1170.0, f64::INFINITY), None);
    assert_eq!(m.screen_to_server(2130.0, 540.0), None);
    assert_eq!(m.screen_to_server(1170.0, 1080.0), None);
    assert_eq!(
        m.clip_damage_rect(Rect {
            x: f64::NAN,
            y: 0.0,
            width: 100.0,
            height: 100.0
        }),
        None
    );
}
