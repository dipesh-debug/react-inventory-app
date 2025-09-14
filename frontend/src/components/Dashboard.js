import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';

// The URL for your Python backend API
const API_URL = process.env.NODE_ENV === 'production' ? 'https://react-inventory-app-xqv1.onrender.com/api' : 'http://localhost:5001/api';

function Dashboard() {
    // Data and loading state
    const [inventoryData, setInventoryData] = useState({ items: [], totalPages: 1, currentPage: 1 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    // Filter and Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [filterName, setFilterName] = useState('');
    const [filterDate, setFilterDate] = useState('');
    const [allItemNames, setAllItemNames] = useState([]);

    // Live search state
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);

    // Form state
    const [newItem, setNewItem] = useState({
        item_code: '',
        item_name: '',
        rack_no: '',
        quantity: 0,
        description: ''
    });
    const [imageFile, setImageFile] = useState(null);

    // Fetch items from the API
    const fetchItems = useCallback(async (page, name, date) => {
        try {
            setLoading(true);
            const params = new URLSearchParams({ page });
            if (name) {
                params.append("name", name);
            }
            if (date) {
                params.append("date", date);
                // Send client's timezone offset in minutes.
                // It's the difference between UTC time and local time.
                // e.g., for UTC+5:30, the offset is -330.
                params.append("tzOffset", new Date().getTimezoneOffset());
            }
            const response = await fetch(`${API_URL}/items?${params.toString()}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setInventoryData(data);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchItems(currentPage, filterName, filterDate);
    }, [currentPage, filterName, filterDate, fetchItems]);

    // Fetch all unique item names for the filter dropdown
    useEffect(() => {
        const fetchNames = async () => {
            try {
                const response = await fetch(`${API_URL}/item-names`);
                const data = await response.json();
                setAllItemNames(data);
            } catch (err) {
                console.error("Failed to fetch item names:", err);
            }
        };
        fetchNames();
    }, []);

    // Effect for live search
    useEffect(() => {
        if (searchQuery.length < 2) {
            setSearchResults([]);
            return;
        }
        const fetchSearchResults = async () => {
            const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(searchQuery)}`);
            const data = await response.json();
            setSearchResults(data);
        };
        const debounce = setTimeout(() => fetchSearchResults(), 300);
        return () => clearTimeout(debounce);
    }, [searchQuery]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setNewItem(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('data', JSON.stringify(newItem));
        if (imageFile) {
            formData.append('image_file', imageFile);
        }

        try {
            const response = await fetch(`${API_URL}/items`, {
                method: 'POST',
                body: formData, // Let the browser set the Content-Type for FormData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to add item');
            }

            // Refresh the list, clear the form, and reset filters to see the new item
            setFilterName('');
            setFilterDate('');
            if (currentPage === 1) {
                fetchItems(1, '', '');
            } else {
                setCurrentPage(1);
            }
            setNewItem({ item_code: '', item_name: '', rack_no: '', quantity: 0, description: '' });
            setImageFile(null);
            // Reset file input visually
            if (document.getElementById('image_file')) {
                document.getElementById('image_file').value = '';
            }
            alert('Item added successfully!');

        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const handleFilterSubmit = (e) => {
        e.preventDefault();
        setCurrentPage(1); // Reset to first page on new filter
        fetchItems(1, filterName, filterDate);
    };

    const clearFilters = () => {
        setFilterName('');
        setFilterDate('');
        setCurrentPage(1);
    };

    if (loading) return <div className="container mt-4">Loading inventory...</div>;
    if (error) return <div className="container mt-4 alert alert-danger">Error: {error}</div>;

    return (
        <div className="row">
            {/* Form Column */}
            <div className="col-md-4">
                <div className="card p-4">
                    <h2>Add New Item</h2>
                    <form onSubmit={handleSubmit}>
                        <div className="mb-3"><label htmlFor="item_code" className="form-label">Item Code</label><input type="text" className="form-control" id="item_code" name="item_code" value={newItem.item_code} onChange={handleInputChange} required /></div>
                        <div className="mb-3"><label htmlFor="item_name" className="form-label">Item Name</label><input type="text" className="form-control" id="item_name" name="item_name" value={newItem.item_name} onChange={handleInputChange} required /></div>
                        <div className="mb-3"><label htmlFor="rack_no" className="form-label">Rack Number</label><input type="text" className="form-control" id="rack_no" name="rack_no" value={newItem.rack_no} onChange={handleInputChange} required /></div>
                        <div className="mb-3"><label htmlFor="quantity" className="form-label">Initial Quantity</label><input type="number" className="form-control" id="quantity" name="quantity" value={newItem.quantity} onChange={handleInputChange} min="0" /></div>
                        <div className="mb-3"><label htmlFor="description" className="form-label">Description</label><textarea className="form-control" id="description" name="description" value={newItem.description} onChange={handleInputChange} rows="3"></textarea></div>
                        <div className="mb-3"><label htmlFor="image_file" className="form-label">Item Image</label><input type="file" className="form-control" id="image_file" name="image_file" accept="image/*" onChange={(e) => setImageFile(e.target.files[0])} /></div>
                        <button type="submit" className="btn btn-primary w-100">Add Item</button>
                    </form>
                </div>
            </div>

            {/* Table Column */}
            <div className="col-md-8">
                {/* Filter Form */}
                <div className="card mb-4">
                    <div className="card-body">
                        <h5 className="card-title">Filters</h5>
                        <form onSubmit={handleFilterSubmit} className="row align-items-end">
                            <div className="col-md-5">
                                <label htmlFor="filter_item_name" className="form-label">Item Name</label>
                                <select className="form-select" id="filter_item_name" value={filterName} onChange={(e) => setFilterName(e.target.value)}>
                                    <option value="">All Items</option>
                                    {allItemNames.map(name => <option key={name} value={name}>{name}</option>)}
                                </select>
                            </div>
                            <div className="col-md-5">
                                <label htmlFor="filter_date" className="form-label">Created Date</label>
                                <input type="date" className="form-control" id="filter_date" value={filterDate} onChange={(e) => setFilterDate(e.target.value)} />
                            </div>
                            <div className="col-md-2 d-flex">
                                <button type="submit" className="btn btn-info w-100 me-2">Filter</button>
                                <button type="button" onClick={clearFilters} className="btn btn-secondary w-100">Clear</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div className="card p-4">
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <h2>Current Inventory</h2>
                        <div className="position-relative w-50">
                            <input
                                type="text"
                                className="form-control"
                                placeholder="🔍 Live search for an item..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onBlur={() => setTimeout(() => setSearchResults([]), 200)}
                            />
                            {searchResults.length > 0 && (
                                <div className="list-group position-absolute w-100" style={{ zIndex: 1000 }}>
                                    {searchResults.map(item => (
                                        <Link key={item.item_code} to={`/item/${item.item_code}`} className="list-group-item list-group-item-action">
                                            <div className="fw-bold">{item.item_code}</div>
                                            <div>{item.item_name}</div>
                                            <div className="small text-muted">{item.description}</div>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="table-responsive">
                        <table className="table table-hover" style={{ cursor: 'pointer', verticalAlign: 'middle' }}>
                            <thead>
                                <tr>
                                    <th scope="col">Image</th><th scope="col">Item Code</th><th scope="col">Item Name</th><th scope="col">Rack No.</th><th scope="col">Quantity</th><th scope="col">Created At</th>
                                </tr>
                            </thead>
                            <tbody>
                                {inventoryData.items.length > 0 ? (
                                    inventoryData.items.map(item => (
                                        <tr key={item.id} onClick={() => navigate(`/item/${item.item_code}`)}>
                                            <td>
                                                {item.image_filename ? (
                                                    <img src={item.image_filename} alt={item.item_name} style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '0.25rem' }} />
                                                ) : (
                                                    <div style={{ width: '60px', height: '60px', backgroundColor: '#f0f0f0', borderRadius: '0.25rem' }} />
                                                )}
                                            </td>
                                            <td>{item.item_code}</td><td>{item.item_name}</td><td>{item.rack_no}</td><td>{item.quantity}</td><td>{new Date(item.created_at).toLocaleDateString()}</td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr><td colSpan="6" className="text-center">No items match the current filters.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                    {/* Pagination */}
                    {inventoryData.totalPages > 1 && (
                        <nav className="mt-3">
                            <ul className="pagination justify-content-center">
                                <li className={`page-item ${inventoryData.currentPage <= 1 ? 'disabled' : ''}`}>
                                    <button className="page-link" onClick={() => setCurrentPage(p => p - 1)}>Previous</button>
                                </li>
                                <li className="page-item disabled"><span className="page-link">Page {inventoryData.currentPage} of {inventoryData.totalPages}</span></li>
                                <li className={`page-item ${inventoryData.currentPage >= inventoryData.totalPages ? 'disabled' : ''}`}>
                                    <button className="page-link" onClick={() => setCurrentPage(p => p + 1)}>Next</button>
                                </li>
                            </ul>
                        </nav>
                    )}
                </div>
            </div>
        </div>
    );
}


export default Dashboard;
