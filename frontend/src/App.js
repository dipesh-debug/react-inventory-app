import React from 'react';
import { Route, Routes, Link } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';


import Dashboard from './components/Dashboard';
import ItemDetails from './components/ItemDetails';

function App() {
  return (
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
  );
}

export default App;