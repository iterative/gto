from typing import Optional


def generate_annotate_commit_message(
    name: str, type: Optional[str] = None, path: Optional[str] = None
) -> str:
    return (
        f"Annotate artifact `{name}`"
        f"{f' of type `{type}`' if type is not None else ''}"
        f"{f' with path `{path}`' if path is not None else ''}"
    )


def generate_remove_commit_message(name: str) -> str:
    return f"Remove annotation for artifact `{name}`"


def generate_empty_commit_message() -> str:
    return ""
