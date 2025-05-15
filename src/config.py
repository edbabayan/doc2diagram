from pathlib import Path


class CFG:
    root = Path(__file__).parent.parent
    data_dir = root / "data"
    source_dir = root / "src"

    attachments_dir = data_dir / "attachments"
    metadata_extractor_dir = source_dir / "meta_miner"

    llm_cache_path = metadata_extractor_dir / "metadata_cache"

    env_variable_file = root / ".env"
    tree_file_path = data_dir / "confluence_page_tree.json"
    diagram_path = data_dir / "confluence_page_tree_diagram"

    HEADERS_TO_SPLIT_ON = [
        ("h1", "Section"),
        ("h2", "Subsection"),
        ("h3", "Topic"),
    ]

    opeanai_embed_dim = 3072
    embed_model = "text-embedding-3-large"
    local_llm_model = 'qwen3:8b'