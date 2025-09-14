import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';

// When you deploy, replace the production URL with your actual backend URL.
// Consider free-tier services like Supabase, ElephantSQL, or Railway for a permanent database.
const API_URL = process.env.NODE_ENV === 'production' ? 'https://react-inventory-app-xqv1.onrender.com/api' : 'http://localhost:5001/api'; // Using Render for the backend

function ItemDetails() {
    const { itemCode } = useParams();
    const navigate = useNavigate();
    const [item, setItem] = useState(null);
    const [loading, setLoading] = useState(true);
    const [imageFile, setImageFile] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchItemDetails = async () => {
            try {
                setLoading(true);
                const response = await fetch(`${API_URL}/items/${itemCode}`);
                if (!response.ok) {
                    if (response.status === 404) throw new Error('Item not found');
                    throw new Error('Failed to fetch item details');
                }
                const data = await response.json();
                setItem(data);
            } catch (e) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };
        fetchItemDetails();
    }, [itemCode]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setItem(prev => ({ ...prev, [name]: value }));
    };

    const handleUpdate = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('data', JSON.stringify(item));
        if (imageFile) {
            formData.append('image_file', imageFile);
        }

        try {
            const response = await fetch(`${API_URL}/items/${itemCode}`, {
                method: 'PUT',
                body: formData,
            });
            if (!response.ok) {
                throw new Error('Failed to update item');
            }
            alert('Item updated successfully!');
            navigate('/');
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const handleDelete = async () => {
        if (window.confirm(`Are you sure you want to delete item ${item.item_code}?`)) {
            try {
                const response = await fetch(`${API_URL}/items/${itemCode}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete item');
                alert('Item deleted successfully!');
                navigate('/');
            } catch (err) {
                alert(`Error: ${err.message}`);
            }
        }
    };

    if (loading) return <div className="text-center mt-5">Loading item details...</div>;
    if (error) return <div className="alert alert-danger mt-4">{error}</div>;
    if (!item) return <div className="alert alert-warning mt-4">Item not found.</div>;

    return (
        <div>
            <nav aria-label="breadcrumb">
                <ol className="breadcrumb">
                    <li className="breadcrumb-item"><Link to="/">Dashboard</Link></li>
                    <li className="breadcrumb-item active" aria-current="page">{item.item_code}</li>
                </ol>
            </nav>
            <div className="card p-4" style={{ maxWidth: '600px', margin: 'auto' }}>
                <h2>Edit Item: {item.item_name}</h2>
                {item.image_filename && (
                    <div className="text-center mb-3">
                        <img src={item.image_filename} alt={item.item_name} style={{ maxWidth: '200px', maxHeight: '200px', objectFit: 'cover', borderRadius: '0.25rem' }} />
                    </div>
                )}
                <form onSubmit={handleUpdate}>
                    <div className="mb-3"><label className="form-label">Item Code</label><input type="text" className="form-control" value={item.item_code} readOnly disabled /></div>
                    <div className="mb-3"><label htmlFor="item_name" className="form-label">Item Name</label><input type="text" className="form-control" id="item_name" name="item_name" value={item.item_name} onChange={handleInputChange} required /></div>
                    <div className="mb-3"><label htmlFor="rack_no" className="form-label">Rack Number</label><input type="text" className="form-control" id="rack_no" name="rack_no" value={item.rack_no} onChange={handleInputChange} required /></div>
                    <div className="mb-3"><label htmlFor="quantity" className="form-label">Quantity</label><input type="number" className="form-control" id="quantity" name="quantity" value={item.quantity} onChange={handleInputChange} min="0" /></div>
                    <div className="mb-3"><label htmlFor="description" className="form-label">Description</label><textarea className="form-control" id="description" name="description" value={item.description || ''} onChange={handleInputChange} rows="3"></textarea></div>
                    <div className="mb-3">
                        <label htmlFor="image_file" className="form-label">Update Image</label>
                        <input type="file" className="form-control" id="image_file" name="image_file" accept="image/*" onChange={(e) => setImageFile(e.target.files[0])} />
                    </div>
                    <div className="d-flex justify-content-between">
                        <button type="submit" className="btn btn-success">Save Changes</button>
                        <button type="button" className="btn btn-danger" onClick={handleDelete}>Delete Item</button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default ItemDetails;