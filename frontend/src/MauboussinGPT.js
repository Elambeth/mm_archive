import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, BookOpen, AlertCircle, Home, Menu, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './MauboussinGPT.css';

const MauboussinGPT = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
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
    setResponse(null);

    try {
      // This is the only line that changes
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || `API responded with status: ${res.status}`);
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
    setIsSidebarOpen(false);
  };

  return (
    <div className="app-container">
      {isSidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />
      )}
      
      <button className="mobile-menu-button" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
        {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-content">
          <div className="sidebar-header">
            <BookOpen className="sidebar-logo" size={32} />
            <span className="sidebar-title">MauboussinGPT</span>
          </div>

          <nav className="sidebar-nav">
            <button onClick={handleReset} className="nav-button">
              <Home size={24} />
              <span>New Search</span>
            </button>

            <button className="nav-button">
              <Search size={24} />
              <span>Recent Searches</span>
            </button>
          </nav>
        </div>
      </div>

      <div className="main-content">
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
                {loading ? 'Processing...' : 'Ask'}
              </button>
            </div>
          </form>
          
          {loading && (
            <div className="loading-indicator" style={{ textAlign: 'center', margin: '20px 0' }}>
              <p style={{ fontWeight: 'bold' }}>Processing your request...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <AlertCircle size={20} />
              <div>
                <p>{error}</p>
              </div>
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