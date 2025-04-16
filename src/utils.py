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
