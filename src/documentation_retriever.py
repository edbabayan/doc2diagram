import os
from pathlib import Path
from dotenv import load_dotenv

from atlassian import Confluence

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

def get_page_contents(pages, include_children: bool = True):
    contents = []

    for page in pages.get("results", []):
        page_id = page["content"]["id"]
        title = page["content"]["title"]

        # Get full content
        full_page = confluence.get_page_by_id(page_id, expand="body.storage")
        html_content = full_page["body"]["storage"]["value"]

        page_data = {
            "id": page_id,
            "title": title,
            "content": html_content,
            "children": []
        }

        contents.append(page_data)

        if include_children:
            child_pages = confluence.get_child_pages(page_id)
            for child in child_pages:
                child_id = child["id"]
                child_title = child["title"]
                child_full = confluence.get_page_by_id(child_id, expand="body.storage")
                child_content = child_full["body"]["storage"]["value"]

                page_data["children"].append({
                    "id": child_id,
                    "title": child_title,
                    "content": child_content
                })

        contents.append(page_data)

    return contents


if __name__ == '__main__':
    results = search_pages(space="EPMRPP", title="ReportPortal Contributors")
    pages_with_content = get_page_contents(results)

    print('')