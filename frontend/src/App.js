// frontend/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MauboussinGPT from './MauboussinGPT';
import PaperViewer from './PaperViewer';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MauboussinGPT />} />
        <Route path="/paper/:id" element={<PaperViewer />} />
      </Routes>
    </Router>
  );
}

export default App;