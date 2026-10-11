//! Reused spike byte assertions, now driven through the product config builder.
//! CredSSP completion below is synthetic test control; no TLS/NLA host connection is claimed.
use blou_core::layout::{DesktopLayout, LayoutBuilder, VirtualMonitor};
use blou_rdp::config::{build_connection_config, monitor_data};
use ironrdp_connector::{ClientConnector, Credentials, Sequence};
use ironrdp_core::{decode, encode_vec, WriteBuf};
use ironrdp_pdu::gcc::{self, ClientMonitorData, Monitor, MonitorFlags};
use ironrdp_pdu::mcs::ConnectInitial;
use ironrdp_pdu::nego::{ConnectionConfirm, ResponseFlags, SecurityProtocol};
use ironrdp_pdu::x224::X224;

fn credentials() -> Credentials {
    Credentials::UsernamePassword {
        username: "USERNAME".into(),
        password: "PASSWORD".into(),
    }
}
fn expected_monitor_body() -> Vec<u8> {
    let mut v = vec![];
    v.extend(0u32.to_le_bytes());
    v.extend(3u32.to_le_bytes());
    for (i, left) in [0i32, 1920, 3840].into_iter().enumerate() {
        v.extend(left.to_le_bytes());
        v.extend(0i32.to_le_bytes());
        v.extend((left + 1919).to_le_bytes());
        v.extend(1079i32.to_le_bytes());
        v.extend((if i == 0 { 1u32 } else { 0 }).to_le_bytes());
    }
    v
}

#[test]
fn monitor_data_pdu_bytes_are_exact() {
    let core = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    let (layout, desktop) = monitor_data(&core).unwrap();
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
    // Raw upstream boundary fixture retains the spike's 16x100x100 values.
    // Product config is limited to four monitors and uses validated core geometry.
    let mut layout = ClientMonitorData {
        monitors: (0..16)
            .map(|i| Monitor {
                left: i * 100,
                top: 0,
                right: i * 100 + 99,
                bottom: 99,
                flags: if i == 0 {
                    MonitorFlags::PRIMARY
                } else {
                    MonitorFlags::empty()
                },
            })
            .collect(),
    };
    layout.monitors.push(layout.monitors[0].clone());
    assert!(encode_vec::<ClientMonitorData>(&layout).is_err());
}

fn connector(extended: bool) -> ConnectInitial {
    let core = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    let (cfg, _) = build_connection_config(&core, credentials(), None, &"00".repeat(32))
        .unwrap()
        .into_parts();
    let mut c = ClientConnector::new(cfg, "127.0.0.1:3389".parse().unwrap());
    let mut out = WriteBuf::new();
    c.step(&[], None, &mut out).unwrap();
    assert!(!out.filled().is_empty());
    out.clear();
    let flags = if extended {
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
    c.step_no_input(&mut out).unwrap();
    assert!(
        c.should_perform_credssp(),
        "NLA must be demanded when HYBRID selected"
    );
    c.mark_credssp_as_done();
    out.clear(); // offline state-machine control only
    c.step_no_input(&mut out).unwrap();
    let x224: X224<ironrdp_pdu::x224::X224Data<'_>> = decode(out.filled()).unwrap();
    decode::<ConnectInitial>(x224.0.data.as_ref()).unwrap()
}

#[test]
fn connector_emits_three_monitors_in_gcc_client_blocks() {
    let ci = connector(true);
    let blocks = ci.conference_create_request.gcc_blocks();
    let m = blocks.monitor.as_ref().expect("monitor block present");
    assert_eq!(m.monitors.len(), 3);
    let (want, desktop) =
        monitor_data(&LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap()).unwrap();
    assert_eq!(*m, want);
    assert_eq!(blocks.core.desktop_width, desktop.width);
    assert_eq!(blocks.core.desktop_height, desktop.height);
    assert_eq!(
        encode_vec::<ClientMonitorData>(m).unwrap(),
        expected_monitor_body()
    );
    let early = blocks.core.optional_data.early_capability_flags.unwrap();
    assert!(early.contains(gcc::ClientEarlyCapabilityFlags::SUPPORT_MONITOR_LAYOUT_PDU));
}

#[test]
fn monitor_block_omitted_if_server_lacks_extended_client_data() {
    assert!(connector(false)
        .conference_create_request
        .gcc_blocks()
        .monitor
        .is_none());
}

#[test]
fn builder_requires_nla_and_a_configured_pin() {
    let layout = LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap();
    let config = build_connection_config(&layout, credentials(), None, &"00".repeat(32)).unwrap();
    assert!(config.rdp().enable_credssp);
    assert!(!config.rdp().enable_tls);
    assert!(!config.rdp().enable_standard_rdp_security);
    assert!(build_connection_config(&layout, credentials(), None, "").is_err());
    assert!(build_connection_config(&layout, credentials(), None, "invalid").is_err());
}

#[test]
fn tls_only_server_confirm_is_rejected() {
    let (config, _) = build_connection_config(
        &LayoutBuilder::horizontal_row(3, 1920, 1080).unwrap(),
        credentials(),
        None,
        &"00".repeat(32),
    )
    .unwrap()
    .into_parts();
    let mut connector = ClientConnector::new(config, "127.0.0.1:3389".parse().unwrap());
    let mut out = WriteBuf::new();
    connector.step(&[], None, &mut out).unwrap();
    out.clear();
    let confirm = encode_vec(&X224(ConnectionConfirm::Response {
        flags: ResponseFlags::EXTENDED_CLIENT_DATA_SUPPORTED,
        protocol: SecurityProtocol::SSL,
    }))
    .unwrap();
    assert!(connector.step(&confirm, None, &mut out).is_err());
}

#[test]
fn builder_rejects_more_than_four_odd_width_and_desktop_overflow() {
    for layout in [
        LayoutBuilder::horizontal_row(5, 1920, 1080).unwrap(),
        LayoutBuilder::horizontal_row(3, 1921, 1080).unwrap(),
        DesktopLayout::new(
            vec![
                VirtualMonitor {
                    x: 0,
                    y: 0,
                    width: 1920,
                    height: 1080,
                    is_primary: true,
                },
                VirtualMonitor {
                    x: 68080,
                    y: 0,
                    width: 1920,
                    height: 1080,
                    is_primary: false,
                },
            ],
            70000,
            1080,
        )
        .unwrap(),
    ] {
        assert!(build_connection_config(&layout, credentials(), None, &"00".repeat(32)).is_err());
    }
}
