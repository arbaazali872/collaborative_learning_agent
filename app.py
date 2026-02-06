import streamlit as st
from openai import OpenAI
from prompts import get_system_prompt, EXAMPLE_TOPICS

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

client = get_openai_client()

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
        temperature=0.7
    )
    
    # Extract response text
    assistant_message = response.choices[0].message.content
    
    # Add assistant response to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_message
    })
    
    return assistant_message


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
        
        # Review button - show after first exchange
        if len(st.session_state.messages) >= 2:
            if st.button("📝 Review Session", use_container_width=True, type="primary"):
                with st.spinner("Preparing review..."):
                    trigger_review()
                st.rerun()
        
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