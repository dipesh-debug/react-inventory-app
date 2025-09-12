import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';


import Dashboard from './components/Dashboard';
import ItemDetails from './components/ItemDetails';

function App() {
  return (
    <Router>
      <div className="container-fluid py-4">
        <h1 className="mb-4">
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            Inventory Management System
          </Link>
        </h1>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/item/:itemCode" element={<ItemDetails />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;