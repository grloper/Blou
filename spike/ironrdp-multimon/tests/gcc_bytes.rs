//! Offline verification that IronRDP's ClientConnector emits a client GCC block
//! carrying our fabricated 3x1920x1080 TS_UD_CS_MONITOR. We drive the real state
//! machine (X.224 request -> synthetic server confirm -> MCS Connect-Initial) and
//! then decode what it wrote. No network. Does NOT prove a Windows host accepts it.

use blou_ironrdp_spike::{fabricated_row, spike_config};
use ironrdp_connector::{ClientConnector, Sequence};
use ironrdp_core::{decode, encode_vec, WriteBuf};
use ironrdp_pdu::gcc::{self, ClientMonitorData, MonitorFlags};
use ironrdp_pdu::mcs::ConnectInitial;
use ironrdp_pdu::nego::{ConnectionConfirm, ResponseFlags, SecurityProtocol};
use ironrdp_pdu::x224::X224;

fn le32(v: i32) -> [u8; 4] {
    v.to_le_bytes()
}

/// Expected TS_UD_CS_MONITOR body (without the 4-byte UserDataHeader):
/// flags(0) u32, monitorCount u32, then 3 x { left, top, right, bottom, flags }.
fn expected_monitor_body() -> Vec<u8> {
    let mut v = vec![];
    v.extend(0u32.to_le_bytes());
    v.extend(3u32.to_le_bytes());
    for (i, left) in [0, 1920, 3840].into_iter().enumerate() {
        v.extend(le32(left));
        v.extend(le32(0));
        v.extend(le32(left + 1919));
        v.extend(le32(1079));
        v.extend((if i == 0 { 1u32 } else { 0 }).to_le_bytes());
    }
    v
}

#[test]
fn monitor_data_pdu_bytes_are_exact() {
    let (layout, desktop) = fabricated_row(3, 1920, 1080);
    assert_eq!((desktop.width, desktop.height), (5760, 1080));
    let bytes = encode_vec::<ClientMonitorData>(&layout).unwrap();
    assert_eq!(bytes.len(), 8 + 3 * 20);
    assert_eq!(bytes, expected_monitor_body());
    let back: ClientMonitorData = decode(&bytes).unwrap();
    assert_eq!(back, layout);
    assert!(back.monitors[0].flags.contains(MonitorFlags::PRIMARY));
    assert!(!back.monitors[1].flags.contains(MonitorFlags::PRIMARY));
}

#[test]
fn seventeen_monitors_rejected_by_encoder() {
    // The 16 limit is enforced by IronRDP's encoder (MS-RDPBCGR: max 16).
    let (mut layout, _) = fabricated_row(16, 100, 100);
    layout.monitors.push(layout.monitors[0].clone());
    assert!(encode_vec::<ClientMonitorData>(&layout).is_err());
}

/// Run the connector to the point it emits MCS Connect-Initial and return the decoded PDU.
fn connect_initial_for(config_layout_count: u16, extended_client_data: bool) -> ConnectInitial {
    let (layout, desktop) = fabricated_row(config_layout_count, 1920, 1080);
    let cfg = spike_config(layout, desktop);
    let mut c = ClientConnector::new(cfg, "127.0.0.1:3389".parse().unwrap());
    let mut out = WriteBuf::new();

    // 1. X.224 Connection Request (NLA only: HYBRID|HYBRID_EX requested).
    c.step(&[], None, &mut out).unwrap();
    assert!(!out.filled().is_empty());
    out.clear();

    // 2. Synthetic server X.224 Connection Confirm selecting HYBRID (NLA).
    let flags = if extended_client_data {
        ResponseFlags::EXTENDED_CLIENT_DATA_SUPPORTED
    } else {
        ResponseFlags::empty()
    };
    let confirm = encode_vec(&X224(ConnectionConfirm::Response {
        flags,
        protocol: SecurityProtocol::HYBRID,
    }))
    .unwrap();
    c.step(&confirm, None, &mut out).unwrap();
    out.clear();

    // 3. EnhancedSecurityUpgrade -> Credssp -> (caller did TLS + CredSSP; skip, offline).
    c.step_no_input(&mut out).unwrap();
    assert!(
        c.should_perform_credssp(),
        "NLA must be demanded when HYBRID selected"
    );
    c.mark_credssp_as_done();
    out.clear();

    // 4. Basic Settings Exchange: emits MCS Connect-Initial with the GCC client blocks.
    c.step_no_input(&mut out).unwrap();
    let x224: X224<ironrdp_pdu::x224::X224Data<'_>> = decode(out.filled()).unwrap();
    decode::<ConnectInitial>(x224.0.data.as_ref()).unwrap()
}

#[test]
fn connector_emits_three_monitors_in_gcc_client_blocks() {
    let ci = connect_initial_for(3, true);
    let blocks = ci.conference_create_request.gcc_blocks();
    let m = blocks.monitor.as_ref().expect("monitor block present");
    assert_eq!(m.monitors.len(), 3);
    let (want, desktop) = fabricated_row(3, 1920, 1080);
    assert_eq!(*m, want);
    // Core data must describe the 5760x1080 virtual desktop.
    assert_eq!(blocks.core.desktop_width, desktop.width);
    assert_eq!(blocks.core.desktop_height, desktop.height);
    // And the re-encoded block body equals the hand-computed bytes.
    assert_eq!(
        encode_vec::<ClientMonitorData>(m).unwrap(),
        expected_monitor_body()
    );
    // Early capability flag SUPPORT_MONITOR_LAYOUT_PDU is set so the server may send MonitorLayout PDU.
    let early = blocks.core.optional_data.early_capability_flags.unwrap();
    assert!(early.contains(gcc::ClientEarlyCapabilityFlags::SUPPORT_MONITOR_LAYOUT_PDU));
}

#[test]
fn monitor_block_omitted_if_server_lacks_extended_client_data() {
    // Real finding: IronRDP only sends TS_UD_CS_MONITOR when the server's X.224 confirm
    // sets EXTENDED_CLIENT_DATA_SUPPORTED. Windows 8+/Server 2012+ do (UNVERIFIED here).
    let ci = connect_initial_for(3, false);
    assert!(ci.conference_create_request.gcc_blocks().monitor.is_none());
}
