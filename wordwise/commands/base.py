from abc import ABC, abstractmethod
import argparse


class Command(ABC):
    """Base abstract class for all WordWise commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the command name used in the CLI."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Returns the command description for help text."""
        pass

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command-specific arguments to the parser.

        Args:
            parser: ArgumentParser instance for this command
        """
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the command logic.

        Args:
            args: Parsed command arguments

        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        pass