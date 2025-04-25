import os

from loguru import logger
from bs4 import BeautifulSoup
from atlassian import Confluence


def extract_attached_filenames(html_content: str) -> list:
    """
    Extract filenames from <img> and <ri:attachment> tags in the HTML content.
    """
    logger.info("Extracting filenames from HTML content...")

    soup = BeautifulSoup(html_content, "html.parser")

    images = [img["src"] for img in soup.find_all("img") if img.has_attr("src")]
    attachments = [
        tag["ri:filename"] for tag in soup.find_all("ri:attachment") if tag.has_attr("ri:filename")
    ]

    return images + attachments


def extract_attachments_by_name(client: Confluence, page_id: str, attachment_names: list) -> list:
    """
    Extract download URLs of specific attachments from a Confluence page.
    """
    logger.info(f"Fetching attachments for page ID: {page_id} with target names: {attachment_names}")

    attachments = client.get_attachments_from_content(page_id, expand="body.storage")

    matching_attachments = [
        attachment for attachment in attachments.get("results", [])
        if attachment["title"] in attachment_names
    ]

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
    """
    logger.info("Cleaning header tags in HTML content...")

    soup = BeautifulSoup(html, "lxml")

    for tag_name in ["h1", "h2", "h3", "h4"]:
        for tag in soup.find_all(tag_name):
            for br in tag.find_all("br"):
                br.extract()

            cleaned_text = tag.get_text(strip=True)

            if not cleaned_text:
                if tag.find(["ac:image", "img", "ri:attachment"]):
                    tag.name = "p"
                else:
                    tag.decompose()
            else:
                tag.string = cleaned_text

    return str(soup)
