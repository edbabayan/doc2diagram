import os
import html2text
from bs4 import BeautifulSoup
from atlassian import Confluence


def extract_attached_filenames(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # Extract images from <img> tags
    images = [img["src"] for img in soup.find_all("img") if "src" in img.attrs]
    # Extract images from <ri:attachment> tags
    attachments = [attachment["ri:filename"] for attachment in soup.find_all("ri:attachment") if "ri:filename" in attachment.attrs]
    return images + attachments


def convert_html_to_markdown(html_content: str) -> str:
    """
    Converts HTML content to Markdown format.

    Args:
        html_content (str): The HTML content to be converted.

    Returns:
        str: The converted Markdown content.
    """
    # Create an instance of the html2text.HTML2Text class
    h = html2text.HTML2Text()

    # Disable wrapping of lines to make it more readable
    h.body_width = 0

    # Convert the HTML to Markdown
    markdown_content = h.handle(html_content)

    return markdown_content

def extract_attachments_by_name(client, page_id, attachment_names):
    """
    Extract attachments from a Confluence page by their names.
    Args:
        client (Confluence): The Confluence client instance.
        page_id (str): The ID of the Confluence page.
        attachment_names (list): List of attachment filenames to extract.
    Returns:
        list: List of matching attachment URLs.
    """
    # Fetch all attachments for the page
    attachments = client.get_attachments_from_content(page_id, expand="body.storage")
    # Filter attachments by their filenames
    matching_attachments = [attachment for attachment in attachments["results"]
        if attachment["title"] in attachment_names
    ]
    # Extract the download links for the matching attachments
    attachment_urls = [
        attachment["_links"]["download"] for attachment in matching_attachments
    ]
    # Prepend the base URL to the download links
    base_url = os.environ["CONFLUENCE_URL"]
    full_urls = [f"{base_url}{url}" for url in attachment_urls]
    return full_urls