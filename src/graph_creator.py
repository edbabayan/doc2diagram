import os
import json
from pathlib import Path
from graphviz import Digraph

from dotenv import load_dotenv


# Set the root directory to the parent of the current file's directory
root = Path(__file__).parent.parent

# Load the environment variables
load_dotenv(dotenv_path=root.joinpath(".env"))

json_path = root / "confluence_page_tree.json"

with open(json_path, "r") as file:
    data = json.load(file)

# Initialize Graphviz Digraph
dot = Digraph(comment="Confluence Page Tree", format='png')
dot.attr(rankdir='TB')  # Top to bottom layout

def add_nodes(node, parent_id=None):
    node_id = node["id"]
    title = node["title"]
    dot.node(node_id, title)

    if parent_id:
        dot.edge(parent_id, node_id)

    for child in node.get("children", []):
        add_nodes(child, node_id)

# Start from root(s)
for page in data:
    add_nodes(page)

# Save and render
output_path = Path("confluence_tree_diagram")
dot.render(output_path, view=True)  # Opens the image after creation
print(f"Diagram saved to: {output_path}.png")