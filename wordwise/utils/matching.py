# wordwise/utils/matching.py
"""Utilities for word matching and suggestions."""


def levenshtein_distance(s1, s2):
    """
    Calculate the Levenshtein distance between two strings.

    Args:
        s1 (str): First string
        s2 (str): Second string

    Returns:
        int: The Levenshtein distance between s1 and s2
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    # If second string is empty, the distance is just the length of the first
    if len(s2) == 0:
        return len(s1)

    # Initialize previous row of distances
    previous_row = range(len(s2) + 1)

    for i, c1 in enumerate(s1):
        # Current row starts with the column number
        current_row = [i + 1]

        for j, c2 in enumerate(s2):
            # Calculate insertions, deletions and substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)

            # Get the minimum to determine the optimal path
            current_row.append(min(insertions, deletions, substitutions))

        # Update previous row to current row
        previous_row = current_row

    return previous_row[-1]


def find_similar_words(query, word_list, max_distance=2):
    """
    Find words similar to the query in the provided word list.

    Args:
        query (str): The query word
        word_list (list): List of candidate words
        max_distance (int): Maximum Levenshtein distance to consider

    Returns:
        list: List of similar words sorted by similarity
    """
    query = query.lower()
    similarities = []

    for word in word_list:
        word_lower = word.lower()
        distance = levenshtein_distance(query, word_lower)

        if distance <= max_distance:
            similarities.append((word, distance))

    # Sort by distance (closest first)
    return [word for word, distance in sorted(similarities, key=lambda x: x[1])]