from pathlib import Path

class CFG:
    root = Path(__file__).parent.parent

    HEADERS_TO_SPLIT_ON = [
        ("h1", "Section"),
        ("h2", "Subsection"),
        ("h3", "Topic"),
        ("h4", "Sub‑topic"),
    ]