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
