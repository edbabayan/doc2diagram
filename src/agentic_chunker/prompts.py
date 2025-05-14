class AgentPrompts:
    chunker_prompt = """
    You are tasked with creating effective and contextually rich chunks from the document provided. Your primary goal is to maintain the document's integrity while breaking it into manageable segments. Pay special attention to PRESERVING ALL ATTACHMENTS.

    **MANDATORY CHUNKING GUIDELINES:**

    1. **Content Preservation (HIGHEST PRIORITY):**
       - NEVER remove or modify ANY content from the original text.
       - ALL attachments, URLs, links, and file references MUST be preserved exactly as they appear.
       - When you see [Attachment] markers with URLs, these MUST appear in your output identically.
       - Every single character, including formatting markers, must be preserved.

    2. **Semantic Segmentation:**
       - Break the document based on logical structure—chapters, sections, subsections, or paragraphs.
       - Ensure each chunk contains a complete idea or topic.
       - Keep related content together whenever possible.
       - NEVER create chunks that contain only a single sentence or very small text segments.
       - Each chunk MUST contain multiple paragraphs or a substantial section of content.

    3. **Optimal Chunk Size:**
       - Target chunks of approximately 1000 tokens.
       - MINIMUM chunk size should be 500 tokens (unless the document itself is smaller).
       - AVOID creating very small chunks—ensure each chunk has sufficient context to be understood independently.
       - Balance detail and context within each chunk.
       - Adjust chunk size based on natural semantic boundaries.

    4. **Meaningful Content Units:**
       - Each chunk must represent a meaningful unit of information.
       - Single sentences, isolated paragraphs, or tiny text fragments are NOT acceptable as standalone chunks.
       - If a section is too small to form a meaningful chunk by itself, combine it with related content.
       - Prioritize logical grouping over strict token count when dealing with smaller sections.

    5. **Overlap Between Chunks:**
       - Use 10-20% overlap between chunks to preserve context.
       - Ensure important information isn't lost at chunk boundaries.
       - Key context should appear in adjacent chunks where relevant.
       - For very short sections that must span chunks, include them entirely in both chunks.

    6. **Metadata Inclusion:**
       - Start each chunk with relevant headings/subheadings.
       - Include page numbers and section titles where available.
       - Retain document title and metadata in each chunk.

    7. **Formatting Preservation:**
       - Maintain ALL original formatting elements (bold, italics, lists, etc.).
       - Preserve spacing and paragraph structure.
       - Keep tables, charts, and visual elements intact with their descriptions.

    8. **Attachment Handling (CRITICAL):**
       - ALL [Attachment] tags MUST be preserved with their complete URLs and descriptions.
       - Example: "[https://example.com/file.pdf](https://example.com/file.pdf) (PDF)" must appear exactly as shown.
       - Never shorten, simplify, or remove attachment references.
       - Keep attachment context by including surrounding text in the same chunk.
       - URLs must remain completely unmodified, including all parameters and special characters.

    9. **Project Information Preservation:**
       - Maintain project names exactly as they appear in the document.
       - Preserve project hierarchies without modification.
       - Keep all project-related metadata intact.

    10. **Chunk Validation Checklist:**
        - Does the chunk contain MULTIPLE paragraphs or substantial content?
        - Is the chunk at least 500 tokens (unless the document itself is smaller)?
        - Does the chunk represent a complete idea or logical section?
        - Are ALL original content and formatting preserved?
        - Are ALL attachments and URLs included exactly as in the original?
        - Do chunk boundaries occur at natural breaks (end of sections/subsections)?

    11. **Output Format Requirements:**
        Each chunk MUST include these key fields:
        - content_type: Document type (report, guide, etc.)
        - hierarchy: Document's organizational structure
        - keywords: Key topics in the chunk
        - summary: Brief overview of chunk content
        - project_name: don't change the project name
        - attachments: ALL attachment references present in original text
        - text: The complete chunk content WITH ALL ATTACHMENTS preserved
        - chunk_size: Approximate token count of the chunk

    **CRITICAL INSTRUCTION:**
    - Create chunks ONLY from the Current Page Content.
    - Use Previous/Next Page Content solely for context understanding.
    - VERIFY that your output includes ALL [Attachment] markers, URLs, and file references from the original text.
    - NEVER create chunks consisting of single sentences or very small text fragments.
    - When in doubt about chunk size, err on the side of LARGER chunks rather than smaller ones.

    **Example:**
    If input contains: "Brand guide introduction. [Attachment] [https://kb.example.com/file.png](https://kb.example.com/file.png) (PNG)"
    Output MUST contain: "Brand guide introduction. [Attachment] [https://kb.example.com/file.png](https://kb.example.com/file.png) (PNG)"

    ANY chunking that removes or modifies attachments is INCORRECT and unacceptable.
    ANY chunking that creates single-sentence or very small text fragments is INCORRECT and unacceptable.
    """
