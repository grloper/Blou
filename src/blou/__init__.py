"""
Blou — Android RDP client with virtual multi-monitor.
Core algorithmic, layout, security, and protocol engines.
"""

from .layout import (
    DesktopLayout,
    VirtualMonitor,
    LayoutBuilder,
    MonitorArrangement
)
from .viewport import (
    CoordinateMapper,
    ViewportDimensions,
    Rect,
    SwipeNavigationController
)
from .security import (
    CertificatePinningVerifier,
    CertificateVerificationResult,
    HardwareKeystorePolicy
)
from .dvc import (
    DisplayControlEncoder,
    DISPLAYCONTROL_MONITOR_PRIMARY,
    DISPLAYCONTROL_PDU_TYPE_LAYOUT
)

__all__ = [
    "DesktopLayout",
    "VirtualMonitor",
    "LayoutBuilder",
    "MonitorArrangement",
    "CoordinateMapper",
    "ViewportDimensions",
    "Rect",
    "SwipeNavigationController",
    "CertificatePinningVerifier",
    "CertificateVerificationResult",
    "HardwareKeystorePolicy",
    "DisplayControlEncoder",
    "DISPLAYCONTROL_MONITOR_PRIMARY",
    "DISPLAYCONTROL_PDU_TYPE_LAYOUT",
]
