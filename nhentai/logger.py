import logging

from rich.console import Console
from rich.logging import RichHandler


console = Console()

logging.addLevelName(16, "SUCCESS")
logger = logging.getLogger("nhentai")
LOGGER_HANDLER = RichHandler(console=console, markup=True, rich_tracebacks=True)
FORMATTER = logging.Formatter("%(message)s")
LOGGER_HANDLER.setFormatter(FORMATTER)
logger.addHandler(LOGGER_HANDLER)
logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    logger.log(16, "nhentai")
    logger.info("info")
    logger.warning("warning")
    logger.debug("debug")
    logger.error("error")
    logger.critical("critical")
