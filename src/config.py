from pathlib import Path


class CFG:
    root = Path(__file__).parent.parent
    source_dir = root / "src"
    metadata_extractor_dir = source_dir / "meta_miner"

    llm_cache_path = metadata_extractor_dir / "metadata_cache"

    env_variable_file = root / ".env"
    tree_file_path = root / "confluence_page_tree.json"
    diagram_path = root / "confluence_page_tree_diagram"

    HEADERS_TO_SPLIT_ON = [
        ("h1", "Section"),
        ("h2", "Subsection"),
        ("h3", "Topic"),
        ("h4", "Sub‑topic"),
    ]
