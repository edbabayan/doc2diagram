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

def get_page_contents(pages):
    contents = []

    for page in pages.get("results", []):
        page_id = page["content"]["id"]
        title = page["content"]["title"]

        # Get full content (e.g. body.storage gives HTML content)
        full_page = confluence.get_page_by_id(
            page_id,
            expand="body.storage"
        )

        html_content = full_page["body"]["storage"]["value"]
        contents.append({"id": page_id, "title": title, "content": html_content})

    return contents

if __name__ == '__main__':
    results = search_pages(space="EPMRPP", title="ReportPortal Contributors")
    pages_with_content = get_page_contents(results)

    print('')