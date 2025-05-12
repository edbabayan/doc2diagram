class AgentPrompts:
    chunker_prompt = """
        You are tasked with creating effective and contextually rich chunks from the document provided. Follow 
        these detailed guidelines to produce high-quality chunks suitable for retrieval augmented generation systems:

        **Guidelines for Chunk Creation:**

        1. **Semantic Segmentation:**
           - **Logical Structure:** Break the document based on its logical structure—chapters, sections, subsections, or paragraphs.
           - **Thematic Consistency:** Ensure each chunk contains a complete idea or topic to maintain context and coherence.

        2. **Optimal Chunk Size:**
           - **Token Limits:** Aim for chunks that are approximately 500 tokens or fewer to fit within model constraints.
           - **Balance Detail and Context:** Chunks should be large enough to provide meaningful context but small enough for efficient processing.

        3. **Overlap Between Chunks:**
           - **Sliding Window:** Use overlapping between chunks to preserve context that might be lost at boundaries.
           - **Overlap Size:** Typically, an overlap of 10-20% of the chunk size works well.

        4. **Include Metadata and Contextual Information:**
           - **Headings and Subheadings:** Start each chunk with clear headings or subheadings to provide context.
           - **Page Numbers and Section Titles:** Include page numbers and section titles within the chunk.
           - **Document Title and Metadata:** Retain important metadata such as the document title, version, date, and any relevant identifiers.

        5. **Preprocessing and Cleaning:**
           - **Remove Non-Text Elements:** Exclude images, charts, or formatting that cannot be processed as text.
           - **Normalize Text:** Correct OCR errors, remove special characters, and standardize the text formatting.

        6. **Context Preservation:**
           - **Avoid Sentence Splitting:** Ensure that sentences are not cut off in the middle between chunks.
           - **Maintain Coherence:** Keep related sentences and paragraphs together to preserve the flow of information.

        7. **Language and Formatting:**
           - **Retain Original Language:** Keep the original language of the document unless instructed otherwise.
           - **Preserve Formatting:** Maintain formatting elements like bullet points, numbered lists, and emphasis where possible.

        8. **Self-Contained Chunks:**
           - **Complete Ideas:** Each chunk should be self-contained, including all necessary context for understanding.
           - **Summaries and Explanations:** Add brief summaries or explanations if needed to clarify the content within the chunk.
        9. **Project name**
           - Don't change the project name, it should be the same as the one in the document.
           
        - **Chunk Only the Current Page:** Create chunks exclusively from the **Current Page Content** provided.
        - **Use Context Appropriately:** Utilize the **Previous Page Content** and **Next Page Content** solely for understanding context, but do not include their text in the chunks.
        """