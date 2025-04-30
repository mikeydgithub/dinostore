from flask import Flask, render_template, url_for, session, request, jsonify, redirect, flash
from PIL import Image
import os
import psycopg2
import datetime # Import the datetime module
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  #  Set the login view for redirection

class User(UserMixin):
    """User model for the database."""
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        """Retrieves a user from the database by ID."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password_hash FROM users WHERE id = %s;", (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        if user_data:
            return User(id=user_data[0], username=user_data[1],
                        email=user_data[2], password_hash=user_data[3])
        return None

class Order:
    """Order model for the database."""
    def __init__(self, id, user_id, order_date):
        self.id = id
        self.user_id = user_id
        self.order_date = order_date

    @staticmethod
    def get_orders_by_user_id(user_id):
        """Retrieves orders for a given user ID from the database."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, order_date FROM orders WHERE user_id = %s ORDER BY order_date DESC;", (user_id,))
        orders_data = cur.fetchall()
        cur.close()
        conn.close()
        orders = []
        for order_data in orders_data:
            orders.append(Order(id=order_data[0], user_id=user_id,
                                order_date=order_data[1]))
        return orders

class OrderItem:
    """OrderItem model for the database."""
    def __init__(self, order_id, product_name, quantity, price):
        self.order_id = order_id
        self.product_name = product_name
        self.quantity = quantity
        self.price = price

    @staticmethod
    def get_order_items_by_order_id(order_id):
        """Retrieves order items for a given order ID from the database."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT product_name, quantity, price FROM order_items WHERE order_id = %s;", (order_id,))
        order_items_data = cur.fetchall()
        cur.close()
        conn.close()
        order_items = []
        for item_data in order_items_data:
            order_items.append(OrderItem(order_id=order_id,
                                        product_name=item_data[0],
                                        quantity=item_data[1], price=item_data[2]))
        return order_items


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[
        DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[
        DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """Validates that the username is unique."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username = %s;",
                    (username.data,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            raise ValidationError('Username is already taken.')

    def validate_email(self, email):
        """Validates that the email is unique."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE email = %s;", (email.data,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            raise ValidationError('Email is already registered.')
class LoginForm(FlaskForm):
    """Form for user login."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route("/register", methods=['GET', 'POST'])
def register():
    """User registration route."""
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        hashed_password = generate_password_hash(
            password)  # Hash the password
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                (username, email, hashed_password))
            conn.commit()
        except Exception as e:
            print(f"Error during registration: {e}")  # Log the error
            conn.rollback()
            flash("An error occurred during registration. Please try again.",
                  'error')  # Inform the user
            return render_template('register.html', form=form)
        cur.close()
        conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    """User login route."""
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, password_hash FROM users WHERE email = %s;",
            (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        if user_data:
            user = User(id=user_data[0], username=user_data[1],
                        email=user_data[2], password_hash=user_data[3])
            if check_password_hash(user.password_hash,
                                    password):  # Check the password
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(
                    url_for('index'))  # Redirect to the homepage or profile
            else:
                flash('Invalid password.', 'error')
        else:
            flash('Invalid email.', 'error')
    return render_template('login.html', form=form)


@app.route("/logout")
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))


@app.route("/profile")
@login_required
def profile():
    """User profile route."""
    user_orders = Order.get_orders_by_user_id(
        current_user.id)  # Get orders for current user
    return render_template('profile.html', user=current_user, orders=user_orders)


@app.route("/order/<int:order_id>")  # Route to view a specific order's details
@login_required
def order_detail(order_id):
    """View the details of a specific order."""
    # First, get the order to make sure it belongs to the current user
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM orders WHERE id = %s;", (order_id,))
    order_user_id = cur.fetchone()
    cur.close()
    conn.close()

    if not order_user_id or order_user_id[0] != current_user.id:
        flash("Order not found or does not belong to you.", "error")
        return redirect(
            url_for('profile'))  # Redirect to profile or order history

    order_items = OrderItem.get_order_items_by_order_id(
        order_id)  # Get the items in the order
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT order_date FROM orders WHERE id = %s;", (order_id,))
    order_date = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('order_detail.html', order_items=order_items,
                           order_date=order_date)

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    return conn

def fetch_products_from_db():
    """Fetches product data from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, image, price FROM products;")
    products = []
    for row in cur.fetchall():
        products.append({'id': row[0], 'name': row[1], 'image': row[2], 'price': float(row[3])})
    cur.close()
    conn.close()
    print(f"Flask - fetch_products_from_db() returning: {products}")
    return products

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(filename, width, height):
    """Resizes an image and saves it to the resized folder."""
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
    """Displays the homepage with product listings."""
    products = fetch_products_from_db()
    resized_products = []
    for product in products:
        resized_image_url = resize_image(product['image'], 200, 200)
        resized_products.append({**product, 'resized_image': resized_image_url})
        session['test'] = 'test'
        print(f"Session: {session}")
    return render_template("index.html", products=resized_products, cart=session.get('cart', {}))

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    """Adds a product to the shopping cart in the session."""
    product_id_str = request.form.get("product_id")
    quantity_str = request.form.get("quantity", "1")

    try:
        product_id = int(product_id_str)
        quantity = int(quantity_str)
    except ValueError:
        return jsonify({"error": "Invalid product ID or quantity"}), 400

    new_cart = {}
    if 'cart' not in session:
        session['cart'] = {}
    else:
        for key, value in session['cart'].items():
            try:
                new_cart[int(key)] = value
            except ValueError:
                print(f"Flask - Warning: Non-integer key found in cart: {key}")
        session['cart'] = new_cart

    # Force all keys in the cart to be integers upon adding
    # Ensure product_id is an integer *before* using it as a key
    session['cart'][product_id] = session['cart'].get(product_id, 0) + quantity
    session.modified = True
    print(f"Flask - Session after adding: {session['cart']}")
    return jsonify({"message": "Added to cart",
                    "cart_count": sum(session['cart'].values())})

@app.route("/cart")
def view_cart():
    """Displays the shopping cart page."""
    cart_items = []
    total_price = 0
    cart = session.get('cart', {})
    products_from_db = fetch_products_from_db()  # Call it once here
    products_from_db_dict = {
        p['id']: p for p in products_from_db
    }  # Create the lookup dictionary

    print(f"Flask - view_cart - Contents of session['cart']: {cart}, Keys Type: {[type(k) for k in cart.keys()]}")  # Debugging
    print(f"Flask - view_cart - products_from_db: {products_from_db_dict}")  # Debugging

    for product_id_str, quantity in cart.items():
        try:
            product_id = int(product_id_str)  # Explicitly convert the key to integer
            print(
                f"Flask - view_cart - Looking for product_id: {product_id} (Type: {type(product_id)})")  # Debugging
            product = products_from_db_dict.get(product_id)
            if product:
                print(
                    f"Flask - view_cart - Found product: {product['name']}, Quantity: {quantity}")  # Debugging
                total_price += product['price'] * quantity
                cart_items.append({'product': product, 'quantity': quantity})
            else:
                print(
                    f"Flask - view_cart - Could not find product with id: {product_id} in database")  # Debugging
        except ValueError:
            print(
                f"Flask - view_cart - Invalid product_id in cart (not an integer): {product_id_str}")

    print(f"Flask - view_cart - cart_items list before rendering: {cart_items}")  # Debugging
    return render_template("cart.html", cart_items=cart_items,
                           total_price=total_price)

@app.route("/update_cart", methods=["POST"])
def update_cart():
    """Updates the quantity of a product in the shopping cart."""
    product_id_str = request.form.get("product_id")
    quantity_str = request.form.get("quantity")

    try:
        product_id = int(product_id_str)
        quantity = int(quantity_str)
    except ValueError:
        return jsonify({"error": "Invalid product ID or quantity"}), 400

    if 'cart' in session:
        session['cart'] = {int(k): v for k, v in session['cart'].items()}
        if quantity > 0:
            session['cart'][product_id] = quantity
        else:
            del session['cart'][product_id]
        session.modified = True
        return jsonify({"message": "Cart updated",
                        "cart_count": sum(session['cart'].values())})
    return jsonify({"error": "Product not in cart"}), 400

@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    """Removes a product from the shopping cart."""
    product_id_str = request.form.get("product_id")

    try:
        product_id = int(product_id_str)
    except ValueError:
        return jsonify({"error": "Invalid product ID"}), 400

    # Force keys in cart to be integers before attempting removal
    if 'cart' in session:
        session['cart'] = {int(k): v for k, v in session['cart'].items()}

    print(
        f"Flask - remove_from_cart - product_id to remove: {product_id} (Type: {type(product_id)})")
    print(
        f"Flask - remove_from_cart - session contents after forcing int keys: {session.get('cart')}")

    if 'cart' in session and product_id in session['cart']:
        del session['cart'][product_id]
        session.modified = True
        return jsonify({"message": "Removed from cart",
                        "cart_count": sum(session['cart'].values())})
    else:
        print(
            f"Flask - remove_from_cart - Cart not in session or product_id not in cart (after forcing int).")
        return jsonify({"error": "Product not in cart"}), 400

#Fetch Cart Items: This route retrieves the cart items and total price, similar to the view_cart route.
@app.route("/checkout")
def checkout():
    """Displays the checkout page."""
    cart_items = []
    total_price = 0
   # Force keys in cart to be integers when retrieving from session
    cart = {int(k): v for k, v in session.get('cart', {}).items()}
    print(f"Flask - /checkout - session['cart']: {cart},  Key types: {[type(k) for k in cart.keys()]}")
    products_from_db = {p['id']: p for p in fetch_products_from_db()}

    for product_id, quantity in cart.items():
        print(
            f"Flask - /checkout - product_id from cart: {product_id}, type: {type(product_id)}")  # Debugging
        product = products_from_db.get(product_id)
        if product:
            print(
                f"Flask - /checkout - Found product: {product['name']}, Quantity: {quantity}")  # Debugging
            total_price += product['price'] * quantity
            cart_items.append({'product': product, 'quantity': quantity})
        else:
            print(
                f"Flask - /checkout - Could not find product with id: {product_id} in database")  # Debugging

    print(f"Flask - /checkout - cart_items list before rendering: {cart_items}")  # Debugging
    return render_template("checkout.html", cart_items=cart_items,
                           total_price=total_price)

@app.route("/test")
def test_page():
        return render_template('test.html')

@app.route("/process_order", methods=["POST"])
def process_order():
    """Processes the order (simulated)."""
    name = request.form.get("name")
    address = request.form.get("address")
    email = request.form.get("email")

    cart = session.get('cart', {})
    products_from_db = {p['id']: p for p in fetch_products_from_db()}
    order_items = []
    total_price = 0

    for product_id, quantity in cart.items():
        product = products_from_db.get(product_id)
        if product:
            total_price += product['price'] * quantity
            order_items.append({
                'product_id': product_id,
                'product_name': product['name'],
                'quantity': quantity,
                'price': product['price'],
            })


    # For this example, we'll just simulate a successful order.
    order_date = datetime.datetime.now()
    print(f"Simulating order processing for: {name}, {address}, {email}")
    print(f"Order items: {order_items}")
    print(f"Order total: ${total_price:.2f}")
    print(f"Order Date: {order_date}")

    session.pop('cart', None)  # Clear the cart

    return render_template("order_confirmation.html",
                           name=name,
                           address=address,
                           email=email,
                           order_items=order_items,
                           total_price=total_price,
                           order_date=order_date)


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESIZED_FOLDER'], exist_ok=True)
    app.run(debug=True)
    