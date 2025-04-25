import json
from graphviz import Digraph
from collections import defaultdict

from src.config import CFG


# Read the JSON data
with open(CFG.tree_file_path, "r") as file:
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
    1: '#34A853',  # Green for content sections/subsections
    2: '#FBBC05',  # Yellow for topics
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


def add_content_node(node_id, title, level=1, tooltip=""):
    """Add a content node with specific styling."""
    color = level_colors[min(level, 3)]
    label = truncate_text(title)

    if not title:
        label = "Untitled Content"

    dot.node(node_id,
             label=label,
             shape='note',
             style='filled',
             fillcolor=color,
             fontcolor='white',
             tooltip=tooltip)


def process_page(page, parent_id=None, level=0):
    """Process a page and its subsections/topics."""
    page_id = str(page["id"])
    title = page["title"]

    # Add the page node
    add_page_node(page_id, title, level)

    # Connect to parent if exists
    if parent_id:
        dot.edge(parent_id, page_id, label="child page", fontsize="10")

    # Process content with hierarchy if any
    if "content" in page and page["content"]:
        # Group content by subsection
        subsections = defaultdict(list)
        for content_item in page["content"]:
            metadata = content_item.get("metadata", {})
            subsection = metadata.get("Subsection", "")
            topic = metadata.get("Topic", "")

            # Add content item to its subsection group
            subsections[subsection].append((topic, content_item))

        # Process each subsection and its topics
        for i, (subsection_name, topics_list) in enumerate(subsections.items()):
            if not subsection_name:  # Skip items without subsection
                continue

            # Create subsection node
            subsection_id = f"{page_id}_subsection_{i}"
            add_content_node(subsection_id, subsection_name, level=1, tooltip=f"Subsection: {subsection_name}")

            # Connect page to subsection
            dot.edge(page_id, subsection_id, label="contains", fontsize="10", style="dashed")

            # Process topics under this subsection
            topic_dict = defaultdict(list)
            for topic_name, content_item in topics_list:
                topic_dict[topic_name].append(content_item)

            # Create topic nodes under the subsection
            for j, (topic_name, content_items) in enumerate(topic_dict.items()):
                if not topic_name:  # Skip items without topic
                    continue

                # Create topic node
                topic_id = f"{subsection_id}_topic_{j}"
                add_content_node(topic_id, topic_name, level=2, tooltip=f"Topic: {topic_name}")

                # Connect subsection to topic
                dot.edge(subsection_id, topic_id, label="contains", fontsize="10", style="dotted")

    # Process child pages recursively
    if "child_pages" in page and page["child_pages"]:
        for child_page in page["child_pages"]:
            process_page(child_page, page_id, level)


# Start processing from root pages
for page in data:
    process_page(page)

# Use a hierarchical layout
dot.attr('graph', splines='ortho')  # Use orthogonal splines for cleaner layout

# Save and render
dot.render(CFG.diagram_path, view=False, cleanup=True)
print(f"Diagram saved to: {CFG.diagram_path}.png")