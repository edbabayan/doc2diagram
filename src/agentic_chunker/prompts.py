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

    3. **Optimal Chunk Size:**
       - Target chunks of approximately 1000 tokens.
       - Balance detail and context within each chunk.
       - Adjust chunk size based on natural semantic boundaries.

    4. **Overlap Between Chunks:**
       - Use 10-20% overlap between chunks to preserve context.
       - Ensure important information isn't lost at chunk boundaries.
       - Key context should appear in adjacent chunks where relevant.

    5. **Metadata Inclusion:**
       - Start each chunk with relevant headings/subheadings.
       - Include page numbers and section titles where available.
       - Retain document title and metadata in each chunk.

    6. **Formatting Preservation:**
       - Maintain ALL original formatting elements (bold, italics, lists, etc.).
       - Preserve spacing and paragraph structure.
       - Keep tables, charts, and visual elements intact with their descriptions.

    7. **Attachment Handling (CRITICAL):**
       - ALL [Attachment] tags MUST be preserved with their complete URLs and descriptions.
       - Example: "[https://example.com/file.pdf](https://example.com/file.pdf) (PDF)" must appear exactly as shown.
       - Never shorten, simplify, or remove attachment references.
       - Keep attachment context by including surrounding text in the same chunk.
       - URLs must remain completely unmodified, including all parameters and special characters.

    8. **Project Information Preservation:**
       - Maintain project names exactly as they appear in the document.
       - Preserve project hierarchies without modification.
       - Keep all project-related metadata intact.

    9. **Output Validation:**
       - Before finalizing each chunk, verify ALL original content is preserved.
       - Confirm ALL attachments are included with their complete URLs.
       - Ensure chunk boundaries occur at natural breaks (end of paragraphs/sections).

    10. **Output Format Requirements:**
        Each chunk MUST include these key fields:
        - content_type: Document type (report, guide, etc.)
        - hierarchy: Document's organizational structure
        - keywords: Key topics in the chunk
        - summary: Brief overview of chunk content
        - project_name: don't change the project name
        - attachments: ALL attachment references present in original text
        - text: The complete chunk content WITH ALL ATTACHMENTS preserved

    **CRITICAL INSTRUCTION:**
    - Create chunks ONLY from the Current Page Content.
    - Use Previous/Next Page Content solely for context understanding.
    - VERIFY that your output includes ALL [Attachment] markers, URLs, and file references from the original text.

    **Example:**
    If input contains: "Brand guide introduction. [Attachment] [https://kb.example.com/file.png](https://kb.example.com/file.png) (PNG)"
    Output MUST contain: "Brand guide introduction. [Attachment] [https://kb.example.com/file.png](https://kb.example.com/file.png) (PNG)"

    ANY chunking that removes or modifies attachments is INCORRECT and unacceptable.
    """