# wordwise/config.py
"""Command registry and application configuration for WordWise."""

from wordwise.registry import COMMANDS
# Import all command modules to trigger decorator registration
from wordwise.commands import LookupCommand, ViewCommand, \
    SaveCommand, EditCommand, ExportCommand, ReviewCommand, \
    DeleteCommand, SetGoalCommand
# add future commands herea

AVAILABLE_COMMANDS = COMMANDS
