use blou_ironrdp_spike::{fabricated_row, spike_config};
use ironrdp_core::encode_vec;
use ironrdp_pdu::gcc::ClientMonitorData;

fn main() {
    let (layout, desktop) = fabricated_row(3, 1920, 1080);
    println!("desktop {}x{}", desktop.width, desktop.height);
    println!(
        "monitor data bytes: {:02x?}",
        encode_vec::<ClientMonitorData>(&layout).unwrap()
    );
    let _cfg = spike_config(layout, desktop);
}
