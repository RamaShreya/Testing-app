from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import text
import os
from models import db, User, Product, Order, LabReview, Coupon

app = Flask(__name__)
# SECURITY BEST PRACTICE: Use a strong, random secret key for session signing
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Context Processor for Global Template Variables ---
@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    vuln_mode = session.get('vuln_mode', False)
    return dict(cart_count=cart_count, vuln_mode=vuln_mode)

# --- Application Routes ---

@app.route('/')
def index():
    query = request.args.get('q')
    category = request.args.get('category')
    
    products_query = Product.query
    if query:
        # Implementing backend search functionality securely
        products_query = products_query.filter(Product.name.icontains(query))
    if category:
        products_query = products_query.filter_by(category=category)
        
    products = products_query.all()
    return render_template('index.html', products=products, search_query=query, current_category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # BROKEN AUTHENTICATION LOGIC (VULN_MODE)
        vuln_mode = session.get('vuln_mode', False)
        
        if user:
            if vuln_mode:
                # INSECURE: Allow login if password matches the hash directly (plain text comparison)
                # or if the password is "anything" (for quick testing)
                if password == user.password_hash or password == "password123":
                    login_user(user)
                    flash('VULNERABLE LOGIN SUCCESSFUL (Broken Auth)', 'danger')
                    return redirect(url_for('index'))
            
            # SECURE: Using proper salted hashing
            if check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
        
        flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', 'warning')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/toggle-vuln')
def toggle_vuln():
    current_mode = session.get('vuln_mode', False)
    session['vuln_mode'] = not current_mode
    session.modified = True
    
    if session['vuln_mode']:
        flash('Vulnerability Mode: ON (Training Mode Active)', 'danger')
    else:
        flash('Vulnerability Mode: OFF (Safe Mode)', 'success')
        
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
def cart():
    # Retrieve cart from session (or empty dict)
    session_cart = session.get('cart', {})
    
    cart_items = []
    total = 0.0
    
    for product_id_str, quantity in session_cart.items():
        product = Product.query.get(int(product_id_str))
        if product:
            subtotal = product.price * quantity
            total += subtotal
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    
    if 'cart' not in session:
        session['cart'] = {}
        
    cart = session['cart']
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        cart[product_id_str] += 1
    else:
        cart[product_id_str] = 1
        
    session.modified = True
    flash(f'Added {product.name} to cart!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session:
        product_id_str = str(product_id)
        if product_id_str in session['cart']:
            del session['cart'][product_id_str]
            session.modified = True
            flash('Item removed from cart.', 'info')
            
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    session_cart = session.get('cart', {})
    if not session_cart:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        session.pop('cart', None) # Clear the cart
        flash('Order placed successfully! (This is a dummy checkout)', 'success')
        return redirect(url_for('index'))
        
    total = 0.0
    for product_id_str, quantity in session_cart.items():
        product = Product.query.get(int(product_id_str))
        if product:
            total += product.price * quantity
            
    return render_template('checkout.html', total=total)

@app.route('/lab')
def lab():
    return render_template('lab.html')

@app.route('/lab/sqli', methods=['GET', 'POST'])
def lab_sqli():
    results = None
    query_used = None
    vuln_mode = session.get('vuln_mode', False)
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        
        if vuln_mode:
            # INSECURE: Raw SQL concatenation
            query_used = f"SELECT id, username FROM user WHERE username = '{username}'"
            try:
                # Using text() but still vulnerable because of f-string
                results = db.session.execute(text(query_used)).fetchall()
            except Exception as e:
                results = str(e)
        else:
            # SECURE: Using ORM
            user = User.query.filter_by(username=username).all()
            results = [(u.id, u.username) for u in user]
            query_used = "SELECT id, username FROM user WHERE username = ?"
            
    return render_template('lab_sqli.html', results=results, query_used=query_used)

@app.route('/orders/<int:user_id>')
@login_required
def view_orders(user_id):
    vuln_mode = session.get('vuln_mode', False)
    
    if not vuln_mode:
        # SECURE: Authorization check
        if current_user.id != user_id:
            flash("UNAUTHORIZED: You can only view your own orders.", "danger")
            return redirect(url_for('index'))
    
    # Fetch orders for the requested user_id
    orders = Order.query.filter_by(user_id=user_id).all()
    target_user = User.query.get(user_id)
    
    return render_template('lab_orders.html', orders=orders, target_user=target_user)

@app.route('/lab/xss', methods=['GET', 'POST'])
def lab_xss():
    review = None
    if request.method == 'POST':
        review = {
            "author": request.form.get("author", "Anonymous"),
            "content": request.form.get("content", "")
        }
    return render_template('lab_xss.html', review=review)

@app.route('/lab/auth')
def lab_auth():
    return render_template('lab_auth.html')

@app.route('/lab/idor')
def lab_idor():
    return render_template('lab_idor.html')

@app.route('/lab/csrf')
def lab_csrf():
    return render_template('lab_csrf.html')

@app.route('/lab/bruteforce')
def lab_bruteforce():
    return render_template('lab_bruteforce.html')

@app.route('/lab/phishing')
def lab_phishing():
    return render_template('lab_phishing.html')

@app.route('/lab/ransomware')
def lab_ransomware():
    return render_template('lab_ransomware.html')

@app.route('/lab/dos')
def lab_dos():
    return render_template('lab_dos.html')

@app.route('/lab/mitm')
def lab_mitm():
    return render_template('lab_mitm.html')

# --- Advanced Lab Routes ---

@app.route('/lab/stored-xss', methods=['GET', 'POST'])
def lab_stored_xss():
    if request.method == 'POST':
        content = request.form.get('content')
        username = request.form.get('username', 'Anonymous')
        if content:
            new_review = LabReview(username=username, content=content)
            db.session.add(new_review)
            db.session.commit()
            flash('Comment posted!', 'success')
    
    reviews = LabReview.query.order_by(LabReview.timestamp.desc()).all()
    return render_template('lab_stored_xss.html', reviews=reviews)

@app.route('/lab/csrf-attack')
def lab_csrf_attack():
    return render_template('lab_csrf_attack.html')

@app.route('/lab/download')
def lab_download():
    filename = request.args.get('file')
    if not filename:
        return render_template('lab_traversal.html')
    
    vuln_mode = session.get('vuln_mode', False)
    # Target directory for downloads
    download_dir = os.path.join(app.root_path, 'static', 'downloads')
    
    if vuln_mode:
        # INSECURE: Directory Traversal
        file_path = os.path.join(download_dir, filename)
        try:
            return send_file(file_path)
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        # SECURE: Validation
        from werkzeug.utils import secure_filename
        if not filename:
            abort(400)
        safe_filename = secure_filename(filename)
        file_path = os.path.join(download_dir, safe_filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_file(file_path)
        else:
            abort(404)

@app.route('/lab/upload', methods=['GET', 'POST'])
def lab_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            vuln_mode = session.get('vuln_mode', False)
            filename = file.filename
            
            if not vuln_mode:
                # SECURE: Extension check
                allowed = {'png', 'jpg', 'jpeg', 'gif'}
                if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed:
                    flash('Invalid file type! (Only images allowed in Safe Mode)', 'danger')
                    return redirect(url_for('lab_upload'))
            
            # Save to a temporary lab directory
            upload_path = os.path.join(app.root_path, 'static', 'lab_uploads')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            
            file.save(os.path.join(upload_path, filename))
            flash(f'File {filename} uploaded successfully!', 'success')
            
    return render_template('lab_upload.html')

@app.route('/lab/redirect')
def lab_redirect():
    target = request.args.get('url')
    if not target:
        return render_template('lab_redirect.html')
    
    vuln_mode = session.get('vuln_mode', False)
    if vuln_mode:
        # INSECURE: Open Redirect
        return redirect(target)
    else:
        # SECURE: Whitelist
        if target.startswith('/') or target.startswith(request.host_url):
            return redirect(target)
        else:
            flash('Unauthorized redirect blocked!', 'danger')
            return redirect(url_for('lab_redirect'))

@app.route('/lab/info-disclosure')
def lab_info_disclosure():
    vuln_mode = session.get('vuln_mode', False)
    debug_info = None
    if vuln_mode:
        # INSECURE: Information Disclosure
        debug_info = {
            'SERVER_SOFTWARE': request.environ.get('SERVER_SOFTWARE'),
            'PATH': os.environ.get('PATH'),
            'DB_URI': app.config.get('SQLALCHEMY_DATABASE_URI'),
            'SECRET_KEY_PREVIEW': str(app.config.get('SECRET_KEY'))[:10] + "..."
        }
    return render_template('lab_info.html', debug_info=debug_info)

@app.route('/lab/business-logic', methods=['GET', 'POST'])
def lab_business_logic():
    total = 100.00
    quantity = 1
    discount = 0.0
    final_price = 100.00
    
    if request.method == 'POST':
        qty_str = request.form.get('quantity', '1')
        coupon_code = request.form.get('coupon', '')
        
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 1
            
        vuln_mode = session.get('vuln_mode', False)
        
        if not vuln_mode:
            # SECURE: Validate quantity
            if qty < 1:
                flash('Quantity must be at least 1!', 'danger')
                qty = 1
        
        # Apply coupon
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon:
            discount = total * (coupon.discount / 100)
            flash(f'Coupon {coupon_code} applied!', 'success')
        
        final_price = (total * qty) - discount
        return render_template('lab_logic.html', total=total, quantity=qty, discount=discount, final_price=final_price)

    return render_template('lab_logic.html', total=total, quantity=quantity, discount=discount, final_price=final_price)

@app.route('/lab/brute-force', methods=['GET', 'POST'])
def lab_brute_force():
    attempts = session.get('brute_attempts', 0)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        vuln_mode = session.get('vuln_mode', False)
        
        if not vuln_mode:
            # SECURE: Rate limiting (simplified)
            if attempts >= 3:
                flash('Account locked due to too many attempts. Please wait 10 minutes.', 'danger')
                return render_template('lab_brute.html', attempts=attempts)
        
        if username == 'admin' and password == 'supersecret123':
            session['brute_attempts'] = 0
            flash('Login Successful!', 'success')
        else:
            attempts += 1
            session['brute_attempts'] = attempts
            flash('Invalid credentials.', 'danger')
            
    return render_template('lab_brute.html', attempts=attempts)

# --- Initialization ---
def init_db():
    print(f"Database path: {os.path.abspath('database.db')}")
    print("Recreating database with updated schema...")
    db.drop_all()
    db.create_all()
    
    sample_products = [
            Product(name='Pro Laptop X1', description='High-performance laptop with 16GB RAM and 512GB SSD. Perfect for professionals.', price=1299.99, category='Computers', image_url='https://images.unsplash.com/photo-1496181133206-80ce9b88a853?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Smartphone Z Pro', description='Latest generation smartphone with stunning OLED display and pro camera system.', price=899.99, category='Smartphones', image_url='https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Noise Cancelling Headphones', description='Over-ear wireless headphones with industry-leading noise cancellation.', price=249.99, category='Audio', image_url='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Smartwatch Elite', description='Fitness tracker and smartwatch with heart rate monitor and GPS.', price=199.99, category='Wearables', image_url='https://images.unsplash.com/photo-1523275335684-37898b6baf30?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Wireless Charger Pad', description='Fast wireless charging pad compatible with smartphones and earbuds', price=29.99, category='Accessories', image_url='/static/images/wireless_charger.png'),
            Product(name='Gaming Console Ultra', description='Next-gen gaming console with 4K resolution and 120fps support.', price=499.99, category='Computers', image_url='https://images.unsplash.com/photo-1486401899868-0e435ed85128?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='4K Action Camera', description='Waterproof action camera capable of recording 4K video at 60fps.', price=199.99, category='Accessories', image_url='https://images.unsplash.com/photo-1502920917128-1aa500764cbd?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Bluetooth Portable Speaker', description='Compact, waterproof Bluetooth speaker with 12-hour battery life.', price=59.99, category='Audio', image_url='https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Wireless Earbuds', description='True wireless earbuds with active noise cancellation and charging case.', price=129.99, category='Audio', image_url='https://images.unsplash.com/photo-1590658268037-6bf12165a8df?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Tablet Pro 11"', description='11-inch tablet with powerful processor and stylus support for creatives.', price=649.99, category='Computers', image_url='https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Smart Home Hub', description='Voice-controlled smart home speaker to control all your connected devices.', price=89.99, category='Audio', image_url='https://images.unsplash.com/photo-1543512214-318c7553f230?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Mirrorless Camera Kit', description='24MP mirrorless camera with 15-45mm kit lens, great for vlogging.', price=799.99, category='Accessories', image_url='https://images.unsplash.com/photo-1516035069371-29a1b244cc32?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='External SSD 1TB', description='Portable 1TB NVMe SSD for blazing-fast file transfers.', price=109.99, category='Accessories', image_url='https://images.unsplash.com/photo-1531492746076-161ca9bcad58?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Gaming Mechanical Keyboard', description='RGB mechanical keyboard with tactile blue switches.', price=89.99, category='Accessories', image_url='https://images.unsplash.com/photo-1595225476474-87563907a212?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Wireless Gaming Mouse', description='Lightweight wireless gaming mouse with 20K DPI optical sensor.', price=69.99, category='Accessories', image_url='https://images.unsplash.com/photo-1527814050087-3793815479db?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='27" 4K Monitor', description='27-inch 4K UHD IPS monitor with accurate colors for design and work.', price=329.99, category='Computers', image_url='https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='USB-C Docking Station', description='10-in-1 USB-C hub with HDMI, ethernet, and SD card reader.', price=49.99, category='Accessories', image_url='https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='Drone with 4K Camera', description='Compact drone with 3-axis gimbal and 4K camera.', price=599.99, category='Accessories', image_url='https://images.unsplash.com/photo-1473968512647-3e447244af8f?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
            Product(name='E-Reader Pro', description='Lightweight e-reader with high-resolution display and long battery life', price=249.99, category='Computers', image_url='/static/images/ereader.png'),
            Product(name='Fitness Tracker Band', description='Slim fitness tracker with sleep monitoring and step counting.', price=39.99, category='Wearables', image_url='https://images.unsplash.com/photo-1576243345690-4e4b79b63288?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60')
        ]
    db.session.bulk_save_objects(sample_products)
    
    # Adding sample users and orders for Lab demonstrations
    admin = User(username='admin', password_hash=generate_password_hash('admin123'))
    guest = User(username='guest', password_hash=generate_password_hash('guest123'))
    db.session.add_all([admin, guest])
    db.session.commit()
    
    # Adding sample orders for IDOR demo
    orders = [
        Order(user_id=admin.id, product_name='Pro Laptop X1', amount=1299.99, status='Delivered'),
        Order(user_id=guest.id, product_name='Wireless Earbuds', amount=129.99, status='Processing'),
        Order(user_id=guest.id, product_name='Smartwatch Elite', amount=199.99, status='Shipped')
    ]
    db.session.add_all(orders)
    db.session.commit()
    
    # Adding sample coupons for Business Logic demo
    coupons = [
        Coupon(code='SAVE10', discount=10.0),
        Coupon(code='WELCOME50', discount=50.0)
    ]
    db.session.add_all(coupons)
    db.session.commit()
    
    # Ensure directories exist for traversal and upload labs
    for folder in ['downloads', 'lab_uploads']:
        path = os.path.join(app.root_path, 'static', folder)
        if not os.path.exists(path):
            os.makedirs(path)
            
    # Create a dummy secret file for traversal lab
    with open(os.path.join(app.root_path, 'static', 'downloads', 'readme.txt'), 'w') as f:
        f.write("This is a public file.")
    
    # Create a secret file outside the downloads folder (to test traversal)
    with open(os.path.join(app.root_path, 'secret.txt'), 'w') as f:
        f.write("CONFIDENTIAL: If you can see this, Directory Traversal is active!")

    print("Database initialized with products, users, orders, and coupons")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)
