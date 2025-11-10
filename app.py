# app.py
import streamlit as st
import requests
import PyPDF2
import hashlib
import textwrap
import os
from io import BytesIO

# --- CONFIG ---
# Get OLLAMA_URL from environment with proper formatting
OLLAMA_BASE_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_LIST_URL = f"{OLLAMA_BASE_URL}/api/tags"
MODEL_NAME = "paper-analyzer"

# --- SESSION STATE ---
if "chunks" not in st.session_state:
    st.session_state.chunks = []
if "processed" not in st.session_state:
    st.session_state.processed = False
if "model_ready" not in st.session_state:
    st.session_state.model_ready = False

# --- SIMPLIFIED PROMPTS (Better for TinyLlama) ---
ANSWER_PROMPT = """Analyze this research paper content and answer the question.

CONTEXT: {context}

QUESTION: {question}

Structure your answer with these sections:
1. KEY CONCEPT: [1-2 sentences]
2. MATHEMATICAL FORMULATION: [equations and formulas]
3. MATHEMATICAL INTUITION: [meaning and significance]
4. PRACTICAL IMPLICATIONS: [3-5 applications]
5. SUMMARY: [2-3 sentence recap]

Answer:"""

SUMMARY_PROMPT = """Summarize this research paper content in 100 words using bullet points:

{context}

Summary:"""

QUIZ_PROMPT = """Generate 3 true/false questions based on this research paper content. For each question, provide the answer and explanation.

{context}

Questions:"""

# --- HELPER FUNCTIONS ---
def check_model_ready():
    """Check if Ollama and model are ready"""
    try:
        response = requests.get(OLLAMA_LIST_URL, timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [model.get("name", "") for model in models]
            # Check if our model exists
            if any(MODEL_NAME in name for name in model_names):
                return True
        return False
    except:
        return False

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from PDF file with error handling"""
    try:
        pdf = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def split_text(text: str, chunk_size: int = 800, overlap: int = 100):
    """Split text into manageable chunks"""
    if not text:
        return []
    words = text.split()
    if not words:
        return []
    
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
        if i >= len(words):
            break
    return chunks

def query_ollama(prompt: str) -> str:
    """Query Ollama API with robust error handling"""
    try:
        # First check if model is ready
        if not check_model_ready():
            return "Error: AI model is not ready yet. Please wait a moment and try again."
            
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.5}
            },
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response from model.")
        else:
            return f"API Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "Error: Request timeout - the AI service is taking too long to respond."
    except requests.exceptions.ConnectionError:
        return f"Error: Cannot connect to AI service at {OLLAMA_BASE_URL}. Please check if the backend is running."
    except Exception as e:
        return f"Error: {str(e)}"

def format_response(raw: str) -> str:
    """Format the AI response into structured sections"""
    # If there's an error message, return it as is
    if raw.startswith("Error:") or raw.startswith("API Error:"):
        return f"**❌ {raw}**"
    
    # Initialize sections
    sections = {
        "KEY CONCEPT": "",
        "MATHEMATICAL FORMULATION": "", 
        "MATHEMATICAL INTUITION": "",
        "PRACTICAL IMPLICATIONS": "",
        "SUMMARY": ""
    }
    
    current_section = None
    lines = raw.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for section headers (more flexible matching)
        line_upper = line.upper()
        if "KEY CONCEPT" in line_upper or line.startswith("1."):
            current_section = "KEY CONCEPT"
        elif "MATHEMATICAL FORMULATION" in line_upper or line.startswith("2."):
            current_section = "MATHEMATICAL FORMULATION"
        elif "MATHEMATICAL INTUITION" in line_upper or line.startswith("3."):
            current_section = "MATHEMATICAL INTUITION"
        elif "PRACTICAL IMPLICATIONS" in line_upper or line.startswith("4."):
            current_section = "PRACTICAL IMPLICATIONS"
        elif "SUMMARY" in line_upper or line.startswith("5."):
            current_section = "SUMMARY"
        elif current_section and line:
            # Add content to current section
            if sections[current_section]:
                sections[current_section] += " " + line
            else:
                sections[current_section] = line

    # Format the output
    formatted = "## 📊 Research Paper Analysis\n\n"
    for section, content in sections.items():
        if content and content.strip():
            formatted += f"### {section}\n{content.strip()}\n\n"
        else:
            # If section is empty but we have content, show a placeholder
            if raw.strip():
                formatted += f"### {section}\n*Information not specified in response*\n\n"
            
    return formatted

# --- MAIN APP ---
def main():
    st.set_page_config(
        page_title="Research Paper Analyzer", 
        layout="wide", 
        page_icon="🔍"
    )

    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem; 
        color: #1E90FF; 
        text-align: center; 
        margin-bottom: 1rem;
    }
    .info-box {
        padding: 1rem;
        background-color: #f0f8ff;
        border-radius: 10px;
        border-left: 5px solid #1E90FF;
        margin: 1rem 0;
    }
    .stButton>button {
        background: #4CAF50; 
        color: white; 
        border-radius: 8px; 
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='main-header'>🔍 Research Paper Q&A Assistant</h1>", unsafe_allow_html=True)
    st.markdown("**Upload research papers → Ask questions → Get structured AI analysis**")

    # Check if model is ready
    if not st.session_state.model_ready:
        with st.spinner("🔍 Checking AI model status..."):
            if check_model_ready():
                st.session_state.model_ready = True
                st.success("✅ AI model is ready!")
            else:
                st.warning("⏳ AI model is still loading. Please wait...")

    # Info box about the demo
    st.markdown("""
    <div class="info-box">
    <strong>💡 Demo Note:</strong> This application uses a lightweight AI model for fast responses. 
    For complex research papers, responses focus on key concepts and practical insights.
    </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("📁 Upload Research Paper")
        uploaded_file = st.file_uploader("Choose PDF file", type="pdf")
        
        if st.button("🚀 Process Paper", type="primary", use_container_width=True):
            if uploaded_file:
                with st.spinner("Processing PDF..."):
                    text = extract_text_from_pdf(uploaded_file)
                    
                    if text and len(text) > 100:  # Ensure meaningful content
                        st.session_state.chunks = split_text(text)
                        st.session_state.processed = True
                        st.success(f"✅ Processed! Split into {len(st.session_state.chunks)} sections")
                        
                        # Show first chunk preview
                        with st.expander("Preview first section"):
                            st.text(st.session_state.chunks[0][:500] + "...")
                    else:
                        st.error("❌ Could not extract sufficient text from PDF. Please try another file.")
            else:
                st.warning("⚠️ Please upload a PDF file first")

    # --- MAIN CONTENT ---
    if st.session_state.get("processed", False) and st.session_state.chunks:
        st.success("🎉 Ready! Use the tabs below to analyze the paper.")
        
        # Show basic info
        total_words = sum(len(chunk.split()) for chunk in st.session_state.chunks)
        st.caption(f"📄 Document stats: {len(st.session_state.chunks)} sections, ~{total_words} words")

        tab1, tab2, tab3 = st.tabs(["💬 Q&A Analysis", "📝 Summary", "❓ Quiz"])

        with tab1:
            st.subheader("Ask Questions About the Paper")
            question = st.text_area(
                "Enter your question:", 
                height=100, 
                placeholder="e.g., Explain the main methodology...\nWhat are the key findings?\nDescribe the experimental setup..."
            )
            
            if st.button("🤖 Analyze", type="primary", use_container_width=True):
                if question.strip():
                    if not st.session_state.model_ready:
                        st.error("AI model is not ready yet. Please wait...")
                    else:
                        # Use first 3 chunks for context (adjust based on content)
                        context = "\n\n".join(st.session_state.chunks[:3])
                        prompt = ANSWER_PROMPT.format(context=context, question=question)
                        
                        with st.spinner("🔍 Analyzing paper content..."):
                            raw_response = query_ollama(prompt)
                            formatted_response = format_response(raw_response)
                            st.markdown(formatted_response)
                else:
                    st.warning("Please enter a question")

        with tab2:
            st.subheader("Generate Summary")
            if st.button("📋 Generate Summary", use_container_width=True):
                if not st.session_state.model_ready:
                    st.error("AI model is not ready yet. Please wait...")
                else:
                    context = "\n\n".join(st.session_state.chunks[:5])  # More context for summary
                    prompt = SUMMARY_PROMPT.format(context=context)
                    
                    with st.spinner("📝 Generating summary..."):
                        summary = query_ollama(prompt)
                        st.markdown(f"### 📄 Paper Summary\n{summary}")

        with tab3:
            st.subheader("Generate Quiz")
            if st.button("🎯 Generate Quiz", use_container_width=True):
                if not st.session_state.model_ready:
                    st.error("AI model is not ready yet. Please wait...")
                else:
                    context = "\n\n".join(st.session_state.chunks[:4])
                    prompt = QUIZ_PROMPT.format(context=context)
                    
                    with st.spinner("🎲 Creating quiz questions..."):
                        quiz = query_ollama(prompt)
                        st.markdown(f"### ❓ Comprehension Quiz\n{quiz}")

    else:
        # Welcome screen
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            ### 🎯 How to Use:
            
            1. **Upload** a research paper PDF in the sidebar
            2. **Click** "Process Paper" to extract content  
            3. **Choose** your analysis method:
               - **Q&A**: Ask specific questions about the paper
               - **Summary**: Get a concise overview
               - **Quiz**: Test understanding with true/false questions
            
            ### 📚 Supported Content:
            - Academic research papers
            - Conference proceedings  
            - Technical reports
            - Scientific articles
            """)
        
        with col2:
            st.markdown("""
            ### 🔧 Current Status:
            - Frontend: ✅ Ready
            - AI Backend: {} 
            """.format("✅ Ready" if st.session_state.model_ready else "⏳ Loading..."))

if __name__ == "__main__":
    main()
