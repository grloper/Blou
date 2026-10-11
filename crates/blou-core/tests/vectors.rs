use blou_core::{
    dvc,
    layout::LayoutBuilder,
    pin::CertificatePinningVerifier,
    viewport::{CoordinateMapper, Rect, SwipeNavigationController, ViewportDimensions},
};
use serde_json::{json, Value};

fn integer(v: &Value) -> i32 {
    i32::try_from(v.as_i64().unwrap()).unwrap()
}
fn real(v: &Value) -> f64 {
    v.as_f64().unwrap()
}
fn rect(v: &Value) -> Rect {
    Rect {
        x: real(&v["x"]),
        y: real(&v["y"]),
        width: real(&v["width"]),
        height: real(&v["height"]),
    }
}

#[test]
fn python_golden_vectors_match_rust_outputs() {
    let v: Value =
        serde_json::from_str(include_str!("../../../tests/vectors/portable-core.json")).unwrap();
    for entry in v["layouts"].as_array().unwrap() {
        let layout = if entry["kind"] == "grid" {
            LayoutBuilder::grid_2x2(1920, 1080)
        } else {
            LayoutBuilder::horizontal_row(entry["count"].as_u64().unwrap() as usize, 1920, 1080)
        }
        .unwrap();
        assert_eq!(
            json!([layout.bounding_width(), layout.bounding_height()]),
            entry["bounds"]
        );
        let monitors: Vec<_> = layout.monitors().iter().enumerate().map(|(i, m)| json!({"index": i, "x": m.x, "y": m.y, "width": m.width, "height": m.height, "is_primary": m.is_primary})).collect();
        assert_eq!(json!(monitors), entry["monitors"]);
        assert_eq!(
            json!(dvc::encode_monitor_layout_pdu(&layout).unwrap()),
            entry["dvc"]
        );
    }
    assert_eq!(json!(dvc::encode_caps_pdu(4, 1)), v["caps"]);
    for entry in v["viewport"].as_array().unwrap() {
        let mapper = CoordinateMapper::new(
            LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap(),
            ViewportDimensions {
                width: real(&entry["phone"][0]),
                height: real(&entry["phone"][1]),
            },
            entry["monitor"].as_u64().unwrap() as usize,
        )
        .unwrap();
        assert_eq!(
            json!([mapper.scale(), mapper.offset_x(), mapper.offset_y()]),
            entry["transform"]
        );
        for point in entry["screen"].as_array().unwrap() {
            assert_eq!(
                json!(mapper.screen_to_server(real(&point["input"][0]), real(&point["input"][1]))),
                point["output"]
            );
        }
        for point in entry["server"].as_array().unwrap() {
            assert_eq!(
                json!(mapper
                    .server_to_screen(integer(&point["input"][0]), integer(&point["input"][1]))),
                point["output"]
            );
        }
        for damage in entry["damage"].as_array().unwrap() {
            let output = mapper
                .clip_damage_rect(rect(&damage["input"]))
                .map(|r| json!({"x": r.x, "y": r.y, "width": r.width, "height": r.height}));
            let expected = damage["output"].as_object().map(|_| {
                let r = rect(&damage["output"]);
                json!({"x": r.x, "y": r.y, "width": r.width, "height": r.height})
            });
            assert_eq!(output, expected);
        }
    }
    for swipe in v["swipes"].as_array().unwrap() {
        let mut mapper = CoordinateMapper::new(
            LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap(),
            ViewportDimensions {
                width: 1000.0,
                height: 500.0,
            },
            swipe["initial"].as_u64().unwrap() as usize,
        )
        .unwrap();
        let mut controller = SwipeNavigationController::default();
        controller.on_touch_down(real(&swipe["start"]), 250.0);
        assert_eq!(
            controller.on_touch_move(real(&swipe["end"]), 250.0),
            Some(real(&swipe["delta"]))
        );
        assert_eq!(
            controller
                .on_touch_up(&mut mapper, real(&swipe["end"]), 250.0)
                .unwrap(),
            swipe["switched"].as_bool().unwrap()
        );
        assert_eq!(json!(mapper.active_monitor_index()), swipe["active"]);
    }
    let bytes: Vec<u8> = v["pin"]["synthetic"]
        .as_array()
        .unwrap()
        .iter()
        .map(|b| u8::try_from(b.as_u64().unwrap()).unwrap())
        .collect();
    assert_eq!(
        CertificatePinningVerifier::fingerprint(&bytes).unwrap(),
        v["pin"]["sha256"].as_str().unwrap()
    );
}
