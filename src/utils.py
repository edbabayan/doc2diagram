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


def convert_html_to_markdown_with_attachments(html_content: str) -> str:
    """
    Converts HTML content to Markdown format, preserving Confluence attachments.

    Args:
        html_content (str): The HTML content to be converted.

    Returns:
        str: The converted Markdown content with attachments preserved.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Replace <ac:image> with Markdown ![]() using <ri:attachment>
    for ac_image in soup.find_all("ac:image"):
        attachment = ac_image.find("ri:attachment")
        if attachment and attachment.has_attr("ri:filename"):
            img_url = attachment["ri:filename"]
            filename = img_url.split("/")[-1]
            markdown_img = f"![{filename}]({img_url})"
            ac_image.replace_with(markdown_img)

    # Replace <ac:link> that wraps an attachment with a Markdown link
    for ac_link in soup.find_all("ac:link"):
        attachment = ac_link.find("ri:attachment")
        link_text = ac_link.get_text(strip=True)
        if attachment and attachment.has_attr("ri:filename"):
            file_url = attachment["ri:filename"]
            markdown_link = f"[{link_text}]({file_url})"
            ac_link.replace_with(markdown_link)

    # Convert the rest of the cleaned HTML
    h = html2text.HTML2Text()
    h.body_width = 0
    markdown_content = h.handle(str(soup))

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


def clean_header_tags(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag_name in ["h1", "h2", "h3", "h4"]:
        for tag in soup.find_all(tag_name):
            for br in tag.find_all("br"):
                br.extract()

            cleaned_text = tag.get_text(strip=True)

            if not cleaned_text:
                if tag.find("ac:image") or tag.find("img") or tag.find("ri:attachment"):
                    tag.name = "p"
                else:
                    tag.decompose()
            else:
                tag.string = cleaned_text

    return str(soup)
