import textwrap
from typing import Any, Dict, Set

__all__ = ['make_replacements', 'get_all_subclasses']


def make_replacements(original: str, replacements: Dict[str, Any]) -> str:
    for pattern, repl in replacements.items():
        indent = -1
        for line in original.splitlines():
            indent = line.find(pattern)
            if indent > -1:
                break
        indent = max(0, indent)
        replacement = textwrap.dedent(str(repl))
        if replacement:
            replacement_lines = [line for line in replacement.splitlines() if line.strip()]
            replacement = replacement_lines[0]
            if len(replacement_lines) > 1:
                replacement += '\n' + textwrap.indent('\n'.join(replacement_lines[1:]), ' ' * indent)
        original = original.replace(pattern, replacement)
    return original


def get_all_subclasses(cls: type) -> Set[type]:
    all_subclasses = set()
    for subclass in cls.__subclasses__():
        all_subclasses.add(subclass)
        all_subclasses.update(get_all_subclasses(subclass))
    return all_subclasses
