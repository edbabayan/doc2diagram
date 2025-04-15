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

def documentation_search(query: str, space: str = "EPMRPP") -> list:
    """
    Search for documentation in Confluence.

    Args:
        query (str): The search query.
        space (str): The space key to search in.

    Returns:
        list: A list of pages that match the search query.
    """
    results = confluence.cql(
        f"space='{space}' and title~'{query}'",
        limit=50,
        expand="body.storage",
    )

    # Extract the page titles and IDs from the results
    pages = [
        {"title": result["title"], "id": result["id"]}
        for result in results["results"]
    ]

    return pages

print('')