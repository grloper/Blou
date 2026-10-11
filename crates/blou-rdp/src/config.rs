//! Build NLA-only engine settings from validated geometry and an out-of-band certificate pin.
//! TLS-only fallback and standard RDP security stay disabled. This does not connect a host.
use blou_core::{
    dvc::validate_display_layout, layout::DesktopLayout, pin::CertificatePinningVerifier, CoreError,
};
use ironrdp_connector::{Config, Credentials, DesktopSize};
use ironrdp_pdu::{
    gcc::{self, ClientMonitorData, Monitor, MonitorFlags},
    rdp::capability_sets::{MajorPlatformType, RailSupportLevel},
};

/// Keep the validated engine and TLS configurations together until the transport consumes them.
/// No Debug implementation: engine credentials must not enter logs.
pub struct ConnectionConfig {
    rdp: Config,
    tls: rustls::ClientConfig,
}
impl ConnectionConfig {
    pub fn rdp(&self) -> &Config {
        &self.rdp
    }
    pub fn into_parts(self) -> (Config, rustls::ClientConfig) {
        (self.rdp, self.tls)
    }
}

pub fn monitor_data(layout: &DesktopLayout) -> Result<(ClientMonitorData, DesktopSize), CoreError> {
    validate_display_layout(layout)?;
    let desktop = DesktopSize {
        width: u16::try_from(layout.bounding_width())
            .map_err(|_| CoreError("Desktop width exceeds unsigned 16-bit range"))?,
        height: u16::try_from(layout.bounding_height())
            .map_err(|_| CoreError("Desktop height exceeds unsigned 16-bit range"))?,
    };
    let monitors = layout
        .monitors()
        .iter()
        .map(|m| {
            Ok(Monitor {
                left: m.x,
                top: m.y,
                right: i32::try_from(m.right())
                    .map_err(|_| CoreError("Monitor right exceeds signed 32-bit range"))?,
                bottom: i32::try_from(m.bottom())
                    .map_err(|_| CoreError("Monitor bottom exceeds signed 32-bit range"))?,
                flags: if m.is_primary {
                    MonitorFlags::PRIMARY
                } else {
                    MonitorFlags::empty()
                },
            })
        })
        .collect::<Result<Vec<_>, CoreError>>()?;
    Ok((ClientMonitorData { monitors }, desktop))
}

pub fn build_connection_config(
    layout: &DesktopLayout,
    credentials: Credentials,
    domain: Option<String>,
    fingerprint: &str,
) -> Result<ConnectionConfig, Box<dyn std::error::Error + Send + Sync>> {
    if fingerprint.is_empty() {
        return Err(CoreError("A certificate pin is required before connecting").into());
    }
    let pin = CertificatePinningVerifier::new(Some(fingerprint))?;
    let tls = crate::tls::pinned_client_config(pin)?;
    let (monitor_layout, desktop_size) = monitor_data(layout)?;
    // Defaults reuse the successful spike at the same unmodified engine revision.
    let rdp = Config {
        desktop_size,
        monitor_layout: Some(monitor_layout),
        desktop_scale_factor: 0,
        enable_tls: false, // disables TLS-only fallback; NLA still includes TLS
        enable_credssp: true,
        enable_standard_rdp_security: false,
        credentials,
        domain,
        client_build: 0,
        client_name: "blou".into(),
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
    };
    Ok(ConnectionConfig { rdp, tls })
}
