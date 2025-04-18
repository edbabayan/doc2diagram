import json
from pathlib import Path
from graphviz import Digraph

# Set the root directory to the parent of the current file's directory
root = Path(__file__).parent.parent

# Define the path to your JSON file
json_path = root / "confluence_page_tree.json"

# Read the JSON data
with open(json_path, "r") as file:
    data = json.load(file)

# Initialize Graphviz Digraph
dot = Digraph(comment="Confluence Page Tree with Content Titles", format='png')
dot.attr(rankdir='TB')  # Top to bottom layout
dot.attr(dpi='300')  # Set higher resolution
dot.graph_attr['nodesep'] = '0.5'
dot.graph_attr['ranksep'] = '0.7'

# Define colors for different levels
level_colors = {
    0: '#4285F4',  # Blue for pages
    1: '#34A853',  # Green for content sections
    2: '#FBBC05',  # Yellow for sub-sections
    3: '#EA4335'  # Red for deeper content
}


def truncate_text(text, max_length=30):
    """Truncate text for display in nodes."""
    if not text:
        return "Untitled"
    return (text[:max_length] + '...') if len(text) > max_length else text


def add_page_node(node_id, title, level=0):
    """Add a page node with specific styling."""
    color = level_colors[min(level, 3)]
    dot.node(node_id,
             label=truncate_text(title),
             shape='box',
             style='filled,rounded',
             fillcolor=color,
             fontcolor='white',
             tooltip=title)


def add_content_node(node_id, title, content_index, level=1):
    """Add a content node with specific styling."""
    color = level_colors[min(level, 3)]
    label = truncate_text(title)
    if not title:
        label = f"Content {content_index + 1}"

    dot.node(node_id,
             label=label,
             shape='note',
             style='filled',
             fillcolor=color,
             fontcolor='white',
             tooltip=title)


def process_page(page, parent_id=None, level=0):
    """Process a page and its content."""
    page_id = page["id"]
    title = page["title"]

    # Add the page node
    add_page_node(page_id, title, level)

    # Connect to parent if exists
    if parent_id:
        dot.edge(parent_id, page_id, label="child page", fontsize="10")

    # Process content if any
    if "content" in page and page["content"]:
        for i, content_item in enumerate(page["content"]):
            content_id = f"{page_id}_content_{i}"
            content_title = content_item.get("title", "")

            # Add content node
            add_content_node(content_id, content_title, i, level + 1)

            # Connect page to content
            dot.edge(page_id, content_id, label="contains", fontsize="10", style="dashed")

            # Process child chunks recursively
            if "child_chunks" in content_item and content_item["child_chunks"]:
                process_child_chunks(content_item["child_chunks"], content_id, level + 2)

    # Process child pages recursively
    if "child_pages" in page and page["child_pages"]:
        for child_page in page["child_pages"]:
            process_page(child_page, page_id, level)


def process_child_chunks(chunks, parent_id, level=2):
    """Process child chunks of content."""
    for i, chunk in enumerate(chunks):
        chunk_id = f"{parent_id}_chunk_{i}"
        chunk_title = chunk.get("title", "")

        # Skip chunks with no title
        if not chunk_title:
            continue

        # Add chunk node
        add_content_node(chunk_id, chunk_title, i, level)

        # Connect parent to chunk
        dot.edge(parent_id, chunk_id, label="sub-section", fontsize="8", style="dotted")

        # Process deeper chunks recursively
        if "child_chunks" in chunk and chunk["child_chunks"]:
            process_child_chunks(chunk["child_chunks"], chunk_id, level + 1)


# Start processing from root pages
for page in data:
    process_page(page)

# Use a hierarchical layout
dot.attr('graph', splines='ortho')  # Use orthogonal splines for cleaner layout

# Save and render
output_path = Path("confluence_title_hierarchy_diagram")
dot.render(output_path, view=True)
print(f"Diagram saved to: {output_path}.png")

