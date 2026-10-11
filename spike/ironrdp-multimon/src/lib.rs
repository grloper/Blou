//! Spike: declare a client-fabricated multi-monitor layout through IronRDP and
//! inspect the exact bytes the connector emits. Offline only; no server involved.
//!
//! The fabricated layout is the Blou "layout lie": N monitors of `w`x`h` placed
//! side by side, primary at (0,0), so the virtual desktop is `N*w` x `h`.
//! Coordinates follow MS-RDPBCGR 2.2.1.3.6.1 (TS_MONITOR_DEF: inclusive right/bottom).

use ironrdp_connector::{Config, Credentials, DesktopSize};
use ironrdp_pdu::gcc::{self, ClientMonitorData, Monitor, MonitorFlags};
use ironrdp_pdu::rdp::capability_sets::{MajorPlatformType, RailSupportLevel};

/// Side-by-side layout: monitor i occupies x in [i*w, i*w + w - 1].
pub fn fabricated_row(count: u16, w: u16, h: u16) -> (ClientMonitorData, DesktopSize) {
    assert!((1..=16).contains(&count), "MS-RDPBCGR: 1..=16 monitors");
    let monitors = (0..count)
        .map(|i| {
            let left = i32::from(i) * i32::from(w);
            Monitor {
                left,
                top: 0,
                right: left + i32::from(w) - 1,
                bottom: i32::from(h) - 1,
                flags: if i == 0 {
                    MonitorFlags::PRIMARY
                } else {
                    MonitorFlags::empty()
                },
            }
        })
        .collect();
    (
        ClientMonitorData { monitors },
        DesktopSize {
            width: count * w,
            height: h,
        },
    )
}

/// NLA (CredSSP/HYBRID) only, no TLS-only fallback, with the fabricated layout declared.
pub fn spike_config(layout: ClientMonitorData, desktop: DesktopSize) -> Config {
    Config {
        desktop_size: desktop,
        monitor_layout: Some(layout),
        desktop_scale_factor: 0,
        enable_tls: false,
        enable_credssp: true,
        enable_standard_rdp_security: false,
        credentials: Credentials::UsernamePassword {
            username: "spike".into(),
            password: "spike".into(),
        },
        domain: None,
        client_build: 0,
        client_name: "blou-spike".into(),
        keyboard_type: gcc::KeyboardType::IBM_ENHANCED,
        keyboard_subtype: 0,
        keyboard_functional_keys_count: 12,
        keyboard_layout: 0,
        connection_type: gcc::ConnectionType::Lan,
        ime_file_name: String::new(),
        bitmap: None,
        dig_product_id: String::new(),
        client_dir: String::new(),
        alternate_shell: String::new(),
        work_dir: String::new(),
        remote_application_mode: false,
        rail_support_level: RailSupportLevel::empty(),
        platform: MajorPlatformType::ANDROID,
        hardware_id: None,
        request_data: None,
        autologon: false,
        enable_audio_playback: false,
        enable_audio_capture: false,
        performance_flags: Default::default(),
        license_cache: None,
        timezone_info: Default::default(),
        compression_type: None,
        enable_server_pointer: false,
        pointer_software_rendering: false,
        multitransport_flags: None,
        support_dyn_vc_gfx_protocol: false,
    }
}
