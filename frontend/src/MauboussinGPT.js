import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, BookOpen, AlertCircle, Home, ChevronLeft, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './MauboussinGPT.css';

const MauboussinGPT = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const lastQuestion = localStorage.getItem("lastquestion");
    const lastAnswer = localStorage.getItem("lastanswer");
    if (lastQuestion && lastAnswer) {
      setQuery(lastQuestion);
      setResponse(JSON.parse(lastAnswer));
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      
      if (!res.ok) {
        throw new Error(`API responded with status: ${res.status}`);
      }

      const data = await res.json();
      setResponse(data);
      localStorage.setItem("lastquestion", query);
      localStorage.setItem("lastanswer", JSON.stringify(data));
      
    } catch (err) {
      setError(err.message || 'Failed to get response. Please try again.');
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const handleViewPDF = (source) => {
    navigate(`/paper/${source.id}`, { 
      state: { 
        paperInfo: {
          title: source.title,
          year: source.year,
          page: source.page,
          tags: source.tags,
          id: source.id,
          filename: source.filename
        }
      }
    });
  };

  const handleReset = () => {
    setQuery('');
    setResponse(null);
    setError(null);
    localStorage.removeItem("lastquestion");
    localStorage.removeItem("lastanswer");
  };

  return (
    <div className="app-container">
      <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <button 
          className="sidebar-toggle"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        >
          {isSidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
        {isSidebarOpen && (
          <div className="sidebar-content">
            <button 
              onClick={handleReset}
              className="home-button"
            >
              <Home size={20} />
              <span>New Search</span>
            </button>
            {/* Add more sidebar content here */}
          </div>
        )}
      </div>

      <div className={`main-content ${isSidebarOpen ? 'with-sidebar' : ''}`}>
        <div className="container">
          <div className="header">
            <h1>Mauboussin GPT</h1>
            <p>Ask questions about Michael Mauboussin's research papers and get AI-powered answers with citations</p>
          </div>

          <form onSubmit={handleSubmit} className="search-form">
            <div className="search-container">
              <div className="search-input-container">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="What does Mauboussin say about ROIC?"
                  disabled={loading}
                />
                <Search className="search-icon" size={20} />
              </div>
              <button type="submit" disabled={loading || !query.trim()}>
                {loading ? 'Searching...' : 'Ask'}
              </button>
            </div>
          </form>

          {error && (
            <div className="error-message">
              <AlertCircle size={20} />
              <p>{error}</p>
            </div>
          )}

          {response && response.answer && (
            <div className="results">
              <div className="result-card">
                <h2>Answer</h2>
                <div className="answer-content">
                  <ReactMarkdown>
                    {response.answer}
                  </ReactMarkdown>
                </div>
              </div>

              {response.sources && response.sources.length > 0 && (
                <div className="result-card">
                  <h2>Sources</h2>
                  <div className="sources-list">
                    {response.sources.map((source, i) => (
                      <div key={i} className="source-item">
                        <div className="source-content">
                          <BookOpen size={20} />
                          <div>
                            <h3>{source.title} ({source.year})</h3>
                            <button 
                              onClick={() => handleViewPDF(source)}
                              className="page-link"
                            >
                              View Page {source.page} →
                            </button>
                            {source.excerpt && (
                              <div className="excerpt">
                                <ReactMarkdown>
                                  {source.excerpt}
                                </ReactMarkdown>
                              </div>
                            )}
                            {source.tags && (
                              <div className="tags-container">
                                {source.tags.map((tag, index) => (
                                  <span key={index} className="tag">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MauboussinGPT;