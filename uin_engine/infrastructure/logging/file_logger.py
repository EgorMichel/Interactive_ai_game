import logging
from uin_engine.application.ports.logger import ILogger

class FileLogger(ILogger):
    """A concrete implementation of ILogger that writes to a file."""

    def __init__(self, log_file: str = "game.log", level: int = logging.DEBUG):
        # Configure the logger
        self.logger = logging.getLogger("UIN_Engine_Logger")
        self.logger.setLevel(level)

        # Avoid adding duplicate handlers if this class is instantiated multiple times
        if not self.logger.handlers:
            # Create a file handler
            handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            handler.setLevel(level)

            # Create a formatter and add it to the handler
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)

            # Add the handler to the logger
            self.logger.addHandler(handler)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)
