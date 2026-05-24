import { useState } from "react";
import questionsData from "./data/questions.json";

export default function App() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [answers, setAnswers] = useState<{ [key: string]: string }>({});

  const handleChange = (id: number, value: string) => {
    setAnswers((prev) => ({
      ...prev,
      [`q${id}`]: value,
    }));
  };

  const handleSubmit = async () => {
    if (!name || !email) {
      alert("Please enter name and email");
      return;
    }

    try {
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          email,
          answers,
        }),
      });

      if (res.ok) {
        alert("Responses saved successfully!");
        setName("");
        setEmail("");
        setAnswers({});
      } else {
        alert("Error saving responses");
      }
    } catch (error) {
      alert("Network error. Make sure the backend server is running.");
      console.error(error);
    }
  };

  return (
    <div style={{ padding: "40px", maxWidth: "800px", margin: "auto" }}>
      <h1>Candidate Evaluation System</h1>

      <h2>Candidate Info</h2>

      <input
        type="text"
        placeholder="Candidate Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ width: "100%", padding: "8px", marginBottom: "10px" }}
      />

      <input
        type="email"
        placeholder="Candidate Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{ width: "100%", padding: "8px", marginBottom: "20px" }}
      />

      <h2>Questions</h2>

      {questionsData.questions.map((q) => (
        <div key={q.id} style={{ marginBottom: "25px" }}>
          <h3>
            {q.id}. {q.text}
          </h3>

          {q.options.map((opt) => (
            <div key={opt}>
              <label>
                <input
                  type="radio"
                  name={`q${q.id}`}
                  value={opt}
                  checked={answers[`q${q.id}`] === opt}
                  onChange={() => handleChange(q.id, opt)}
                />
                {" "}{opt}
              </label>
            </div>
          ))}
        </div>
      ))}

      <button
        onClick={handleSubmit}
        style={{
          padding: "10px 20px",
          fontSize: "16px",
          cursor: "pointer",
        }}
      >
        Submit Evaluation
      </button>
    </div>
  );
}
