# MangaPost AI Studio ⛩️

MangaPost is a premium, cutting-edge AI-powered pre-production studio for Manga and Webtoon creators. It utilizes a high-performance multi-agent workflow (Agentic Crew) to autonomously process story outlines into highly-structured, page-by-page manga scripts, complete with algorithmic panel layouts. 

Built with an ultra-lightweight Vanilla JS frontend and a Serverless FastAPI backend, MangaPost achieves maximum native performance with zero build steps or heavy dependencies.

![MangaPost Studio](https://raw.githubusercontent.com/user/mangapost/main/preview.png) *(Placeholder for your app screenshot)*

## ✨ Core Features

*   **Multi-Agent AI Pipeline**: Powered by Llama 3.3 70B via the Groq engine, processing stories through a Lead Writer, Pacing Editor, and Dialogue Polisher sequentially.
*   **Real-time SSE Streaming**: Watch your manga script generate in real-time natively in the browser—no state-management bloat needed.
*   **Algorithmic Layout Engine**: Automatically transforms script pacing and panel sizes into vector-based wireframe layouts dynamically.
*   **Neo-Noir Design System**: A premium dark-mode, glassmorphism UI designed for deep creative focus. 
*   **Zero-Dependency Frontend**: 100% Native Web Architecture (HTML, CSS, JS). No React, No Vite, No Node.js.
*   **Serverless Ready**: The Python backend is optimized into a monolithic `api/index.py` perfect for one-click Vercel deployment.

## 🛠 Tech Stack

*   **Frontend**: Vanilla HTML5, CSS3, & JavaScript.
*   **Backend**: Python, FastAPI.
*   **AI Orchestration**: CrewAI & LangChain.
*   **LLM Provider**: Groq (Llama 3.3 70B).
*   **Deployment**: Vercel (Native integration for static frontend and serverless python backend).

## 🚀 Deployment (Vercel)

Deploying MangaPost is incredibly simple. Because it lacks Node modules, Vercel will instantly serve the frontend and map the `/api/generate` endpoint seamlessly.

1.  Push this exact repository to GitHub.
2.  Connect the repository to a new project in **Vercel**.
3.  Go to your Vercel Project **Settings > Environment Variables**:
    *   Add `GROQ_API_KEY` and paste in your API key from Groq.
4.  Hit **Deploy**.

*Note due to Vercel Hobby limits: Serverless functions time out at 60s. Depending on script generation length, Vercel Pro (300s timeout) may be optimal for heavier CrewAI loads.*

## 💻 Local Development

Want to test it locally before deploying?

1.  **Start your Virtual Environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    # OR source venv/bin/activate # Mac/Linux
    ```
2.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Add Secrets:**
    Create a `.env` file in the root directory and add:
    ```env
    GROQ_API_KEY=your_key_here
    ```
4.  **Run the Server:**
    ```bash
    uvicorn api.index:app --reload
    ```
5.  **Open the Studio:**
    Visit `http://localhost:8000` in your browser.

## 📁 Repository Structure
```text
.
├── api/
│   └── index.py         # Main Serverless Backend & AI Logic
├── .gitignore           # Ignores local environments 
├── .vercelignore        # Ignores files from Vercel deployment
├── app.js               # Frontend Logic & SSE Event handling
├── index.html           # UI DOM Structure
├── requirements.txt     # Python Dependencies
├── style.css            # Pre-compiled Design System UI
└── vercel.json          # Serverless routing config
```
