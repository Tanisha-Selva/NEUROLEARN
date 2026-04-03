# NeuroLearnAI

**NeuroLearnAI** is a premium, AI-powered adaptive learning platform designed to eliminate inefficient studying by pinpointing exact concept-level weaknesses from raw exam data.

This project was built to deliver a fully functional, production-ready prototype capable of dynamic domain detection, OCR analysis, multi-test progress tracking, and LLM-driven personalized tutoring. 

---

## 🎯 The Problem
Students often receive arbitrary grades (e.g., 65% in Math) without understanding *which specific concepts* dragged their score down. Without targeted feedback, students resort to re-reading entire textbooks, wasting hours revising subjects they already know while neglecting their actual weak spots.

## 💡 The Solution
NeuroLearnAI acts as an omniscient AI tutor. By uploading raw test results or answer sheets (CSV, PDF, or Image), the platform:
- Analyzes the textual content using OCR and LLMs to extract embedded concepts.
- Identifies exact strengths and weaknesses down to the sub-topic level.
- Automatically adjusts the difficulty pipeline for future learning sessions.
- Synthesizes a personalized 7-day study plan populated with targeted resources.

---

## 🧩 Core Features
- **Intelligent File Upload**: Handles CSVs, text-layered PDFs, and unstructured images (via Tesseract OCR).
- **Dual Flow Architecture**: Differentiates automatically between School Students (guided UI, general subjects) and College Students (flexible uploads, domain-specific deep analysis).
- **Native AI Pipeline**: Bypasses rigid regex heuristics by piping raw document text directly into the Gemini 1.5 Flash LLM for dynamic context interpretation, ensuring accurate domain detection (e.g. never confusing DBMS with Calculus).
- **MongoDB Persistence**: Tracks progress across multiple attempts seamlessly within the cloud.
- **WOW UI/UX**: Built with Streamlit but heavily customized with CSS to deliver a premium, dark-mode ed-tech interface featuring glassmorphism, responsive cards, and dynamic Plotly data visualizations.
- **Adaptive Difficulty**: Calculates difficulty flow trends based on historical performance markers.

---

## 🚀 How to Run

### Option 1: Native Local Deployment
1. **Clone the repository** and navigate to the project root:
   ```bash
   cd NeuroLearnAI
   ```
2. **Install system dependencies** (Optional, for image processing):
   - Install `tesseract-ocr` on your OS.
3. **Install Python packages**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure your Environment**:
   - Rename `template.env` (or create a `.env` file) and add your `GEMINI_API_KEY` and `MONGO_URI`. If skipped, the system gracefully falls back to local JSON caching and mockup static AI data.
5. **Run the App**:
   ```bash
   streamlit run frontend.py
   ```

### Option 2: Docker Container
1. **Build the image**:
   ```bash
   docker build -t neurolearnai .
   ```
2. **Run the container**:
   ```bash
   docker run -p 8501:8501 neurolearnai
   ```
   Navigate to `localhost:8501` in your browser.

---

## ⚙️ Tech Stack
- **Frontend**: Streamlit, Plotly, HTML/CSS Injections
- **Backend**: Python 3.10+
- **AI / LLM**: Google Generative AI (Gemini 1.5 API)
- **Database**: MongoDB (PyMongo), Local JSON fallbacks
- **Analytics Parsing**: PyPDF2, Pillow, Pytesseract, Pandas

---

## 🧪 Testing

We have built a robust unit-testing suite assessing backend evaluation pipelines, database concurrency, and AI prompt resilience.
To run the automated tests:
```bash
pytest test_backend.py -v
```

---

_Check out our `skillme.md` file for deep insights into our UX decisions, human-centered design logic, and educational reasoning!_
