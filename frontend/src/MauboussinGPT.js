import React, { useState } from 'react';
import { Search, BookOpen, AlertCircle } from 'lucide-react';
import './MauboussinGPT.css';

const MauboussinGPT = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      console.log('Sending query:', query); // Debug log
      const res = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      
      if (!res.ok) {
        throw new Error(`API responded with status: ${res.status}`);
      }

      const data = await res.json();
      console.log('Received response:', data); // Debug log

      if (!data.answer) {
        throw new Error('Response is missing answer field');
      }

      setResponse(data);
    } catch (err) {
      console.error('Error:', err); // Debug log
      setError(err.message || 'Failed to get response. Please try again.');
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <h1>Mauboussin GPT</h1>
        <p>Ask questions about Michael Mauboussin's research papers and get AI-powered answers with citations</p>
      </div>

      {/* Search Form */}
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
          <button
            type="submit"
            disabled={loading || !query.trim()}
          >
            {loading ? 'Searching...' : 'Ask'}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <AlertCircle size={20} />
          <p>{error}</p>
        </div>
      )}

      {/* Results */}
      {response && response.answer && (
        <div className="results">
          {/* Answer */}
          <div className="result-card">
            <h2>Answer</h2>
            <div className="answer-content">
              {response.answer.split('\n').map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))}
            </div>
          </div>

          {/* Sources */}
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
                        <p className="page-number">Page {source.page}</p>
                        {source.excerpt && (
                          <p className="excerpt">{source.excerpt}</p>
                        )}
                        {source.url && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="pdf-link"
                          >
                            View PDF →
                          </a>
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
  );
};

export default MauboussinGPT;