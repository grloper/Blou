use blou_core::{dvc, layout::LayoutBuilder};

fn word(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap())
}

#[test]
fn encode_caps_pdu() {
    let caps = dvc::encode_caps_pdu(4, 1);
    assert_eq!(caps.len(), 20);
    assert_eq!(
        (0..5).map(|i| word(&caps, i * 4)).collect::<Vec<_>>(),
        vec![5, 20, 4, 1, 1]
    );
}

#[test]
fn encode_3_monitor_layout_pdu() {
    let layout = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    let pdu = dvc::encode_monitor_layout_pdu(&layout).unwrap();
    assert_eq!(pdu.len(), 136);
    assert_eq!(word(&pdu, 0), 2);
    assert_eq!(word(&pdu, 4), 136);
    assert_eq!(word(&pdu, 12), 3);
    for (i, x) in [0, 1920, 3840].into_iter().enumerate() {
        let offset = 16 + i * 40;
        assert_eq!(word(&pdu, offset) & 1, u32::from(i == 0));
        assert_eq!((word(&pdu, offset + 4), word(&pdu, offset + 8)), (x, 0));
        assert_eq!(
            (word(&pdu, offset + 12), word(&pdu, offset + 16)),
            (1920, 1080)
        );
    }
}

#[test]
fn monitor_layout_size_and_unknown_physical_dimensions() {
    for count in 1..=4 {
        let pdu = dvc::encode_monitor_layout_pdu(
            &LayoutBuilder::horizontal_row(count, 1920, 1080).unwrap(),
        )
        .unwrap();
        assert_eq!(word(&pdu, 8), 40);
        for i in 0..count {
            let offset = 16 + i * 40;
            assert_eq!((word(&pdu, offset + 20), word(&pdu, offset + 24)), (0, 0));
            assert_eq!(
                (
                    word(&pdu, offset + 28),
                    word(&pdu, offset + 32),
                    word(&pdu, offset + 36)
                ),
                (0, 100, 100)
            );
        }
    }
}

#[test]
fn odd_widths_are_rejected_without_rounding() {
    let layout = LayoutBuilder::horizontal_row(3, 1921, 1080).unwrap();
    assert!(dvc::encode_monitor_layout_pdu(&layout).is_err());
    assert_eq!(layout.monitors()[1].x, 1921);
    assert_eq!(layout.monitors()[1].width, 1921);
}

#[test]
fn display_control_rejects_out_of_product_or_protocol_range() {
    for count in [5, 16] {
        assert!(dvc::encode_monitor_layout_pdu(
            &LayoutBuilder::horizontal_row(count, 1920, 1080).unwrap()
        )
        .is_err());
    }
    for (w, h) in [(199, 1080), (8194, 1080), (1920, 199), (1920, 8193)] {
        assert!(
            dvc::encode_monitor_layout_pdu(&LayoutBuilder::horizontal_row(1, w, h).unwrap())
                .is_err()
        );
    }
}
