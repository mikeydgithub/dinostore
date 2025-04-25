from flask import Flask, render_template, url_for, session, request, jsonify
from PIL import Image
import os
import psycopg2

app = Flask(__name__)
app.secret_key = 'nDH9KNp4frnBnx8pT00xcsVErlXglPAn'

# Database connection details
DB_HOST = "localhost"
DB_NAME = "dinostore_db"
DB_USER = "postgres"  # Replace with your PostgreSQL username
DB_PASSWORD = "crunchbar"  # Replace with your PostgreSQL password

UPLOAD_FOLDER = 'static/uploads'
RESIZED_FOLDER = 'static/resized'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESIZED_FOLDER'] = RESIZED_FOLDER

def get_db_connection():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    return conn

def fetch_products_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, image, price FROM products;")
    products = []
    for row in cur.fetchall():
        products.append({'id': row[0], 'name': row[1], 'image': row[2], 'price': float(row[3])})
        print(f"Flask - Fetched product from DB: {products[-1]}") # Debugging
    cur.close()
    conn.close()
    return products

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(filename, width, height):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_filename = f"{os.path.splitext(filename)[0]}_{width}x{height}{os.path.splitext(filename)[1]}"
    output_path = os.path.join(app.config['RESIZED_FOLDER'], output_filename)
    try:
        img = Image.open(filepath)
        img = img.resize((width, height))
        img.save(output_path)
        return url_for('static', filename=f'resized/{output_filename}')
    except Exception as e:
        print(f"Error resizing {filename}: {e}")
        return url_for('static', filename=f'uploads/{filename}')

@app.route("/")
def index():
    products = fetch_products_from_db()
    resized_products = []
    for product in products:
        resized_image_url = resize_image(product['image'], 200, 200)
        resized_products.append({**product, 'resized_image': resized_image_url})
    return render_template("index.html", products=resized_products, cart=session.get('cart', {}))

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id_str = request.form.get("product_id")
    quantity_str = request.form.get("quantity", "1")  # Get quantity as string initially

    # Debugging output to check types and values
    print(f"Flask - Received product_id_str: '{product_id_str}', Type: {type(product_id_str)}")
    print(f"Flask - Received quantity_str: '{quantity_str}', Type: {type(quantity_str)}")
    # Debugging output to check types and values

    try:
        product_id = int(product_id_str)
        quantity = int(quantity_str)

        # Debugging output to check types and values
        print(f"Flask - Converted product_id: {product_id}, Type: {type(product_id)}")
        print(f"Flask - Converted quantity: {quantity}, Type: {type(quantity)}")
        # Debugging output to check types and values

    except ValueError:
        print(f"Flask - Error: Could not convert product_id or quantity to integer")
        return jsonify({"error": "Invalid product ID or quantity"}), 400
    
    print(f"Flask - Session before adding: {session.get('cart')}, Type: {type(session.get('cart'))}")

    # Initialize cart if it doesn't exist
    if 'cart' not in session:
        session['cart'] = {}

    # Force all keys in the cart to be integers upon adding
    new_cart = {}
    for key, value in session['cart'].items():
        try:
            new_cart[int(key)] = value
        except ValueError:
            print(f"Flask - Warning: Non-integer key found in cart: {key}")
    session['cart'] = new_cart

    if product_id in session['cart']:
        session['cart'][product_id] += quantity
    else:
        session['cart'][product_id] = quantity

    session.modified = True
    print(f"Flask - Session after adding: {session['cart']}")
    return jsonify({"message": "Added to cart", "cart_count": sum(session['cart'].values())})

@app.route("/cart")
def view_cart():
    cart_items = []
    total_price = 0
    cart = session.get('cart', {})
    print(f"Flask - view_cart - Contents of session['cart']: {cart}, Keys Type: {[type(k) for k in cart.keys()]}") # Debugging
    products_from_db = {p['id']: p for p in fetch_products_from_db()}
    print(f"Flask - view_cart - Contents of products_from_db keys: {[k for k in products_from_db.keys()]}, Values Type: {[type(v) for v in products_from_db.values()]}") # Debugging

    for product_id_str, quantity in cart.items():
        try:
            product_id = int(product_id_str)  # Explicitly convert the key to integer
            print(f"Flask - view_cart - Looking for product_id: {product_id} (Type: {type(product_id)})") # Debugging
            product = products_from_db.get(product_id)
            if product:
                print(f"Flask - view_cart - Found product: {product['name']}, Quantity: {quantity}") # Debugging
                total_price += product['price'] * quantity
                cart_items.append({'product': product, 'quantity': quantity})
            else:
                print(f"Flask - view_cart - Could not find product with id: {product_id} in database") # Debugging
        except ValueError:
            print(f"Flask - Invalid product_id in cart (not an integer): {product_id_str}")

    print(f"Flask - cart_items list before rendering: {cart_items}")
    return render_template("cart.html", cart_items=cart_items, total_price=total_price)

@app.route("/update_cart", methods=["POST"])
def update_cart():
    product_id_str = request.form.get("product_id")
    quantity_str = request.form.get("quantity")

    try:
        product_id = int(product_id_str)
        quantity = int(quantity_str)
    except ValueError:
        return jsonify({"error": "Invalid product ID or quantity"}), 400

    if 'cart' in session and product_id in session['cart']:
        if quantity > 0:
            session['cart'][product_id] = quantity
        else:
            del session['cart'][product_id]
        session.modified = True
        return jsonify({"message": "Cart updated", "cart_count": sum(session['cart'].values())})
    return jsonify({"error": "Product not in cart"}), 400

@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    product_id_str = request.form.get("product_id")

    try:
        product_id = int(product_id_str)
    except ValueError:
        return jsonify({"error": "Invalid product ID"}), 400

    if 'cart' in session and product_id in session['cart']:
        del session['cart'][product_id]
        session.modified = True
        return jsonify({"message": "Removed from cart", "cart_count": sum(session['cart'].values())})
    return jsonify({"error": "Product not in cart"}), 400

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESIZED_FOLDER'], exist_ok=True)
    app.run(debug=True)