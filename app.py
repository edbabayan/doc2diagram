import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from src.config import CFG  # Assuming you're keeping your config

from chatbot import (
    connect_to_qdrant,
    query_retrieval_system,
)


load_dotenv(dotenv_path=CFG.env_variable_file)

# Page configuration
st.set_page_config(
    page_title="Knowledge Base Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar with app information
with st.sidebar:
    st.title("Knowledge Base Assistant")
    st.markdown("""
    This chatbot leverages RAG (Retrieval Augmented Generation) to provide accurate answers
    from your knowledge base.

    **How it works:**
    1. Your question is processed to find relevant documents
    2. The system retrieves context from Qdrant
    3. An LLM generates an answer based on the retrieved context
    """)

    # Optional: Add configuration options in the sidebar
    st.subheader("Configuration")
    retrieval_count = st.slider("Number of documents to retrieve", min_value=1, max_value=10, value=3)
    model_choice = st.selectbox("LLM Model", ["gpt-4o", "gpt-3.5-turbo"], index=0)

    # Add a section to display environment status
    st.subheader("Environment Status")
    qdrant_status = "✅ Connected" if os.environ.get("QDRANT_URL") and os.environ.get(
        "QDRANT_API_KEY") else "❌ Not Connected"
    openai_status = "✅ Connected" if os.environ.get("OPENAI_API_KEY") else "❌ Not Connected"

    st.markdown(f"**Qdrant:** {qdrant_status}")
    st.markdown(f"**OpenAI:** {openai_status}")


# Initialize clients (done here to avoid reinitializing on each rerun)
@st.cache_resource
def initialize_clients():
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Connect to existing Qdrant collection
    qdrant_client, collection_name = connect_to_qdrant("confluence")  # Replace with your collection name

    return openai_client, qdrant_client, collection_name


# Main chat interface
st.title("Chat with your Knowledge Base")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("Ask a question about your knowledge base..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response with a spinner while processing
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Initialize clients
            try:
                openai_client, qdrant_client, collection_name = initialize_clients()

                # First show a message that we're retrieving information
                retrieval_placeholder = st.empty()
                retrieval_placeholder.markdown("🔍 *Retrieving relevant information...*")

                # Retrieve documents from knowledge base
                retrieved_docs = query_retrieval_system(
                    qdrant_client=qdrant_client,
                    collection_name=collection_name,
                    query=prompt,
                    openai_client=openai_client,
                    k=retrieval_count
                )

                # Update the message to show we're now generating the answer
                retrieval_placeholder.markdown("⚙️ *Generating answer based on retrieved information...*")

                # Clear the retrieval message and prepare for streaming
                retrieval_placeholder.empty()

                # Create a placeholder for the streaming text
                response_placeholder = st.empty()

                # Initialize an empty string to store the complete response
                full_response = ""

                # Create the streaming response
                stream = openai_client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system",
                         "content": "You are a helpful assistant that answers questions based on the provided context."},
                        {"role": "user", "content": f"""Answer the following question based on the provided context information. 
If you don't know the answer or the context doesn't contain relevant information, say so.

Context:
{retrieved_docs}

Question: {prompt}

Answer:"""}
                    ],
                    temperature=0,
                    stream=True
                )

                # Display the streaming response
                for chunk in stream:
                    # Extract the content from the chunk
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content or ""
                        full_response += content
                        response_placeholder.markdown(full_response + "▌")

                # Final display without the cursor
                response_placeholder.markdown(full_response)

                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Sorry, an error occurred: {str(e)}"})

# Add a button to clear chat history
if st.button("Clear Conversation"):
    st.session_state.messages = []
    st.rerun()