import UploadPanel from "./components/UploadPanel";
import QueryPanel from "./components/QueryPanel";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>Multi-Agent RAG Research Assistant</h1>
        <p>LangGraph · Qdrant · Groq · FastAPI</p>
      </header>

      <main>
        <UploadPanel />
        <QueryPanel />
      </main>
    </div>
  );
}
