import re
from typing import List, Dict
from bs4 import BeautifulSoup


def (html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag_name in ["h1", "h2", "h3", "h4"]:
        for tag in soup.find_all(tag_name):
            # Remove <br> tags from header contents
            for br in tag.find_all("br"):
                br.extract()
            # Replace header contents with plain text
            tag.string = tag.get_text(strip=True)
    return str(soup)


def hierarchical_title_chunking(text: str) -> List[Dict]:
    lines = text.splitlines()
    chunks = []
    stack = []

    for line in lines:
        header_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()

            # Pop deeper or equal level headings
            while stack and stack[-1]['level'] >= level:
                stack.pop()

            new_chunk = {
                "title": title,
                "level": level,
                "chunk_text": "",
                "child_chunks": []
            }

            if stack:
                stack[-1]['child_chunks'].append(new_chunk)
            else:
                chunks.append(new_chunk)

            stack.append(new_chunk)
        else:
            if stack:
                stack[-1]['chunk_text'] += line + '\n'

    return chunks
