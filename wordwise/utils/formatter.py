# wordwise/utils/formatter.py
"""Output formatting utilities for WordWise."""

def format_section(title, content):
    """
    Format a section with title and content for display.
    
    Args:
        title: Section title
        content: Content string or list of strings
        
    Returns:
        Formatted section string
    """
    formatted = f"\n{title.upper()}\n"
    formatted += "=" * len(title) + "\n"
    
    if isinstance(content, list):
        for item in content:
            formatted += f"• {item}\n"
    else:
        formatted += f"{content}\n"
    
    return formatted

def format_dictionary_entry(word, entry, show_examples=False, show_synonyms=False):
    """
    Format a dictionary entry for display.
    
    Args:
        word: The word being defined
        entry: Dictionary with definition, synonyms, and examples
        show_examples: Whether to include examples in the output
        show_synonyms: Whether to include synonyms in the output
        
    Returns:
        Formatted entry string
    """
    result = f"\n{word.upper()}\n"
    result += "=" * len(word) + "\n"
    
    if "definition" in entry:
        result += format_section("Definition", entry["definition"])
    
    # Only include synonyms when show_synonyms is True
    if show_synonyms and "synonyms" in entry and entry["synonyms"]:
        result += format_section("Synonyms", entry["synonyms"])
    
    # Only include examples when show_examples is True
    if show_examples and "examples" in entry and entry["examples"]:
        result += format_section("Examples", entry["examples"])
    
    return result