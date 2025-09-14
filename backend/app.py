import os
import psycopg2
import json
import re
import uuid
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import cloudinary.api

# --- Configuration ---
app = Flask(__name__)
CORS(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DB_URL = os.environ.get('DB_URL', "postgresql://inventory_user:inventory_password@localhost:5433/inventory_db")
# Cloudinary is configured automatically by the CLOUDINARY_URL environment variable.

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_cloudinary(file):
    """Uploads a file to Cloudinary and returns its secure URL."""
    if not file or file.filename == '' or not allowed_file(file.filename):
        return None
    
    # The upload method returns a dictionary with upload details
    upload_result = cloudinary.uploader.upload(file)
    # We need the secure_url to display the image
    return upload_result.get('secure_url')

def delete_from_cloudinary(secure_url):
    """Deletes a file from Cloudinary given its secure URL."""
    if not secure_url:
        return
    try:
        # Extract public_id from URL.
        # e.g. from "https://res.cloudinary.com/demo/image/upload/v1606312345/folder/sample.jpg"
        # we need to get "folder/sample"
        match = re.search(r'\/v\d+\/(.+?)(?:\.\w+)?$', secure_url)
        if not match:
            print(f"Could not extract public_id from Cloudinary URL: {secure_url}")
            return
        
        public_id = match.group(1)
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Error deleting from Cloudinary: {e}") # Log error but don't fail the request

def get_db_connection():
    """Creates a connection to the PostgreSQL database."""
    conn = psycopg2.connect(DB_URL)
    return conn

def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    try:
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
    except psycopg2.OperationalError as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! DATABASE CONNECTION FAILED ON STARTUP.                             !!!")
        print("!!! This is likely a network issue (e.g., IPv6) between Render and your DB. !!!")
        print("!!! If using Supabase, try using the Connection Pooler URL (port 6543).  !!!")
        print(f"!!! Error: {e}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # Re-raise the exception to ensure the app still fails to start
        raise e

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

    image_url = None
    if 'image_file' in request.files:
        image_file = request.files['image_file']
        try:
            image_url = upload_to_cloudinary(image_file)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # The `image_filename` column now stores the full Cloudinary URL or NULL
        cur.execute(
            'INSERT INTO items (item_code, item_name, rack_no, quantity, description, image_filename) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *',
            (data['item_code'], data['item_name'], data['rack_no'], data['quantity'], data['description'], image_url)
        )
        new_item = cur.fetchone()
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        # If DB insert fails, delete the orphaned image from Cloudinary
        if image_url:
            delete_from_cloudinary(image_url)
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

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if 'image_file' in request.files:
        image_file = request.files.get('image_file')
        try:
            # Get old image URL to delete it after new one is uploaded
            cur.execute('SELECT image_filename FROM items WHERE item_code = %s', (item_code,))
            old_item = cur.fetchone()
            old_image_url = old_item['image_filename'] if old_item else None

            # Upload new image and get its URL from Cloudinary
            new_image_url = upload_to_cloudinary(image_file)

            # Update DB with the new URL
            cur.execute('UPDATE items SET image_filename = %s WHERE item_code = %s', (new_image_url, item_code))

            # If upload and DB update were successful, delete the old image from Cloudinary
            if old_image_url:
                delete_from_cloudinary(old_image_url)
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500

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
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # First, get the image URL to delete the file from Cloudinary later
    cur.execute('SELECT image_filename FROM items WHERE item_code = %s', (item_code,))
    item = cur.fetchone()
    image_url_to_delete = item['image_filename'] if item and item['image_filename'] else None

    # Now, delete the record from the database
    cur.execute('DELETE FROM items WHERE item_code = %s RETURNING id', (item_code,))
    deleted_item = cur.fetchone()
    conn.commit()

    if deleted_item is None:
        cur.close()
        conn.close()
        abort(404)

    # If DB deletion was successful, delete the associated image file from Cloudinary
    if image_url_to_delete:
        delete_from_cloudinary(image_url_to_delete)

    cur.close()
    conn.close()
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

# Initialize the database when the application starts
init_db()

# --- Main Execution ---
if __name__ == '__main__':
    # Note: debug=True is not for production
    app.run(host='0.0.0.0', port=5001, debug=True)