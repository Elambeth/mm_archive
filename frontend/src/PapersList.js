import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Search, AlertCircle } from 'lucide-react';

const PapersList = () => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchPapers = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/papers');
        if (!response.ok) {
          throw new Error('Failed to fetch papers');
        }
        const data = await response.json();
        setPapers(data.papers);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPapers();
  }, []);

  const handleViewPaper = (paper) => {
    navigate(`/paper/${paper.id}`, {
      state: {
        paperInfo: {
          title: paper.title,
          year: paper.year,
          page: 1,
          id: paper.id,
          filename: paper.filename
        }
      }
    });
  };

  const filteredPapers = papers.filter(paper =>
    paper.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    paper.year.toString().includes(searchTerm)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen text-red-500">
        <AlertCircle className="mr-2" />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Research Papers</h1>
        <p className="text-gray-600">Browse Michael Mauboussin's research papers</p>
      </div>

      <div className="relative mb-6">
        <input
          type="text"
          placeholder="Search papers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full p-3 pl-10 border rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <Search className="absolute left-3 top-3.5 text-gray-400" size={20} />
      </div>

      <div className="space-y-4">
        {filteredPapers.map((paper) => (
          <div
            key={paper.id}
            onClick={() => handleViewPaper(paper)}
            className="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <BookOpen className="flex-shrink-0 mt-1 mr-4 text-blue-500" size={24} />
            <div>
              <h2 className="text-xl font-semibold mb-1">{paper.title}</h2>
              <p className="text-gray-600">{paper.year}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PapersList;