import streamlit as st
import importlib.metadata
import re
import fitz
import os

st.set_page_config(page_title="Skill Forge", page_icon="🔧", layout="wide")

# First, check the installed version of google-generativeai
try:
    genai_version = importlib.metadata.version("google-generativeai")
    #st.sidebar.info(f"Google Generative AI version: {genai_version}")
except importlib.metadata.PackageNotFoundError:
    print("Google Generative AI package not found. Please install it.")
    genai_version = "0.0.0"

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

# API key configuration
api_key = "AIzaSyC_9_9rBHatlDMXeoCsvg47A4ZaZ1Zahf0"
api_key = st.secrets["GOOGLE_API_KEY"]

if api_key:
    genai.configure(api_key=api_key)

# Define available models to try in order of preference
PREFERRED_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro-latest",
    "gemini-pro-vision"  # Fallback to an older model
]

# Configure Gemini API with model selection
def configure_gemini():
    try:
        # Check if manual model selection is enabled
        if "manual_model" in st.session_state and st.session_state["manual_model"]:
            model_name = st.session_state.get("model_name", "")
            if model_name:
                st.sidebar.success(f"Using manually selected model: {model_name}")
                
                # Check if the model includes the full path or just the name
                if '/' in model_name:
                    # Full path format
                    model = genai.GenerativeModel(model_name)
                else:
                    # Just model name
                    model = genai.GenerativeModel(model_name=model_name)
                
                return model
        
        # List available models
        available_models = []
        try:
            models = genai.list_models()
            available_models = [model.name for model in models]
            
            # Extract model names for better display
            display_models = []
            for m in available_models:
                if '/' in m:
                    display_models.append(m.split('/')[-1])
                else:
                    display_models.append(m)
                    
            #st.sidebar.write("Available models:", ", ".join(display_models))
        except Exception as e:
            st.sidebar.warning(f"Could not list models: {str(e)}")
            
        # Try to find a preferred model that's available
        for preferred_model in PREFERRED_MODELS:
            for available_model in available_models:
                if preferred_model in available_model:
                    model_name = available_model
                    #st.sidebar.success(f"Using model: {model_name}")
                    
                    # Check if the model includes the full path or just the name
                    if '/' in model_name:
                        # Full path format (older API)
                        model = genai.GenerativeModel(model_name)
                    else:
                        # Just model name (newer API)
                        model = genai.GenerativeModel(model_name=model_name)
                    
                    return model
        
        # If no preferred models are found, use the first available Gemini model
        for available_model in available_models:
            if "gemini" in available_model.lower():
                model_name = available_model
                #st.sidebar.success(f"Using model: {model_name}")
                
                # Check if the model includes the full path or just the name
                if '/' in model_name:
                    # Full path format (older API)
                    model = genai.GenerativeModel(model_name)
                else:
                    # Just model name (newer API)
                    model = genai.GenerativeModel(model_name=model_name)
                
                return model
        
        # If still no model, raise an error
        raise ValueError("No supported Gemini models found in your available models")
        
    except Exception as e:
        st.error(f"❌ API Error: {str(e)}")
        return None

def suggest_courses_gemini(domain, expertise):
    """Fetches AI-generated course recommendations with proper error handling."""
    try:
        model = configure_gemini()
        if not model:
            return "Error configuring the AI model. Please check your API key and model configuration."
            
        prompt = f"""
            I am interested in {domain} and my expertise level is {expertise}. Based on this, suggest 3-5 relevant online courses. For each course, provide:
            - **Course Title**  
            - *Description:* A concise summary of the course content (1-2 lines).  
            - *Platform:* (e.g., Coursera, Udemy, edX)  
            - *Link:* Provide a valid and active URL.  
            If there are no suitable courses available, say so explicitly and briefly explain why that might be the case (e.g., niche domain, new field, etc.).
            Ensure the recommendations are current, well-reviewed, and targeted to the specified expertise level.
            """
        
        # Generate content with proper error handling
        try:
            # Try standard format first (works with most API versions)
            response = model.generate_content(prompt)
        except TypeError:
            # If TypeError, try with list format (older API versions)
            try:
                response = model.generate_content([prompt])
            except Exception as inner_error:
                return f"Error generating content with list format: {str(inner_error)}"
        
        # Handle different response formats
        try:
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'parts') and len(response.parts) > 0:
                return response.parts[0].text
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                # Some API versions use candidates[0].content.parts[0].text
                if hasattr(response.candidates[0], 'content'):
                    if hasattr(response.candidates[0].content, 'parts'):
                        return response.candidates[0].content.parts[0].text
            
            # Fall back to string representation
            return str(response)
        except Exception as format_error:
            return f"Error extracting text from response: {str(format_error)}"

    except Exception as e:
        st.error(f"Error with AI model: {str(e)}")
        return f"Error fetching recommendations: {str(e)}"

def parse_courses(response_text):
    """Extract structured course details from AI response."""
    try:
        # More robust pattern matching to handle varied AI response formats
        course_pattern = re.findall(r"\*\*(.*?)\*\*\s+\*Description:\* (.*?)\s+\*Platform:\* (.*?)\s+\*Link:\* (?:\[(.*?)\]|\((.*?)\))", response_text)
        
        courses = []
        for match in course_pattern:
            title = match[0]
            desc = match[1]
            platform = match[2]
            # Handle different link formats (markdown or plain)
            link = match[3] if match[3] else match[4] if len(match) > 4 else "#"
            courses.append({"title": title, "description": desc, "platform": platform, "link": link})
        
        return courses
    except Exception as e:
        st.error(f"Error parsing courses: {str(e)}")
        return []

def extract_text_from_pdf(pdf_file):
    """Extract text from an uploaded PDF file."""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = "\n".join([page.get_text("text") for page in doc])
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_experience(text):
    """Extract job roles, companies, and descriptions under Experience."""
    try:
        experience_pattern = r"(?i)(Experience|Work Experience|Internships)\s*[:\-\n]([\s\S]*?)(?=\n(?:Projects|Education|Technical Skills|Certificates|$))"
        match = re.search(experience_pattern, text)
        
        if not match:
            return "No experience section found in the resume."
            
        experience_text = match.group(2).strip()
        
        job_entries = re.findall(r"([\w\s]+(?:Intern|Developer|Engineer|Manager))\s+(\w{3,9}\s\d{4}\s*–?\s*\w{0,9}\s?\d{0,4})\s+([\w\s&.,()-]+)", experience_text)
        job_descriptions = re.split(r"[\w\s]+(?:Intern|Developer|Engineer|Manager)\s+\w{3,9}\s\d{4}\s*–?\s*\w{0,9}\s?\d{0,4}\s+[\w\s&.,()-]+", experience_text)
        
        experience_list = []
        for i, job in enumerate(job_entries):
            title, duration, company = job
            description = job_descriptions[i + 1].strip() if i + 1 < len(job_descriptions) else "No description provided."
            experience_list.append(f"**{title}** at **{company}** ({duration})\n\n{description}")
        
        return "\n\n---\n\n".join(experience_list) if experience_list else "No detailed experience information extracted."
    except Exception as e:
        st.error(f"Error extracting experience: {str(e)}")
        return "Error extracting experience information."

def extract_technical_skills(text):
    """Extract all subsections under Technical Skills (Languages, Technology, etc.)."""
    try:
        skills_pattern = r"(?i)(Technical Skills|Skills|Relevant Skills)\s*[:\-\n]([\s\S]*?)(?=\n(?:Projects|Experience|Education|Certificates|$))"
        match = re.search(skills_pattern, text)
        
        if not match:
            return {"General Skills": "No specific skills section found in the resume."}
            
        skills_text = match.group(2).strip()
        
        subsections = re.findall(r"(?i)(Languages|Technology|Developer Tools|Libraries|Software|Frameworks)\s*:\s*([\s\S]*?)(?=\n[A-Z][a-z]*:|$)", skills_text)
        
        structured_skills = {}
        for section, content in subsections:
            structured_skills[section] = content.strip()
            
        # If no subsections were found, return the entire skills text
        if not structured_skills:
            structured_skills["General Skills"] = skills_text
            
        return structured_skills
    except Exception as e:
        st.error(f"Error extracting technical skills: {str(e)}")
        return {"Error": "Could not extract technical skills information."}

def mentor_page(domain):
    """Displays a list of mentors for the given domain."""
    mentors = {
        "Data Science": [
            {"name": "Utkarsh Gupta", "linkedin": "https://www.linkedin.com/in/utkarsh-gupta-650605253/"},
            {"name": "Rushil Sharma", "linkedin": "https://www.linkedin.com/in/rushil-sharma-803299303/"},
        ],
        "Web Development": [
            {"name": "Karan Yadav", "linkedin": "https://www.linkedin.com/in/karan-yadav-46228527b"},
            {"name": "Pratham Karmakar", "linkedin": "https://www.linkedin.com/in/pratham-karmarkar-6b786a293"},
        ],
        "Machine Learning": [
            {"name": "Rithuik Prakash", "linkedin": "https://www.linkedin.com/in/rithuik-prakash-61237a25b"},
            {"name": "Frank Green", "linkedin": "https://www.linkedin.com/in/frankgreencybersec/"},
        ],
        "Default": [
            {"name": "No mentors found", "linkedin": ""},
        ]
    }

    if domain in mentors:
        st.subheader(f"Mentors for {domain}")
        for mentor in mentors[domain]:
            if mentor["linkedin"]:
                st.write(f"[{mentor['name']}]({mentor['linkedin']})") #Linked name
            else:
                st.write(f"{mentor['name']}")
    else:
        st.subheader("No mentors available for this specific domain right now.")
        st.write("Try searching for a different domain such as 'Data Science', 'Web Development', or 'Machine Learning'.")

def chatbot_page():
    """A simple chatbot interface."""
    st.subheader("AI Learning Path Suggestor")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    model = configure_gemini()
    
    if not model:
        st.error("Could not configure the AI model. Please check your API key and try again.")
        return

    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tell me about your past knowledge and background education..."):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        instruction = f"""Given the following background about a user:\n{prompt}\nSuggest 3-5 next topics that the user should consider learning based on their background. \n
        Also, inform the user about any trending topics in their specified domain.
        Explain why each topic is important for their career, provide topic name and keywords that help explore the topic.
        Format:
        Topic: <topic_name>
        Why: <explanation>
        Keywords: <keyword1, keyword2, keyword3>
        
        Trending Topics: <List of trending topics with explanation of why they're important>
        """

        try:
            with st.spinner("Generating response..."):
                # Try standard format first (works with most API versions)
                try:
                    response = model.generate_content(instruction)
                except TypeError:
                    # If TypeError, try with list format (older API versions)
                    response = model.generate_content([instruction])
                
                # Handle different response formats
                if hasattr(response, 'text'):
                    ai_response = response.text
                elif hasattr(response, 'parts') and len(response.parts) > 0:
                    ai_response = response.parts[0].text
                elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                    # Some API versions use candidates[0].content.parts[0].text
                    if hasattr(response.candidates[0], 'content'):
                        if hasattr(response.candidates[0].content, 'parts'):
                            ai_response = response.candidates[0].content.parts[0].text
                else:
                    # Fall back to string representation
                    ai_response = str(response)
        except Exception as e:
            ai_response = f"Error generating response: {str(e)}"

        st.session_state["chat_history"].append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant"):
            st.markdown(ai_response)

# Streamlit UI
def main():    
    st.sidebar.title("Navigation")
    
    # Display debug information
    # with st.sidebar.expander("Debug Info & Instructions"):
    #     st.write("## Troubleshooting")
    #     st.write("If you're having issues with the Google API:")
    #     st.code("pip install --upgrade google-generativeai")
    #     st.write("### Manual Model Selection")
    #     st.write("If automatic model selection fails, try one of these models:")
    #     st.write("- gemini-1.5-pro")
    #     st.write("- gemini-1.5-flash")
    #     st.write("- gemini-1.5-pro-latest")
    #     st.write("- gemini-pro-vision")
        
    #     # Add manual model selection
    #     if "manual_model" not in st.session_state:
    #         st.session_state["manual_model"] = False
            
    #     st.session_state["manual_model"] = st.checkbox("Use manual model selection", value=st.session_state["manual_model"])
        
    #     if st.session_state["manual_model"]:
    #         st.session_state["model_name"] = st.text_input("Enter model name:", value=st.session_state.get("model_name", "gemini-1.5-pro"))
    #         if st.button("Apply Model"):
    #             st.success(f"Will use model: {st.session_state['model_name']}")
    
    page = st.sidebar.radio("Go to", ("Main", "Mentors", "Chatbot"))

    if page == "Main":
        st.markdown(
            """
            <style>
            .main-title {
                color: #2DAA9E; 
                font-size: 3rem;
            }
            .sub-title {
                color: #666;
                font-style: italic;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<h1 class='main-title'>Skill Forge</h1>", unsafe_allow_html=True)
        st.markdown("<h3 class='sub-title'>Crafting career success</h3>", unsafe_allow_html=True)

        st.write("Upload your resume (PDF), extract Experience & Technical Skills, and get personalized course recommendations.")

        if "extracted_content" not in st.session_state:
            st.session_state["extracted_content"] = ""
        
        upload_rsm = st.file_uploader("Drop your resume", type=["pdf"])

        if upload_rsm is not None:
            with st.spinner("Extracting content from your resume..."):
                st.success("✅ File uploaded successfully!")
                resume_text = extract_text_from_pdf(upload_rsm)

                if resume_text:
                    experience = extract_experience(resume_text)
                    skills = extract_technical_skills(resume_text)

                    extracted_content = f"**Extracted Experience:**\n\n{experience}\n\n**Extracted Technical Skills:**\n\n"

                    if isinstance(skills, dict):
                        extracted_content += "\n".join([f"**{key}:** {value}" for key, value in skills.items()])
                    else:
                        extracted_content += skills

                    st.session_state["extracted_content"] = extracted_content
                    st.session_state["domain_suggestion"] = ", ".join(skills.keys()) if isinstance(skills, dict) else ""
                else:
                    st.error("Could not extract text from the PDF. Please try another file.")

        st.subheader("Get Course Recommendations")

        #domain_default = st.session_state.get("domain_suggestion", "")
        domain = st.text_input("Enter your domain of interest (e.g., Data Science, Web Development, Cybersecurity)",
                            value=st.session_state["extracted_content"] if st.session_state["extracted_content"] else "")

        expertise = st.selectbox("Select your expertise level:", ["Beginner", "Intermediate", "Expert"])

        if st.button("Get Course Recommendations"):
            if domain and expertise:
                with st.spinner("Fetching course recommendations... ⏳"):
                    recommendations = suggest_courses_gemini(domain, expertise)
                    courses = parse_courses(recommendations)

                    if courses:
                        st.subheader("Recommended Courses")
                        for course in courses:
                            with st.container():
                                st.markdown(f"### [{course['title']}]({course['link']})")
                                st.write(f"**Description:** {course['description']}")
                                st.write(f"**Platform:** {course['platform']}")
                                st.divider()  # Adds a horizontal line
                    else:
                        # If no courses were parsed but we got a response
                        if recommendations and not recommendations.startswith("Error"):
                            st.subheader("AI Recommendations")
                            st.markdown(recommendations)
                        else:
                            st.error("No valid courses were extracted. Please try again.")
            else:
                st.error("Please enter all required details (Domain, Expertise) before proceeding.")

    elif page == "Mentors":
        st.title("Find Mentors")
        domain = st.session_state.get("domain", "Data Science")  # Default value if not in session
        
        mentor_domain = st.text_input("Enter your domain of interest for finding mentors:", value=domain)
        
        st.session_state["domain"] = mentor_domain
        
        mentor_page(mentor_domain)

    elif page == "Chatbot":
        st.title("AI Learning Assistant")
        chatbot_page()

if __name__ == "__main__":
    main()
