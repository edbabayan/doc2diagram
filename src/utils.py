import html2text


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
