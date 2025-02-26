import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Tag, ArrowLeft } from 'lucide-react';
import './PaperViewer.css';

const PaperViewer = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { paperInfo } = location.state || {};

  useEffect(() => {
    // Debug log to check what data we're receiving
    console.log('Paper Info:', paperInfo);
  }, [paperInfo]);

  if (!paperInfo || !paperInfo.filename) {
    console.error('Missing required paper info:', paperInfo);
    return (
      <div className="paper-viewer">
        <div className="paper-header">
          <button onClick={() => navigate(-1)} className="back-button">
            <ArrowLeft size={20} />
            Back to Search
          </button>
          <h1>Error: Missing Paper Information</h1>
        </div>
      </div>
    );
  }

  // Updated code
  const pdfUrl = `/pdfs/${encodeURIComponent(paperInfo.filename)}#page=${paperInfo.page}`;

  return (
    <div className="paper-viewer">
      <div className="paper-header">
        <button onClick={() => navigate(-1)} className="back-button">
          <ArrowLeft size={20} />
          Back to Search
        </button>
        <h1 className="title">{paperInfo.title}</h1>
        <p className="metadata">Michael Mauboussin • {paperInfo.year}</p>
        <div className="tags">
          {paperInfo.tags?.map((tag, index) => (
            <button key={index} className="tag">
              <Tag className="tag-icon" />
              {tag}
            </button>
          ))}
        </div>
      </div>
      
      <div className="pdf-container">
        <object
          data={pdfUrl}
          type="application/pdf"
          className="pdf-viewer"
        >
          <p>Unable to display PDF. <a href={pdfUrl} target="_blank" rel="noopener noreferrer">Download PDF</a></p>
        </object>
      </div>
    </div>
  );
};

export default PaperViewer;