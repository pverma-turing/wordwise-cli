# wordwise/commands/__init__.py
"""Command implementations for WordWise."""

# Import all commands to ensure they're registered
from wordwise.commands.lookup import LookupCommand
from wordwise.commands.save import SaveCommand
from wordwise.commands.view import ViewCommand
from wordwise.commands.edit import EditCommand
from wordwise.commands.export import ExportCommand
from wordwise.commands.review import ReviewCommand
from wordwise.commands.delete import DeleteCommand
from wordwise.commands.set_goal import SetGoalCommand