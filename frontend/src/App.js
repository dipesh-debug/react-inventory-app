import React from 'react';
// Import Outlet for nested routing
import { Route, Routes, Link, Outlet } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';


import Dashboard from './components/Dashboard';
import ItemDetails from './components/ItemDetails';

// Define a Layout component that contains the shared UI (header)
// and an <Outlet> for the child routes to render into.
function Layout() {
  return (
    <div className="container-fluid py-4">
      <h1 className="mb-4">
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          Inventory Management System
        </Link>
      </h1>
      <Outlet />
    </div>
  );
}

function App() {
  return (
    // The <Routes> component now defines a parent layout route
    // and nests all other pages inside it.
    <Routes>
      <Route path="/" element={<Layout />}>
        {/* The `index` route renders when the URL matches the parent's path exactly ("/") */}
        <Route index element={<Dashboard />} />
        {/* Other routes are relative to the parent */}
        <Route path="item/:itemCode" element={<ItemDetails />} />
        {/* The catch-all route will also render inside the Layout */}
        <Route path="*" element={<div className="text-center mt-5"><h2>404: Page Not Found</h2></div>} />
      </Route>
    </Routes>
  );
}

export default App;