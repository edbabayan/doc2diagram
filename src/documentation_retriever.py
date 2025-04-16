import os
import json
from pathlib import Path
from dotenv import load_dotenv

from atlassian import Confluence
from src.utils import convert_html_to_markdown, extract_attached_filenames, extract_attachments_by_name


# Set the root directory to the parent of the current file's directory
root = Path(__file__).parent.parent

# Load the environment variables
load_dotenv(dotenv_path=root.joinpath(".env"))

# Initialize the ConfluenceLoader with the environment variables
confluence = Confluence(
    url=os.environ["CONFLUENCE_URL"],
    username=os.environ["CONFLUENCE_USERNAME"],
    password=os.environ["CONFLUENCE_API_KEY"],
)

def search_pages(space: str = None, title: str = None, label: str = None, limit: int = None):
    query_parts = ['type = "page"']  # Always include this to exclude images, attachments, etc.

    if title:
        query_parts.append(f'title ~ "{title}"')
    if space:
        query_parts.append(f'space = "{space}"')
    if label:
        query_parts.append(f'label = "{label}"')

    cql_query = " AND ".join(query_parts) if query_parts else "type = page"

    return confluence.cql(cql=cql_query, limit=limit)

def get_desc_page_contents(pages, include_children: bool = True):
    def fetch_page_recursive(page_id):
        full_page = confluence.get_page_by_id(page_id, expand="body.storage")
        title = full_page["title"]
        html_content = full_page["body"]["storage"]["value"]
        markdown_content = convert_html_to_markdown(html_content)
        # Extract images and attachments
        attach_filenames = extract_attached_filenames(html_content)
        # Extract attachments by their names
        attachments = extract_attachments_by_name(confluence, page_id, attach_filenames)

        page_data = {
            "id": page_id,
            "title": title,
            "content": markdown_content,
            "attachments": attachments,
            "children": [],
        }

        if include_children:
            child_pages = confluence.get_child_pages(page_id)
            for child in child_pages:
                child_data = fetch_page_recursive(child["id"])
                page_data["children"].append(child_data)

        return page_data

    contents = []

    for page in pages.get("results", []):
        page_id = page["content"]["id"]
        page_data = fetch_page_recursive(page_id)
        contents.append(page_data)

    return contents

def print_page_tree(pages, indent=0):
    for page in pages:
        print("    " * indent + f"- {page['title']} (ID: {page['id']})")
        if page["children"]:
            print_page_tree(page["children"], indent + 1)


if __name__ == '__main__':
    results = search_pages(space="EPMRPP", title="UX / UI")
    pages_with_content = get_desc_page_contents(results)
    print_page_tree(pages_with_content)

    # Save to JSON
    output_path = root / "confluence_page_tree.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pages_with_content, f, ensure_ascii=False, indent=2)
