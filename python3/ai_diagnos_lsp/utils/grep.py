from typing import Union, List, Tuple
import re
import logging
import os
import html

def grep(pattern: str, lines: Union[str, List[str]], ignore_case: bool = False) -> List[Tuple[int, int]]:
    try:
        """
        Search for a pattern and return (line_number, character_position) for each match.
        
        Args:
            pattern: The pattern to search for
            lines: List of strings or a multi-line string
            ignore_case: Case-insensitive matching
        
        Returns:
            List of (line_number, character_position) tuples
        """
        # Convert string to list if needed
        if isinstance(lines, str):
            lines = lines.splitlines()

        pattern = html.unescape(pattern)
        
        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(re.escape(pattern), flags)
        
        matches = []
        
        for line_num, line in enumerate(lines, start=1):
            try:
                for match in regex.finditer(line):
                    matches.append((line_num, match.start()))
            except Exception as e:
                if os.getenv("AI_DIAGNOS_LOG") is not None:
                    logging.error(f"regex inside grep errored out for the following reason : {e}")
        
        return matches
    except Exception as e:
        if os.getenv("AI_DIAGNOS_LOG") is not None:
            logging.error(f"The whole grep function errored out for the following reason : {e}")
        raise RuntimeError(f"Grep quit for the following reason : {e}") from e
