# SkillForge Pro 🚀

### AI-Powered Resume Analyzer and Course Recommender

SkillForge Pro is an intelligent web application that helps users:
- Extract skills and work experience from a resume (PDF)
- Get personalized course recommendations using Google's Gemini AI
- Interact with an AI chatbot for learning path guidance
- Browse a mentor directory to connect with industry experts

---

## 🌟 Features

✅ Upload a resume or manually enter a domain of interest  
✅ Extract technical skills and experience using regex-based NLP  
✅ Use Gemini 1.5 Pro to fetch high-quality course suggestions  
✅ Get learning path insights via AI chatbot  
✅ Clean and minimal UI with dark-mode compatibility

---

## 🧑‍💻 Tech Stack

- **Frontend/Backend**: [Streamlit](https://streamlit.io/)
- **AI Model**: [Google Gemini Pro](https://ai.google.dev/)
- **PDF Parsing**: PyMuPDF (`fitz`)
- **Language**: Python

---

## 🚀 Deployment

This app is deployable on **Streamlit Community Cloud**.

### 🛠 To Deploy:
1. Push this repo to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Point to `app.py` as the entry script
4. Add your Gemini API key in **Secrets** like this:

```toml
GOOGLE_API_KEY = "your-gemini-api-key-here"
