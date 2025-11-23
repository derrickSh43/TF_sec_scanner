import React, { useState, useEffect } from "react";
import "./App.css";

/* ---------- API helpers ---------- */

const BASE_URL = "http://127.0.0.1:8000";

async function apiGet(path, params = {}) {
  const url = new URL(BASE_URL + path);
  Object.keys(params).forEach((k) => {
    if (params[k] !== "" && params[k] != null) {
      url.searchParams.append(k, params[k]);
    }
  });
  const res = await fetch(url.toString());
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function apiPatch(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(BASE_URL + path, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

/* ---------- Root app ---------- */

function App() {
  const [view, setView] = useState("home"); // "home" | "practice" | "questions"

  return (
    <div className="app-shell">
      {/* Top nav */}
      <header className="nav">
        <div className="nav-inner">
          <div className="nav-left">
            <div className="nav-logo-badge">IC</div>
            <div className="nav-title-block">
              <div className="nav-title">Interview Coach</div>
              <div className="nav-subtitle">DevOps · Cloud · Security</div>
            </div>
          </div>

          <div className="nav-links">
            <button
              className={`nav-link ${view === "home" ? "nav-link--active" : ""}`}
              onClick={() => setView("home")}
            >
              Home
            </button>
            <button
              className={`nav-link ${view === "practice" ? "nav-link--active" : ""}`}
              onClick={() => setView("practice")}
            >
              Practice
            </button>
            <button
              className={`nav-link ${view === "questions" ? "nav-link--active" : ""}`}
              onClick={() => setView("questions")}
            >
              Question Bank
            </button>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="app-main">
        {view === "home" && <HomeView onNavigate={setView} />}
        {view === "practice" && <PracticeView onDone={() => setView("home")} />}
        {view === "questions" && <QuestionBankView />}
      </main>
    </div>
  );
}

/* ---------- Home (styled like KodeKloud) ---------- */

function HomeView({ onNavigate }) {
  return (
    <div className="page-container">
      {/* Hero Section */}
      <section className="home-hero">
        <h1>Drill like a real cloud interview.</h1>
        <p>
          Practice senior-level DevOps, SRE, Cloud Security, and Architect interviews with
          structured questions and AI feedback. Type your answers now; voice support is coming next.
        </p>

        <div className="home-hero-buttons">
          <button className="btn-primary" onClick={() => onNavigate("practice")}>
            Start Practice Session
          </button>
          <button className="btn-secondary" onClick={() => onNavigate("questions")}>
            Manage Question Bank
          </button>
        </div>

        <p className="home-hero-hint">
          Tip: Seed 10–20 questions per role, then run rapid-fire sessions and iterate on your
          answers.
        </p>
      </section>

      {/* 2-column info grid */}
      <section className="grid-2col home-info-grid">
        <div className="card">
          <h3 className="section-title">How to use this tool</h3>
          <ul className="info-list">
            <li>Seed a question bank per role + style (DevOps, SRE, Security, Architect).</li>
            <li>Run practice sessions and answer out loud or by typing.</li>
            <li>Use the AI brain to evaluate clarity, depth, and seniority signal.</li>
            <li>Iterate like a real coaching loop before your actual interviews.</li>
          </ul>
        </div>

        <div className="card">
          <h3 className="section-title">Session snapshot</h3>
          <ul className="info-list">
            <li>
              <strong>Modes</strong> – Offline heuristics &amp; Online AI.
            </li>
            <li>
              <strong>Roles</strong> – DevOps • SRE • Platform • Security.
            </li>
            <li>
              <strong>Styles</strong> – deep_technical • behavioral • candidate_led.
            </li>
            <li>
              <strong>Multi-track</strong> – build tracks per company or job posting.
            </li>
            <li>
              <strong>Realistic</strong> – follow-up questions and targeted gaps.
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}

/* ---------- Question Bank (full logic, in a card) ---------- */

function QuestionBankView() {
  const [roleFilter, setRoleFilter] = useState("");
  const [styleFilter, setStyleFilter] = useState("");
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Add form state
  const [newTemplate, setNewTemplate] = useState({
    role: "",
    style: "standard_behavioral",
    difficulty: "medium",
    question_text: "",
    tags: "",
  });

  // Editing state
  const [editingId, setEditingId] = useState(null);
  const [editingData, setEditingData] = useState({});

  // 🔹 Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  async function fetchTemplates() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet("/question-templates", {
        role: roleFilter || undefined,
        style: styleFilter || undefined,
      });
      setTemplates(data);
      setCurrentPage(1); // reset to first page whenever we refetch
    } catch (err) {
      console.error(err);
      setError("Failed to load templates: " + err.message);
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchTemplates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter, styleFilter]);

  async function handleAdd(e) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost("/question-templates", newTemplate);
      setNewTemplate({
        role: "",
        style: "standard_behavioral",
        difficulty: "medium",
        question_text: "",
        tags: "",
      });
      await fetchTemplates();
    } catch (err) {
      setError("Failed to add template: " + err.message);
    }
  }

  function startEdit(tpl) {
    setEditingId(tpl.id);
    setEditingData({
      question_text: tpl.question_text || "",
      difficulty: tpl.difficulty || "medium",
      tags: tpl.tags || "",
      is_active: tpl.is_active == null ? true : tpl.is_active,
    });
  }

  async function saveEdit(id) {
    setError(null);
    try {
      await apiPatch(`/question-templates/${id}`, editingData);
      setEditingId(null);
      setEditingData({});
      await fetchTemplates();
    } catch (err) {
      setError("Failed to save: " + err.message);
    }
  }

  async function deactivate(id) {
    if (!window.confirm("Deactivate this template?")) return;
    setError(null);
    try {
      await apiDelete(`/question-templates/${id}`);
      await fetchTemplates();
    } catch (err) {
      setError("Failed to deactivate: " + err.message);
    }
  }

  function truncate(text, n = 80) {
    if (!text) return "";
    return text.length > n ? text.slice(0, n - 1) + "…" : text;
  }

  // 🔹 Pagination helpers
  const totalPages = Math.max(1, Math.ceil(templates.length / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const visibleTemplates = templates.slice(startIndex, startIndex + pageSize);

  function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    setCurrentPage(page);
  }

  return (
    <div className="page-container">
      <section className="card">
        <h2 className="section-title">Question Bank</h2>

        {/* Add new template form */}
        <section style={{ marginBottom: 24 }}>
          <h3 className="section-title">Add new question template</h3>
          <form
            onSubmit={handleAdd}
            style={{ display: "grid", gap: 8, maxWidth: 700 }}
          >
            <input
              placeholder="Role"
              value={newTemplate.role}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, role: e.target.value })
              }
              required
            />
            <select
              value={newTemplate.style}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, style: e.target.value })
              }
            >
              <option value="standard_behavioral">standard_behavioral</option>
              <option value="deep_technical">deep_technical</option>
              <option value="candidate_led">candidate_led</option>
              <option value="stress_test">stress_test</option>
            </select>
            <select
              value={newTemplate.difficulty}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, difficulty: e.target.value })
              }
            >
              <option value="easy">easy</option>
              <option value="medium">medium</option>
              <option value="hard">hard</option>
            </select>
            <textarea
              placeholder="Question text"
              rows={3}
              value={newTemplate.question_text}
              onChange={(e) =>
                setNewTemplate({
                  ...newTemplate,
                  question_text: e.target.value,
                })
              }
              required
            />
            <input
              placeholder="Tags (comma-separated)"
              value={newTemplate.tags}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, tags: e.target.value })
              }
            />
            <div>
              <button type="submit" className="btn-primary">
                Add Template
              </button>
            </div>
          </form>
        </section>

        {/* Filters */}
        <section style={{ marginBottom: 24 }}>
          <h3 className="section-title">Filters</h3>
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <input
              placeholder="Role"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              style={{ minWidth: 220 }}
            />
            <select
              value={styleFilter}
              onChange={(e) => setStyleFilter(e.target.value)}
            >
              <option value="">All styles</option>
              <option value="standard_behavioral">standard_behavioral</option>
              <option value="deep_technical">deep_technical</option>
              <option value="candidate_led">candidate_led</option>
              <option value="stress_test">stress_test</option>
            </select>
            <button
              type="button"
              className="btn-secondary"
              onClick={fetchTemplates}
            >
              Refresh
            </button>
          </div>
        </section>

        {/* Templates table */}
        <section>
          <h3 className="section-title">Templates</h3>
          {loading && <div>Loading templates...</div>}
          {error && <div style={{ color: "#fb7185" }}>{error}</div>}
          {!loading && templates.length === 0 && (
            <div>No templates found.</div>
          )}
          {!loading && templates.length > 0 && (
            <>
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{ width: "100%", borderCollapse: "collapse" }}
                >
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Role</th>
                      <th>Style</th>
                      <th>Difficulty</th>
                      <th>Question</th>
                      <th>Tags</th>
                      <th>Active</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleTemplates.map((t) => (
                      <React.Fragment key={t.id}>
                        <tr>
                          <td>{t.id}</td>
                          <td>{t.role}</td>
                          <td>{t.style}</td>
                          <td>{t.difficulty}</td>
                          <td title={t.question_text}>
                            {truncate(t.question_text)}
                          </td>
                          <td>{t.tags}</td>
                          <td>{t.is_active ? "Yes" : "No"}</td>
                          <td>
                            <button
                              className="btn-table"
                              onClick={() => startEdit(t)}
                            >
                              Edit
                            </button>{" "}
                            <button
                              className="btn-table btn-table--danger"
                              onClick={() => deactivate(t.id)}
                            >
                              Deactivate
                            </button>
                          </td>
                        </tr>
                        {editingId === t.id && (
                          <tr>
                            <td colSpan={8}>
                              <div
                                style={{
                                  display: "grid",
                                  gap: 8,
                                  padding: 12,
                                  background: "rgba(15,23,42,0.7)",
                                  borderRadius: 12,
                                }}
                              >
                                <textarea
                                  rows={3}
                                  value={editingData.question_text}
                                  onChange={(e) =>
                                    setEditingData({
                                      ...editingData,
                                      question_text: e.target.value,
                                    })
                                  }
                                />
                                <div
                                  style={{
                                    display: "flex",
                                    flexWrap: "wrap",
                                    gap: 8,
                                    alignItems: "center",
                                  }}
                                >
                                  <select
                                    value={editingData.difficulty}
                                    onChange={(e) =>
                                      setEditingData({
                                        ...editingData,
                                        difficulty: e.target.value,
                                      })
                                    }
                                  >
                                    <option value="easy">easy</option>
                                    <option value="medium">medium</option>
                                    <option value="hard">hard</option>
                                  </select>
                                  <input
                                    placeholder="Tags"
                                    value={editingData.tags}
                                    onChange={(e) =>
                                      setEditingData({
                                        ...editingData,
                                        tags: e.target.value,
                                      })
                                    }
                                  />
                                  <label
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 6,
                                    }}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={!!editingData.is_active}
                                      onChange={(e) =>
                                        setEditingData({
                                          ...editingData,
                                          is_active: e.target.checked,
                                        })
                                      }
                                    />
                                    Active
                                  </label>
                                  <div style={{ marginLeft: "auto" }}>
                                    <button
                                      className="btn-table"
                                      onClick={() => saveEdit(t.id)}
                                    >
                                      Save
                                    </button>{" "}
                                    <button
                                      className="btn-table"
                                      onClick={() => {
                                        setEditingId(null);
                                        setEditingData({});
                                      }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 🔹 Pagination controls */}
              {totalPages > 1 && (
                <div className="pagination">
                  <button
                    className="btn-secondary pagination-btn"
                    disabled={currentPage === 1}
                    onClick={() => goToPage(currentPage - 1)}
                  >
                    Prev
                  </button>

                  <span className="pagination-info">
                    Page {currentPage} of {totalPages}
                  </span>

                  <button
                    className="btn-secondary pagination-btn"
                    disabled={currentPage === totalPages}
                    onClick={() => goToPage(currentPage + 1)}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </section>
    </div>
  );
}


/* ---------- Practice (full logic, styled wrapper) ---------- */

function PracticeView({ onDone }) {
  const [step, setStep] = useState("select"); // "select" | "practice" | "summary"

  const [role, setRole] = useState("Senior DevOps Engineer");
  const [style, setStyle] = useState("deep_technical");

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [index, setIndex] = useState(0);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [answers, setAnswers] = useState([]);

  // 🔹 AI feedback for each question (same index as questions[])
  const [feedback, setFeedback] = useState([]);
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState(null);

  async function startPractice() {
    setLoading(true);
    setError(null);
    setEvalError(null);
    setQuestions([]);
    setAnswers([]);
    setFeedback([]);
    setIndex(0);
    setCurrentAnswer("");

    try {
      const data = await apiGet("/question-templates", {
        role: role || undefined,
        style: style || undefined,
      });

      if (!data || data.length === 0) {
        setError(
          "No templates found for this role/style. Add questions in the Question Bank first."
        );
        setLoading(false);
        return;
      }

      setQuestions(data);
      setStep("practice");
    } catch (err) {
      setError("Failed to load templates: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function evaluateAnswer(question, answer, qIndex) {
    setEvaluating(true);
    setEvalError(null);
    try {
      const res = await apiPost("/evaluate-answer", {
        question_text: question.question_text,
        answer_text: answer,
        role: question.role,
        style: question.style,
      });

      setFeedback((prev) => {
        const copy = [...prev];
        copy[qIndex] = res;
        return copy;
      });
    } catch (err) {
      console.error(err);
      setEvalError("AI evaluation failed: " + err.message);
    } finally {
      setEvaluating(false);
    }
  }

  async function handleNext() {
    if (!questions.length) return;

    const q = questions[index];
    const answerToSave = currentAnswer;

    // store answer
    setAnswers((prev) => {
      const copy = [...prev];
      copy[index] = answerToSave;
      return copy;
    });

    // call AI
    await evaluateAnswer(q, answerToSave, index);

    setCurrentAnswer("");

    if (index + 1 >= questions.length) {
      setStep("summary");
    } else {
      setIndex((i) => i + 1);
    }
  }

  function handlePrevious() {
    if (index === 0) return;
    setIndex((i) => i - 1);
    setCurrentAnswer(answers[index - 1] || "");
    setEvalError(null);
  }

  function backToHome() {
    setStep("select");
    setQuestions([]);
    setAnswers([]);
    setFeedback([]);
    setIndex(0);
    setCurrentAnswer("");
    setError(null);
    setEvalError(null);
    if (onDone) onDone();
  }

  const currentQuestion = questions[index];
  const currentFeedback = feedback[index];

  return (
    <div className="page-container">
      {/* Step 1: select role/style */}
      {step === "select" && (
        <section className="card">
          <h2 className="section-title">Practice Interview</h2>
          <p style={{ marginBottom: 20 }}>
            Choose a role & style, then drill through your own curated question
            set. Answers will be evaluated by the AI brain.
          </p>

          <div
            style={{ display: "grid", gap: 12, maxWidth: 480, marginBottom: 16 }}
          >
            <label>
              Role (free text)
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </label>

            <label>
              Style
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                style={{ marginTop: 4 }}
              >
                <option value="standard_behavioral">standard_behavioral</option>
                <option value="deep_technical">deep_technical</option>
                <option value="candidate_led">candidate_led</option>
                <option value="stress_test">stress_test</option>
              </select>
            </label>
          </div>

          <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
            <button
              className="btn-primary"
              type="button"
              onClick={startPractice}
              disabled={loading}
            >
              {loading ? "Loading..." : "Start practice"}
            </button>
            <button className="btn-secondary" type="button" onClick={backToHome}>
              Back to Home
            </button>
          </div>

          {error && (
            <div style={{ marginTop: 12, color: "#fb7185" }}>{error}</div>
          )}
        </section>
      )}

      {/* Step 2: practice loop */}
      {step === "practice" && currentQuestion && (
        <section className="card">
          <h2 className="section-title">Practice Interview</h2>

          <p style={{ marginBottom: 8 }}>
            Question {index + 1} of {questions.length}
          </p>

          <div
            style={{
              padding: 12,
              borderRadius: 12,
              border: "1px solid rgba(148,163,184,0.4)",
              marginBottom: 12,
              background: "rgba(15,23,42,0.9)",
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 6 }}>
              {currentQuestion.question_text}
            </div>
            <div style={{ fontSize: 13, color: "#9ca3af" }}>
              Role: {currentQuestion.role} • Style: {currentQuestion.style} •
              Difficulty: {currentQuestion.difficulty}
            </div>
          </div>

          <textarea
            rows={8}
            style={{ width: "100%", borderRadius: 10, padding: 10 }}
            value={currentAnswer}
            onChange={(e) => setCurrentAnswer(e.target.value)}
            placeholder="Type your answer here (or read it out while watching your notes)."
          />

          <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
            {index > 0 && (
              <button
                className="btn-secondary"
                type="button"
                onClick={handlePrevious}
                disabled={evaluating}
              >
                Previous
              </button>
            )}
            <button
              className="btn-primary"
              type="button"
              onClick={handleNext}
              disabled={evaluating}
            >
              {index + 1 >= questions.length ? "Finish & see summary" : "Next"}
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={backToHome}
              disabled={evaluating}
            >
              End session
            </button>
          </div>

          {evaluating && (
            <div style={{ marginTop: 10, color: "#93c5fd" }}>
              Evaluating answer with the AI brain…
            </div>
          )}
          {evalError && (
            <div style={{ marginTop: 10, color: "#fb7185" }}>{evalError}</div>
          )}

          {/* 🔹 Live feedback for current question */}
          {currentFeedback && (
            <div className="feedback-panel">
              <h3 className="section-title" style={{ marginBottom: 8 }}>
                AI Feedback
              </h3>
              <div className="feedback-scores">
                <span className="feedback-chip">
                  Clarity: {currentFeedback.clarity_score}/10
                </span>
                <span className="feedback-chip">
                  Depth: {currentFeedback.depth_score}/10
                </span>
                <span className="feedback-chip">
                  Structure: {currentFeedback.structure_score}/10
                </span>
                <span className="feedback-chip">
                  Relevance: {currentFeedback.relevance_score}/10
                </span>
                <span className="feedback-chip">
                  Seniority: {currentFeedback.seniority_signal_score}/10
                </span>
              </div>

              {currentFeedback.strengths && currentFeedback.strengths.length > 0 && (
                <>
                  <strong>Strengths:</strong>
                  <ul>
                    {currentFeedback.strengths.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </>
              )}

              {currentFeedback.gaps && currentFeedback.gaps.length > 0 && (
                <>
                  <strong>Gaps / Missing pieces:</strong>
                  <ul>
                    {currentFeedback.gaps.map((g, i) => (
                      <li key={i}>{g}</li>
                    ))}
                  </ul>
                </>
              )}

              {currentFeedback.improvement_tip && (
                <p>
                  <strong>Improvement tip:</strong>{" "}
                  {currentFeedback.improvement_tip}
                </p>
              )}

              {currentFeedback.follow_up_questions &&
                currentFeedback.follow_up_questions.length > 0 && (
                  <>
                    <strong>Follow-up questions to drill:</strong>
                    <ul>
                      {currentFeedback.follow_up_questions.map((fq, i) => (
                        <li key={i}>{fq}</li>
                      ))}
                    </ul>
                  </>
                )}
            </div>
          )}
        </section>
      )}

      {/* Step 3: summary */}
      {step === "summary" && (
        <section className="card">
          <h2 className="section-title">Session Summary</h2>

          <p style={{ marginBottom: 16 }}>
            Review your answers and the AI feedback for each question.
          </p>

          {questions.map((q, i) => {
            const fb = feedback[i];
            return (
              <div
                key={q.id ?? i}
                style={{
                  marginBottom: 18,
                  paddingBottom: 18,
                  borderBottom:
                    i === questions.length - 1
                      ? "none"
                      : "1px solid rgba(148,163,184,0.3)",
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 6 }}>
                  {i + 1}. {q.question_text}
                </div>
                <div
                  style={{
                    whiteSpace: "pre-wrap",
                    background: "rgba(15,23,42,0.9)",
                    padding: 8,
                    borderRadius: 8,
                    marginBottom: 8,
                  }}
                >
                  {answers[i] || "(no answer recorded)"}
                </div>

                {fb ? (
                  <div className="feedback-panel">
                    <div className="feedback-scores">
                      <span className="feedback-chip">
                        Clarity: {fb.clarity_score}/10
                      </span>
                      <span className="feedback-chip">
                        Depth: {fb.depth_score}/10
                      </span>
                      <span className="feedback-chip">
                        Structure: {fb.structure_score}/10
                      </span>
                      <span className="feedback-chip">
                        Relevance: {fb.relevance_score}/10
                      </span>
                      <span className="feedback-chip">
                        Seniority: {fb.seniority_signal_score}/10
                      </span>
                    </div>
                    {fb.improvement_tip && (
                      <p style={{ marginTop: 6 }}>
                        <strong>Key tip:</strong> {fb.improvement_tip}
                      </p>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: "#9ca3af" }}>
                    (No AI feedback stored for this question.)
                  </div>
                )}
              </div>
            );
          })}

          <button className="btn-primary" type="button" onClick={backToHome}>
            Back to Home
          </button>
        </section>
      )}
    </div>
  );
}


export default App;
