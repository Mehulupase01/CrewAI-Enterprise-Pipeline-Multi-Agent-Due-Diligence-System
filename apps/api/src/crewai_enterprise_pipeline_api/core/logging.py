import logging


def configure_logging(environment: str) -> None:
    if environment == "development":
        level = logging.DEBUG
    elif environment == "test":
        level = logging.WARNING
    else:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
