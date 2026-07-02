import { useState } from "react";
import UploadPanel from "./components/UploadPanel";
import QueryPanel from "./components/QueryPanel";
import "./App.css";

export default function App() {
  const [lastUploadedFile, setLastUploadedFile] = useState(null);

  return (
    <div className="app">
      <header>
        <h1>Multi-Agent RAG Research Assistant</h1>
        <p>LangGraph · Qdrant · Groq · FastAPI</p>
      </header>
      <main>
        <UploadPanel
          onUploadSuccess={(filename) => setLastUploadedFile(filename)}
        />
        <QueryPanel documentScope={lastUploadedFile} />
      </main>
    </div>
  );
}
