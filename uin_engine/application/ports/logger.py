from abc import ABC, abstractmethod

class ILogger(ABC):
    """Abstract interface for a logger."""

    @abstractmethod
    def debug(self, message: str):
        """Logs a debug message."""
        pass

    @abstractmethod
    def info(self, message: str):
        """Logs an info message."""
        pass

    @abstractmethod
    def warning(self, message: str):
        """Logs a warning message."""
        pass

    @abstractmethod
    def error(self, message: str):
        """Logs an error message."""
        pass
