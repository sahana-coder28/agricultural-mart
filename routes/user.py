from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import razorpay
from models import Product, CartItem, WishlistItem, Order, OrderItem, Review, Payment
from extensions import db
from functools import wraps

user_bp = Blueprint('user', __name__)

def farmer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'farmer':
            flash('Farmer access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum([item.product.price * item.quantity for item in cart_items])
    return render_template('shop/cart.html', cart_items=cart_items, total=total)

@user_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        quantity = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    
    if quantity <= 0:
        flash('Invalid quantity.', 'danger')
        return redirect(request.referrer or url_for('main.product_detail', product_id=product_id))
        
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        if cart_item.quantity + quantity > product.stock:
            flash(f'You already have {cart_item.quantity} in cart. Total exceeds stock.', 'danger')
            return redirect(request.referrer or url_for('main.product_detail', product_id=product_id))
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash(f'{quantity} x {product.name} added to cart!', 'success')
    return redirect(request.referrer or url_for('main.index'))

@user_bp.route('/cart/remove/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.', 'info')
    return redirect(url_for('user.cart'))

@user_bp.route('/wishlist')
@login_required
def wishlist():
    wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('shop/wishlist.html', wishlist_items=wishlist_items)

@user_bp.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_wishlist(product_id):
    item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash('Removed from wishlist', 'info')
    else:
        new_item = WishlistItem(user_id=current_user.id, product_id=product_id)
        db.session.add(new_item)
        db.session.commit()
        flash('Added to wishlist', 'success')
    return redirect(request.referrer or url_for('main.index'))

@user_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('main.index'))
        
    total = sum([item.product.price * item.quantity for item in cart_items])
    
    # Final stock check
    for item in cart_items:
        if item.quantity > item.product.stock:
            flash(f'Sorry, {item.product.name} is now out of stock or insufficient. Available: {item.product.stock}', 'danger')
            return redirect(url_for('user.cart'))
            
    if request.method == 'POST':
        # Create the local order and associated items
        order = Order(user_id=current_user.id, total_price=total, status='Pending')
        db.session.add(order)
        
        # Add order items from cart
        for item in cart_items:
            order_item = OrderItem(
                order=order, 
                product_id=item.product_id, 
                quantity=item.quantity, 
                price=item.product.price
            )
            db.session.add(order_item)
            
        db.session.commit()
        
        # Initialize Razorpay Client
        try:
            is_simulated = current_app.config.get('RAZORPAY_SIMULATE', False)
            
            if is_simulated:
                # Simulation Mode: Bypass Razorpay API
                razorpay_order_id = f"sim_order_{order.id}"
            else:
                client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
                
                # Create Razorpay Order
                data = {
                    "amount": int(total * 100),
                    "currency": "INR",
                    "receipt": f"order_{order.id}",
                    "payment_capture": 1
                }
                razorpay_order = client.order.create(data=data)
                razorpay_order_id = razorpay_order['id']
            
            # Create Payment Record
            payment = Payment(
                user_id=current_user.id,
                order_id=order.id,
                razorpay_order_id=razorpay_order_id,
                amount=total,
                status='Pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            return render_template('shop/checkout.html', 
                                 total=total, 
                                 razorpay_order_id=razorpay_order_id,
                                 razorpay_key_id=current_app.config['RAZORPAY_KEY_ID'],
                                 order_id=order.id,
                                 is_simulated=is_simulated)
        except Exception as e:
            flash(f'Error initializing payment gateway: {str(e)}. Please contact support.', 'danger')
            return redirect(url_for('user.checkout'))
        
    return render_template('shop/checkout.html', total=total)

@user_bp.route('/payment/verify', methods=['POST'])
@login_required
def verify_payment():
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    order_id = request.form.get('order_id')
    
    is_simulated = current_app.config.get('RAZORPAY_SIMULATE', False)
    
    try:
        if not is_simulated:
            client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify the payment signature
            client.utility.verify_payment_signature(params_dict)
        else:
            # For simulation, just record the mock signature info
            if not razorpay_payment_id:
                razorpay_payment_id = f"sim_pay_{order_id}"
            if not razorpay_signature:
                razorpay_signature = "sim_sig_verified"
        
        # On success, update records
        payment = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = 'Success'
        
        order = Order.query.get(order_id)
        order.status = 'Confirmed'
        
        # Reduce stock and clear cart
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        for item in cart_items:
            product = Product.query.get(item.product_id)
            product.stock -= item.quantity
            db.session.delete(item)
            
        db.session.commit()
        flash('Payment Successful! Order Confirmed.', 'success')
        return redirect(url_for('user.orders'))
        
    except Exception as e:
        payment = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
        if payment:
            payment.status = 'Failed'
            db.session.commit()
        flash(f'Payment Failed or Signature Verification Failed. Error: {str(e)}', 'danger')
        return redirect(url_for('user.checkout'))

@user_bp.route('/payment-history')
@login_required
def payment_history():
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    return render_template('shop/payment_history.html', payments=payments)

@user_bp.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('shop/orders.html', orders=orders)

@user_bp.route('/profile')
@login_required
def profile():
    return render_template('shop/profile.html')

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        existing_user = current_user.__class__.query.filter_by(email=email).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Email already in use.', 'danger')
            return redirect(url_for('user.edit_profile'))
            
        current_user.username = username
        current_user.email = email
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('user.profile'))
        
    return render_template('shop/edit_profile.html')

@user_bp.route('/my-products')
@login_required
@farmer_required
def my_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('shop/my_products.html', products=products)

@user_bp.route('/product/add', methods=['GET', 'POST'])
@login_required
@farmer_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        
        image_url = 'images/default.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                image_url = f'uploads/{filename}'
        
        product = Product(
            name=name, 
            description=description, 
            category=category, 
            price=price, 
            stock=stock, 
            image_url=image_url,
            user_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('user.my_products'))
    return render_template('shop/add_product.html')

@user_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@farmer_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('You can only edit your own products.', 'danger')
        return redirect(url_for('user.my_products'))
        
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.category = request.form.get('category')
        product.price = float(request.form.get('price'))
        product.stock = int(request.form.get('stock'))
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                product.image_url = f'uploads/{filename}'
                
        db.session.commit()
        flash('Product updated successfully', 'success')
        return redirect(url_for('user.my_products'))
    return render_template('shop/edit_product.html', product=product)

@user_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@login_required
@farmer_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('You can only delete your own products.', 'danger')
        return redirect(url_for('user.my_products'))
    
    # Delete related items
    CartItem.query.filter_by(product_id=product_id).delete()
    WishlistItem.query.filter_by(product_id=product_id).delete()
    OrderItem.query.filter_by(product_id=product_id).delete()
    Review.query.filter_by(product_id=product_id).delete()
    
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted', 'info')
    return redirect(url_for('user.my_products'))

@user_bp.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    product = Product.query.get_or_404(product_id)
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    if not rating:
        flash('Please select a rating.', 'danger')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    try:
        rating_val = int(rating)
    except (ValueError, TypeError, AttributeError):
        flash('Invalid rating submitted.', 'danger')
        return redirect(url_for('main.product_detail', product_id=product_id))

    review = Review(
        user_id=current_user.id,
        product_id=product_id,
        rating=rating_val,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()
    flash('Review submitted successfully!', 'success')
    return redirect(url_for('main.product_detail', product_id=product_id))
