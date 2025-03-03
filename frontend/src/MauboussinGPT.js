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
  const [loadingMessage, setLoadingMessage] = useState('');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const lastQuestion = localStorage.getItem("lastquestion");
    const lastAnswer = localStorage.getItem("lastanswer");
    if (lastQuestion && lastAnswer) {
      setQuery(lastQuestion);
      setResponse(JSON.parse(lastAnswer));
    }
  }, []);

  const loadingMessages = [
    "Rifling through Mauboussin's filing cabinet...",
    "Consulting with the capital allocation experts...",
    "Calculating optimal ROIC strategies...",
    "Distinguishing skill from luck...",
    "Analyzing competitive advantage periods...",
    "Examining the expectations infrastructure...",
    "Checking what the market might be missing...",
    "Contemplating base rates and mental models...",
    "Exploring the success equation...",
    "Considering the outside view...",
    "Pondering mean reversion principles...",
    "Studying the paradox of skill..."
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);
    //setProgress(25);
    setLoadingMessage(loadingMessages[0]);
      // Initialize loading animation
      const messageInterval = setInterval(() => {
        setLoadingMessage(prev => {
          const currentIndex = loadingMessages.indexOf(prev);
          const nextIndex = (currentIndex + 1) % loadingMessages.length;
          return loadingMessages[nextIndex];
        });
      
      // Update progress bar (goes from 0 to 95% while waiting)
      setProgress(prev => {
        // Larger random increments between 10-20%
        const increment = 10 + Math.random() * 10;
        // Cap at 90% until we complete
        return Math.min(prev + increment, 90);
      });
    }, 2000); // Every 2 seconds
    

    try {
      // REMOVE THE LOCAL HOST PART BEFORE BUILDING
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
      
      // When complete, set progress to 100%
      setProgress(100);
      
    } catch (err) {
      setError(err.message || 'Failed to get response. Please try again.');
      setResponse(null);
    } finally {
      clearInterval(messageInterval);
      setLoading(false);
      // Reset after a short delay to show 100% completion
      setTimeout(() => {
        setProgress(0);
        setLoadingMessage('');
      }, 500);
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
            <div style={{
              width: '100%',
              maxWidth: '800px',
              margin: '30px auto',
              padding: '20px',
              backgroundColor: 'white',
              borderRadius: '10px',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
              textAlign: 'center'
            }}>
              <div style={{
                height: '10px',
                width: '100%',
                backgroundColor: '#e0e0e0',
                borderRadius: '5px',
                overflow: 'hidden',
                marginBottom: '20px'
              }}>
                <div style={{
                  height: '100%',
                  width: `${progress}%`,
                  backgroundColor: '#4e54c8',
                  borderRadius: '5px',
                  transition: 'width 0.5s ease'
                }}></div>
              </div>
              <p style={{
                fontSize: '18px',
                fontWeight: '500',
                color: '#333',
                fontStyle: 'italic',
                margin: '0'
              }}>
                {loadingMessage || "Processing your request..."}
              </p>
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