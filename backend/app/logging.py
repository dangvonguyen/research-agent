import json
import logging
import logging.config
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def sanitize_mongodb_uri(uri: str, mask: str = "***") -> str:
    """
    Sanitize MongoDB URI by masking credentials.
    """
    parsed_uri = urlparse(uri)

    if not parsed_uri.username and not parsed_uri.password:
        return str(uri)

    masked_netloc = f"{mask}:{mask}@{parsed_uri.hostname}:{parsed_uri.port}"
    masked_parsed = parsed_uri._replace(netloc=masked_netloc)
    return urlunparse(masked_parsed)


def setup_logging() -> None:
    """
    Setup application logging from configuration.
    """
    # Create logs directory
    log_dir = Path("logs")
    try:
        log_dir.mkdir(exist_ok=True)

    except PermissionError:
        print("ERROR: Permission denied when creating logs directory")
        sys.exit(1)

    except Exception as e:
        print(f"ERROR: Failed to create logs directory: {e}")
        sys.exit(1)

    # Load configuration from file
    config_path = Path(__file__).parent / "logging_config.json"

    if config_path.exists():
        try:
            with config_path.open() as f:
                config = json.load(f)

            logging.config.dictConfig(config)

            app_logger = logging.getLogger("app")
            app_logger.info(
                "Logging system initialized successfully from %s", config_path
            )

        except json.JSONDecodeError as e:
            app_logger = _setup_fallback_logging()
            app_logger.error("Invalid JSON in logging configuration: %s", str(e))

        except Exception as e:
            app_logger = _setup_fallback_logging()
            app_logger.error("Failed to configure logging from file: %s", str(e))
    else:
        app_logger = _setup_fallback_logging()
        app_logger.warning(
            "Logging configuration file not found at %s, using default configuration",
            config_path,
        )


def _setup_fallback_logging() -> logging.Logger:
    """
    Set up a basic fallback logger when the configuration file is unavailable.
    """
    app_logger = logging.getLogger("app")

    # Clear any existing handlers
    for handler in app_logger.handlers[:]:
        app_logger.removeHandler(handler)

    # Add console handler with formatting
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    return app_logger
