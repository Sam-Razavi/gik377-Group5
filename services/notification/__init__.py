import logging

from services.notification.routes import notification_bp

# Konfigurera notification-loggern så att info/warning-meddelanden faktiskt
# syns i terminalen. Vi konfigurerar ENDAST vår egen logger (inte root) så
# att vi inte råkar skriva över en annan apps logg-konfiguration.
_logger = logging.getLogger("notification")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

__all__ = ["notification_bp"]
