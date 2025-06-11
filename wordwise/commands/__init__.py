# wordwise/commands/__init__.py
"""Command implementations for WordWise."""

# Import all commands to ensure they're registered
from wordwise.commands.lookup import LookupCommand
from wordwise.commands.save import SaveCommand
from wordwise.commands.view import ViewCommand