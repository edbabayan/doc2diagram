import os
import json
from dotenv import load_dotenv

from atlassian import Confluence

from src.config import CFG
from src.chunker import hierarchical_title_chunking, html_chunking
from src.utils import (convert_html_to_markdown_with_attachments, extract_attached_filenames,
                       extract_attachments_by_name, clean_header_tags)


# Load the environment variables
load_dotenv(dotenv_path=CFG.root.joinpath(".env"))

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

        # Extract images and attachments
        attach_filenames = extract_attached_filenames(html_content)

        # Extract attachments by their names
        attachments = extract_attachments_by_name(confluence, page_id, attach_filenames)

        # Replace attachment references in the HTML content with their URLs
        for filename, url in zip(attach_filenames, attachments):
            html_content = html_content.replace(filename, url)

        cleaned_html = clean_header_tags(html_content)

        # markdown_content = convert_html_to_markdown_with_attachments(html_content)

        # chunks = hierarchical_title_chunking(markdown_content)
        chunks = html_chunking(cleaned_html, CFG.HEADERS_TO_SPLIT_ON)

        page_data = {
            "id": page_id,
            "title": title,
            "content": chunks,
            "child_pages": [],
        }

        if include_children:
            child_pages = confluence.get_child_pages(page_id)
            for child in child_pages:
                child_data = fetch_page_recursive(child["id"])
                page_data["child_pages"].append(child_data)

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
        if page["child_pages"]:
            print_page_tree(page["child_pages"], indent + 1)


if __name__ == '__main__':
    results = search_pages(space="EPMRPP", title="UX / UI")
    pages_with_content = get_desc_page_contents(results)
    print_page_tree(pages_with_content)

    # Save to JSON
    output_path = CFG.root / "confluence_page_tree.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pages_with_content, f, ensure_ascii=False, indent=2)
