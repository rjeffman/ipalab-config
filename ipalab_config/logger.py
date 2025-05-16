"""Provide logging facilities."""

import logging


logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
logging.addLevelName(logging.CRITICAL, "FATAL")
logger = logging.getLogger("ipalab-config")
