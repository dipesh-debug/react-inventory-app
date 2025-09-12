import psycopg2
import random
from datetime import datetime, timedelta
from app import init_db, get_db_connection # Import from the new backend app

def generate_sample_data():
    """Generates a list of over 100 sample inventory items."""
    
    now = datetime.now()
    # Add the user's specific examples first
    items = [
        {'item_code': 'TSH-RND-SLD-WHT-001', 'item_name': 'Round Neck T-Shirt', 'description': 'A classic 100% cotton crewneck t-shirt in solid white.', 'rack_no': 'R1-S1', 'quantity': 50, 'created_at': now - timedelta(days=1)},
        {'item_code': 'TSH-VNK-SLD-NVY-002', 'item_name': 'V-Neck T-Shirt', 'description': 'A soft-blend v-neck t-shirt in solid navy blue.', 'rack_no': 'R1-S2', 'quantity': 45, 'created_at': now - timedelta(days=2)},
        {'item_code': 'TKS-ZIP-CLR-BG-001', 'item_name': 'Zip-Up Tracksuit', 'description': 'A color-block tracksuit with a black zip-up jacket and grey pants.', 'rack_no': 'R10-S1', 'quantity': 20, 'created_at': now - timedelta(days=5)},
        {'item_code': 'JSY-SOC-MUL-RBW-001', 'item_name': 'Soccer Jersey', 'description': 'A performance jersey featuring a red body with blue and white accents.', 'rack_no': 'R15-S3', 'quantity': 30, 'created_at': now - timedelta(days=10)},
        {'item_code': 'TSH-RND-STR-BW-002', 'item_name': 'Round Neck T-Shirt', 'description': 'An everyday t-shirt with classic black and white horizontal stripes.', 'rack_no': 'R2-S1', 'quantity': 60, 'created_at': now - timedelta(days=15)},
        {'item_code': 'TSH-VNK-CLR-WG-003', 'item_name': 'V-Neck T-Shirt', 'description': 'A modern color-block v-neck with a white body and heather grey sleeves.', 'rack_no': 'R2-S2', 'quantity': 55, 'created_at': now - timedelta(days=20)},
        {'item_code': 'TKS-PLV-CLR-NB-002', 'item_name': 'Pullover Tracksuit', 'description': 'A comfortable fleece pullover hoodie and jogger set in navy and blue.', 'rack_no': 'R10-S2', 'quantity': 25, 'created_at': now - timedelta(days=25)},
        {'item_code': 'JSY-BSK-MUL-YPB-002', 'item_name': 'Basketball Jersey', 'description': 'A breathable mesh jersey with a yellow body, purple side panels, and black trim.', 'rack_no': 'R15-S4', 'quantity': 35, 'created_at': now - timedelta(days=30)},
        {'item_code': 'TSH-RND-GRH-BLK-003', 'item_name': 'Round Neck Graphic T-Shirt', 'description': 'A solid black t-shirt featuring a multi-color graphic on the chest.', 'rack_no': 'R3-S1', 'quantity': 70, 'created_at': now - timedelta(days=35)},
        {'item_code': 'TKS-ZIP-STR-GNW-003', 'item_name': 'Zip-Up Tracksuit', 'description': 'A forest green tracksuit with clean, white stripes down the arms and legs.', 'rack_no': 'R11-S1', 'quantity': 15, 'created_at': now - timedelta(days=40)},
    ]

    # Procedurally generate more items
    categories = {'TSH': 'T-Shirt', 'TKS': 'Tracksuit', 'JSY': 'Jersey'}
    styles = {
        'TSH': {'RND': 'Round Neck', 'VNK': 'V-Neck', 'PLO': 'Polo'},
        'TKS': {'ZIP': 'Zip-Up', 'PLV': 'Pullover'},
        'JSY': {'SOC': 'Soccer', 'BSK': 'Basketball'}
    }
    patterns = {'SLD': 'Solid', 'STR': 'Striped', 'GRH': 'Graphic', 'CLR': 'Color-Block'}
    colors = {'BLK': 'Black', 'WHT': 'White', 'NVY': 'Navy', 'RED': 'Red', 'GRY': 'Grey', 'BLU': 'Blue', 'GRN': 'Green'}

    existing_codes = {item['item_code'] for item in items}
    item_id_counter = len(items) + 1

    while len(items) < 120:
        cat_code = random.choice(list(categories.keys()))
        style_code = random.choice(list(styles[cat_code].keys()))
        pattern_code = random.choice(list(patterns.keys()))
        color_code = random.choice(list(colors.keys()))

        item_code = f"{cat_code}-{style_code}-{pattern_code}-{color_code}-{item_id_counter:03d}"
        if item_code in existing_codes:
            continue

        item_name = f"{styles[cat_code][style_code]} {categories[cat_code]}"
        description = f"A {patterns[pattern_code].lower()} {colors[color_code].lower()} {item_name.lower()}."
        rack_no = f"R{random.randint(1, 20)}-S{random.randint(1, 5)}"
        quantity = random.randint(5, 150)
        created_at = now - timedelta(days=random.randint(0, 365))
        
        items.append({
            'item_code': item_code, 'item_name': item_name, 'description': description,
            'rack_no': rack_no, 'quantity': quantity, 'created_at': created_at
        })
        existing_codes.add(item_code)
        item_id_counter += 1

    return items

def seed_database():
    """Connects to the PostgreSQL DB and inserts the sample data."""
    # First, ensure the database table exists.
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    sample_data = generate_sample_data()
    
    inserted_count = 0
    for item in sample_data:
        try:
            cursor.execute(
                'INSERT INTO items (item_code, item_name, rack_no, quantity, description, created_at) VALUES (%s, %s, %s, %s, %s, %s)',
                (item['item_code'], item['item_name'], item['rack_no'], item['quantity'], item['description'], item['created_at'])
            )
            inserted_count += 1
        except psycopg2.IntegrityError:
            # This error means the item_code already exists (UNIQUE constraint failed).
            # We can safely skip it. For a seeder, skipping is fine.
            conn.rollback() # Rollback the failed transaction before the next one
            print(f"Skipping duplicate item code: {item['item_code']}")
            
    conn.commit()
    cursor.close()
    conn.close()
    print(f"\nDatabase seeding complete. Inserted {inserted_count} new items into PostgreSQL.")

if __name__ == '__main__':
    seed_database()