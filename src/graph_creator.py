import json
from graphviz import Digraph
from collections import defaultdict
from src.config import CFG

# Load the JSON data
with open(CFG.tree_file_path, "r") as file:
    data = json.load(file)

# Initialize Graphviz Digraph
dot = Digraph(comment="Confluence Page Tree", format='png')
dot.attr(rankdir='TB', dpi='300', nodesep='0.5', ranksep='0.7', splines='ortho')

# Node level colors
level_colors = {
    0: '#4285F4',  # Root page
    1: '#34A853',  # Subsection
    2: '#FBBC05',  # Topic
    3: '#EA4335',  # Deep level content
}

def truncate_text(text, max_length=30):
    return (text[:max_length] + '...') if text and len(text) > max_length else (text or "Untitled")

def add_node(node_id, label, level, shape='box', tooltip=""):
    color = level_colors.get(min(level, 3), "#999999")
    dot.node(node_id,
             label=truncate_text(label),
             shape=shape,
             style='filled,rounded' if shape == 'box' else 'filled',
             fillcolor=color,
             fontcolor='white',
             tooltip=label or tooltip)

def process_page(page, parent_id=None, level=0):
    page_id = str(page["id"])
    title = page.get("title", "Untitled")
    add_node(page_id, title, level=0)

    if parent_id:
        dot.edge(parent_id, page_id, label="child page", fontsize="10")

    # Organize content into subsections and topics
    if "content" in page and page["content"]:
        subsections = defaultdict(lambda: defaultdict(list))  # {Subsection: {Topic: [content]}}

        for item in page["content"]:
            hierarchy = item.get("hierarchy", {})
            subsection = hierarchy.get("Subsection") or hierarchy.get("Section", "")
            topic = hierarchy.get("Topic", "")
            subsections[subsection][topic].append(item)

        for i, (subsection_name, topics) in enumerate(subsections.items()):
            if not subsection_name:
                continue
            subsection_id = f"{page_id}_sub_{i}"
            add_node(subsection_id, subsection_name, level=1, shape='note', tooltip=f"Subsection: {subsection_name}")
            dot.edge(page_id, subsection_id, label="contains", fontsize="10", style="dashed")

            for j, (topic_name, content_items) in enumerate(topics.items()):
                if not topic_name:
                    continue
                topic_id = f"{subsection_id}_topic_{j}"
                add_node(topic_id, topic_name, level=2, shape='note', tooltip=f"Topic: {topic_name}")
                dot.edge(subsection_id, topic_id, label="contains", fontsize="10", style="dotted")

    # Recurse into child pages
    for child in page.get("child_pages", []):
        process_page(child, parent_id=page_id, level=level+1)

# Render each root page
for page in data:
    process_page(page)

# Save diagram
dot.render(CFG.diagram_path, view=False, cleanup=True)
print(f"Diagram saved to: {CFG.diagram_path}.png")
