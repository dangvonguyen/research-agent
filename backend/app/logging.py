import json
import logging
import logging.config
from pathlib import Path


def setup_logging() -> None:
    """
    Setup application logging from configuration.
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Load configuration from file
    config_path = Path(__file__).parent / "logging_config.json"

    if config_path.exists():
        with config_path.open() as f:
            config = json.load(f)

        logging.config.dictConfig(config)

        app_logger = logging.getLogger("app")
        app_logger.info("Logging configured successfully")
    else:
        app_logger = logging.getLogger("app")
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        app_logger.addHandler(handler)
        app_logger.setLevel(logging.INFO)
        app_logger.propagate = False
        app_logger.warning("Logging configuration file not found at %s", config_path)
