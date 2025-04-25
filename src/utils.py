import os
from bs4 import BeautifulSoup
from atlassian import Confluence


def extract_attached_filenames(html_content: str) -> list:
    """
    Extract filenames from <img> and <ri:attachment> tags in the HTML content.

    Args:
        html_content (str): The HTML content from which to extract attachment filenames.

    Returns:
        list: A list of attachment filenames or image sources.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract from <img> tags
    images = [img["src"] for img in soup.find_all("img") if img.has_attr("src")]

    # Extract from <ri:attachment> tags
    attachments = [
        tag["ri:filename"] for tag in soup.find_all("ri:attachment") if tag.has_attr("ri:filename")
    ]

    return images + attachments


def extract_attachments_by_name(client: Confluence, page_id: str, attachment_names: list) -> list:
    """
    Extract download URLs of specific attachments from a Confluence page.

    Args:
        client (Confluence): Atlassian Confluence client.
        page_id (str): ID of the Confluence page.
        attachment_names (list): List of filenames to extract.

    Returns:
        list: Full URLs of the matching attachments.
    """
    # Get all attachments associated with the page
    attachments = client.get_attachments_from_content(page_id, expand="body.storage")

    # Match only attachments with specified filenames
    matching_attachments = [
        attachment for attachment in attachments.get("results", [])
        if attachment["title"] in attachment_names
    ]

    # Build full download URLs
    base_url = os.environ.get("CONFLUENCE_URL", "").rstrip("/")
    full_urls = [
        f"{base_url}{attachment['_links']['download']}"
        for attachment in matching_attachments
    ]

    return full_urls


def clean_header_tags(html: str) -> str:
    """
    Clean header tags (<h1> to <h4>) by removing line breaks and empty headings.
    Converts headers with only media to paragraphs, and removes empty ones.

    Args:
        html (str): HTML content to clean.

    Returns:
        str: Cleaned HTML content.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag_name in ["h1", "h2", "h3", "h4"]:
        for tag in soup.find_all(tag_name):
            # Remove <br> tags inside headers
            for br in tag.find_all("br"):
                br.extract()

            cleaned_text = tag.get_text(strip=True)

            # Handle empty headers or media-only headers
            if not cleaned_text:
                if tag.find(["ac:image", "img", "ri:attachment"]):
                    tag.name = "p"  # Convert to paragraph
                else:
                    tag.decompose()  # Remove empty tag
            else:
                tag.string = cleaned_text  # Replace content with stripped text

    return str(soup)
