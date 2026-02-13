import streamlit as st
from openai import OpenAI
from prompts import get_system_prompt, EXAMPLE_TOPICS
import chromadb
from chromadb.config import Settings
import time

# Page configuration
st.set_page_config(
    page_title="Collaborative ML Learning",
    page_icon="🤖",
    layout="wide"
)

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    """Initialize and cache OpenAI client."""
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        st.error("Please add your OPENAI_API_KEY to .streamlit/secrets.toml")
        st.stop()
    return OpenAI(api_key=api_key)

# Initialize ChromaDB client
@st.cache_resource
def get_chroma_client():
    """Initialize and cache ChromaDB client."""
    client = chromadb.PersistentClient(path="./chroma_db")
    return client

client = get_openai_client()
chroma_client = get_chroma_client()

# Get or create collection
@st.cache_resource
def get_collection():
    """Get or create ChromaDB collection for saved messages."""
    return chroma_client.get_or_create_collection(
        name="saved_understanding",
        metadata={"description": "User-saved learning insights"}
    )

collection = get_collection()

# Session state initialization
def initialize_session_state():
    """Initialize all session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'depth_level' not in st.session_state:
        st.session_state.depth_level = None
    
    if 'system_prompt' not in st.session_state:
        st.session_state.system_prompt = None

initialize_session_state()


def call_gpt(user_message: str) -> str:
    """Call OpenAI API with conversation history and system prompt."""
    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Prepare messages for API (OpenAI format includes system message in messages array)
    api_messages = [{"role": "system", "content": st.session_state.system_prompt}]
    
    for msg in st.session_state.messages:
        api_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=api_messages,
        max_tokens=2000,
        temperature=0.5
    )
    
    # Extract response text
    assistant_message = response.choices[0].message.content
    
    # Add assistant response to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_message
    })
    
    return assistant_message


def save_recent_response():
    """Save the most recent assistant response to ChromaDB."""
    # Find the last assistant message
    assistant_messages = [msg for msg in st.session_state.messages if msg["role"] == "assistant"]
    
    if not assistant_messages:
        st.warning("No assistant responses to save yet!")
        return
    
    last_response = assistant_messages[-1]["content"]
    
    # Generate unique ID using timestamp
    save_id = f"save_{int(time.time() * 1000)}"
    
    # Save to ChromaDB
    collection.add(
        documents=[last_response],
        ids=[save_id],
        metadatas=[{
            "timestamp": str(int(time.time())),
            "depth_level": st.session_state.depth_level
        }]
    )
    
    st.success("✅ Response saved!")


def retrieve_previous_understanding():
    """Retrieve similar saved messages based on recent conversation context."""
    # Get recent 2 messages as query context
    if len(st.session_state.messages) < 2:
        st.info("Not enough conversation yet. Start learning first!")
        return
    
    recent_messages = st.session_state.messages[-2:]
    query_text = " ".join([msg["content"] for msg in recent_messages])
    
    # Query ChromaDB for similar saved messages
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=1
        )
        
        if results['documents'] and len(results['documents'][0]) > 0:
            saved_message = results['documents'][0][0]
            
            # Inject into conversation
            retrieve_prompt = f"""SYSTEM NOTE: The user just clicked "Retrieve Previous Understanding." 
Below is a message WE (you and the user) worked through in a PAST conversation that seems 
relevant to our current discussion. This is NOT something the user just said now - it's 
something we figured out together before.

===== PREVIOUSLY SAVED UNDERSTANDING =====
{saved_message}
============================================

Please acknowledge this past understanding and ask the user if they'd like to:
1. Refine/improve this understanding
2. Connect it to what we're currently discussing
3. Explore a different aspect of the topic

Be clear this is from a previous session, not something they just explained."""
            
            call_gpt(retrieve_prompt)
            st.rerun()
        else:
            st.info("No previous understanding found on this topic. Let's work through it together!")
            
    except Exception as e:
        st.info("No previous understanding found on this topic. Let's work through it together!")


def trigger_review():
    """Inject review prompt asking GPT to list covered topics."""
    review_prompt = """Looking at our conversation so far, please:
1. List the main ML/DS topics we've discussed
2. For each topic, write 1 sentence summarizing what we covered
3. Ask me which topic I'd like to revisit

IMPORTANT: Only list topics we actually discussed. Don't mention anything we haven't covered."""
    
    # Call GPT with the review prompt
    return call_gpt(review_prompt)


def reset_session():
    """Reset the learning session."""
    st.session_state.messages = []
    st.session_state.depth_level = None
    st.session_state.system_prompt = None


# ===== UI LAYOUT =====

st.title("🤖 Collaborative ML Learning System")
st.markdown("Learn Data Science & ML concepts through collaborative dialogue")

# Sidebar for session configuration
with st.sidebar:
    st.header("Session Configuration")
    
    # Show current session info if active
    if st.session_state.depth_level:
        st.success(f"**Active Session**")
        st.info(f"**Mode:** {st.session_state.depth_level.title()}")
        
        st.markdown("---")
        
        # Review button - always show from start
        if st.button("📝 Review Session", use_container_width=True, type="primary"):
            with st.spinner("Preparing review..."):
                trigger_review()
            st.rerun()
        
        st.markdown("---")
        
        # Save recent response button
        if st.button("💾 Save Recent Response", use_container_width=True):
            save_recent_response()
        
        # Retrieve previous understanding button
        if st.button("🔍 Retrieve Previous Understanding", use_container_width=True):
            retrieve_previous_understanding()
        
        st.markdown("---")
        
        if st.button("Reset Session", type="secondary"):
            reset_session()
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("About This System")
    st.markdown("""
    This is a **collaborative learning partner**, not just a Q&A bot.
    
    **How it works:**
    1. Share what you know
    2. Learn through structured explanations
    3. Summarize in your own words
    4. Answer challenge questions
    5. Build deeper understanding
    
    **Learning Framework:**
    - Historical context
    - Previous limitations
    - New approaches
    - How problems were solved
    """)
    
    st.markdown("---")
    
    st.subheader("Example Topics")
    with st.expander("Click to see examples"):
        for topic in EXAMPLE_TOPICS:
            st.markdown(f"- {topic}")

# Main content area
if st.session_state.depth_level is None:
    # Session setup screen
    st.subheader("Welcome! Let's set up your learning session")
    
    st.markdown("""
    Before we begin, tell me about your learning goal. This helps me adjust the depth 
    and style of our conversation.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Interview Prep", use_container_width=True, type="primary"):
            st.session_state.depth_level = "interview"
            st.session_state.system_prompt = get_system_prompt("interview")
            st.rerun()
        st.caption("Focus on practical concepts and clear articulation")
    
    with col2:
        if st.button("📚 Exam Preparation", use_container_width=True, type="primary"):
            st.session_state.depth_level = "exam"
            st.session_state.system_prompt = get_system_prompt("exam")
            st.rerun()
        st.caption("Balanced depth with theory and practice")
    
    with col3:
        if st.button("🔬 Research Report", use_container_width=True, type="primary"):
            st.session_state.depth_level = "research"
            st.session_state.system_prompt = get_system_prompt("research")
            st.rerun()
        st.caption("Comprehensive coverage with deep technical detail")
    
    st.markdown("---")
    st.info("💡 **Tip:** You can reset your session anytime using the sidebar")

else:
    # Active learning session
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question or share your thoughts..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_gpt(prompt)
                st.markdown(response)

# Footer
st.markdown("---")
st.caption("Collaborative Learning System | Powered by GPT-4o-mini & Streamlit")