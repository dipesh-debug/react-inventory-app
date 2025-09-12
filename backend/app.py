import os
import psycopg2
import json
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__)
# Allow requests from your React development server (e.g., http://localhost:3000)
CORS(app) # This is a simpler, more global configuration that is often more reliable.
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DB_URL = "postgresql://inventory_user:inventory_password@localhost:5433/inventory_db" # Use port 5433 for Docker

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Creates a connection to the PostgreSQL database."""
    conn = psycopg2.connect(DB_URL)
    return conn

def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            item_code TEXT NOT NULL UNIQUE,
            item_name TEXT NOT NULL,
            rack_no TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            image_filename TEXT,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized successfully.")

# --- API Routes ---

@app.route('/api/items', methods=['GET'])
def get_items():
    """Endpoint to get a paginated and filtered list of items for the main table."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get filter parameters from URL
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    filter_item_name = request.args.get('name', '')
    filter_date = request.args.get('date', '')
    tz_offset_minutes_str = request.args.get('tzOffset')

    # Build query dynamically to handle filters
    query_params = []
    where_clauses = []

    if filter_item_name:
        where_clauses.append("item_name = %s")
        query_params.append(filter_item_name)
    
    if filter_date:
        if tz_offset_minutes_str:
            try:
                # JS getTimezoneOffset is inverted. For UTC+5:30, it's -330.
                # We want to add 5.5 hours to the UTC time to get local time.
                # So we add -(-330) = 330 minutes.
                tz_offset_minutes = int(float(tz_offset_minutes_str))
                where_clauses.append("date(created_at + (%s * interval '1 minute')) = TO_DATE(%s, 'YYYY-MM-DD')")
                query_params.extend([-tz_offset_minutes, filter_date])
            except (ValueError, TypeError):
                # Fallback if tzOffset is not a valid integer
                where_clauses.append("date(created_at AT TIME ZONE 'UTC') = TO_DATE(%s, 'YYYY-MM-DD')")
                query_params.append(filter_date)
        else:
            where_clauses.append("date(created_at AT TIME ZONE 'UTC') = TO_DATE(%s, 'YYYY-MM-DD')")
            query_params.append(filter_date)

    base_query = "FROM items"
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    # Get total count for pagination calculation
    total_items_query = "SELECT COUNT(id) as count " + base_query
    cur.execute(total_items_query, query_params)
    total_items = cur.fetchone()['count']
    total_pages = (total_items + per_page - 1) // per_page

    # Get items for the current page
    offset = (page - 1) * per_page
    items_query = "SELECT * " + base_query + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    paged_query_params = query_params + [per_page, offset]
    cur.execute(items_query, paged_query_params)
    items = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify({
        'items': items,
        'currentPage': page,
        'totalPages': total_pages,
    })

@app.route('/api/items', methods=['POST'])
def add_item():
    """Endpoint to add a new item."""
    if 'data' not in request.form:
        return jsonify({'error': 'Missing data part in form'}), 400

    try:
        data = json.loads(request.form['data'])
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in data part'}), 400

    image_file = request.files.get('image_file')
    image_filename = None

    if image_file and allowed_file(image_file.filename):
        # Create a secure filename
        image_filename = f"{data.get('item_code', 'new_item')}_{image_file.filename}".replace(" ", "_")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image_file.save(image_path)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            'INSERT INTO items (item_code, item_name, rack_no, quantity, description, image_filename) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *',
            (data['item_code'], data['item_name'], data['rack_no'], data['quantity'], data['description'], image_filename)
        )
        new_item = cur.fetchone()
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': f"Item code '{data['item_code']}' already exists."}), 409 # Conflict
    finally:
        cur.close()
        conn.close()

    return jsonify(new_item), 201

@app.route('/api/items/<item_code>', methods=['GET'])
def get_item_details(item_code):
    """Endpoint to get details for a single item."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM items WHERE item_code = %s', (item_code,))
    item = cur.fetchone()
    cur.close()
    conn.close()
    if item is None:
        abort(404)
    return jsonify(item)

@app.route('/api/items/<item_code>', methods=['PUT'])
def update_item(item_code):
    """Endpoint to update an existing item."""
    if 'data' not in request.form:
        return jsonify({'error': 'Missing data part in form'}), 400

    try:
        data = json.loads(request.form['data'])
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in data part'}), 400

    image_file = request.files.get('image_file')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Handle image update
    if image_file and allowed_file(image_file.filename):
        image_filename = f"{item_code}_{image_file.filename}".replace(" ", "_")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image_file.save(image_path)
        # Update the image filename in the database
        cur.execute('UPDATE items SET image_filename = %s WHERE item_code = %s', (image_filename, item_code))

    # Update other fields
    cur.execute(
        'UPDATE items SET item_name = %s, rack_no = %s, quantity = %s, description = %s WHERE item_code = %s RETURNING *',
        (data['item_name'], data['rack_no'], data['quantity'], data['description'], item_code)
    )

    updated_item = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if updated_item is None:
        abort(404)
    return jsonify(updated_item)

@app.route('/api/items/<item_code>', methods=['DELETE'])
def delete_item(item_code):
    """Endpoint to delete an item."""
    conn = get_db_connection()
    # First, get the image filename to delete the file
    cur = conn.cursor()
    cur.execute('SELECT image_filename FROM items WHERE item_code = %s', (item_code,))
    item = cur.fetchone()

    # Now, delete the record from the database
    cur = conn.cursor()
    cur.execute('DELETE FROM items WHERE item_code = %s RETURNING id', (item_code,))
    deleted_item = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if deleted_item is None:
        abort(404)

    # If deletion was successful, delete the associated image file
    if item and item[0]:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], item[0])
        if os.path.exists(image_path):
            os.remove(image_path)

    return jsonify({'message': f"Item '{item_code}' deleted successfully."}), 200

@app.route('/api/search', methods=['GET'])
def search_items():
    """Endpoint for live search popup."""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    search_term = f"%{query}%"
    cur.execute(
        'SELECT item_code, item_name, description FROM items WHERE item_code ILIKE %s OR item_name ILIKE %s LIMIT 5',
        (search_term, search_term)
    )
    items = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(items)

@app.route('/api/item-names', methods=['GET'])
def get_item_names():
    """Endpoint to get all unique item names for filter dropdown."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT DISTINCT item_name FROM items ORDER BY item_name')
    names = [row['item_name'] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(names)

@app.route('/api/uploads/<path:filename>')
def serve_upload(filename):
    """Serves an uploaded file."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Main Execution ---
if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    init_db()
    # Note: debug=True is not for production
    app.run(host='0.0.0.0', port=5001, debug=True)