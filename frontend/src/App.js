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
        <Route path="*" element={<div className="text-center mt-5"><h2>404: Page Not Found</h2></div>} />
      </Routes>
    </div>
  );
}

export default App;