from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from sqlalchemy.orm import joinedload

from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from models import Product, Order, Admin, User, Message, CartItem, WishlistItem, OrderItem, Payment, Review
from extensions import db, bcrypt

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def admin_protect():
    if request.endpoint and request.endpoint != 'admin.login':
        if not current_user.is_authenticated or getattr(current_user, 'role', None) != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin.login'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and getattr(current_user, 'role', None) == 'admin':
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('admin_email')
        password = request.form.get('admin_password')
        admin = Admin.query.filter_by(email=email).first()
        if admin and bcrypt.check_password_hash(admin.password_hash, password):
            login_user(admin)
            flash('Admin logged in successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Login unsuccessful. Please check credentials.', 'danger')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
def dashboard():
    products = Product.query.options(joinedload(Product.seller)).all()
    user_count = User.query.count()
    message_count = Message.query.count()
    order_count = Order.query.count()
    return render_template('admin/dashboard.html', 
                         products=products, 
                         user_count=user_count, 
                         message_count=message_count,
                         order_count=order_count)

@admin_bp.route('/product/add', methods=['GET', 'POST'])
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
        
        product = Product(name=name, description=description, category=category, price=price, stock=stock, image_url=image_url)
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/add_product.html')

@admin_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
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
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/edit_product.html', product=product)

@admin_bp.route('/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Delete any related items that depend on this product to prevent NOT NULL IntegrityErrors
    CartItem.query.filter_by(product_id=product_id).delete()
    WishlistItem.query.filter_by(product_id=product_id).delete()
    OrderItem.query.filter_by(product_id=product_id).delete()
    Review.query.filter_by(product_id=product_id).delete()
    
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/users')
def users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/messages')
def messages():
    all_messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('admin/messages.html', messages=all_messages)

@admin_bp.route('/orders')
def orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=all_orders)

@admin_bp.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        # Lock status if already delivered
        if order.status == 'Delivered':
            flash('This order has already been Delivered and its status is now locked.', 'warning')
            return redirect(url_for('admin.order_detail', order_id=order.id))
            
        new_status = request.form.get('status')
        if new_status:
            # Inventory Management
            if new_status == 'Delivered' and order.status != 'Delivered':
                for item in order.items:
                    if item.product.stock < item.quantity:
                        flash(f'Warning: Insufficient stock for {item.product.name}. Marking as Delivered anyway.', 'warning')
                    item.product.stock -= item.quantity
            
            # Replenish stock if status moves from Delivered back to something else
            if order.status == 'Delivered' and new_status != 'Delivered':
                for item in order.items:
                    item.product.stock += item.quantity

            order.status = new_status
            db.session.commit()
            flash(f'Order #{order.id} status updated to {new_status}', 'success')
            return redirect(url_for('admin.order_detail', order_id=order.id))
    return render_template('admin/order_detail.html', order=order)

@admin_bp.route('/order/delete/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    # Automatically deletes associated OrderItems and Payment via cascade="all, delete-orphan"
    db.session.delete(order)
    db.session.commit()
    flash(f'Order #{order_id} deleted successfully.', 'info')
    return redirect(url_for('admin.orders'))

@admin_bp.route('/transactions')
@login_required
def transactions():
    all_payments = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/transactions.html', payments=all_payments)
