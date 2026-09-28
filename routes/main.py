from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import Product, Message
from extensions import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Only frequently added products (most recent 8)
    products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    return render_template('shop/index.html', products=products)

@main_bp.route('/products')
def products():
    category = request.args.get('category')
    search_query = request.args.get('q')
    
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search_query:
        # Simple SQLite insensitive LIKE search
        query = query.filter(Product.name.ilike(f"%{search_query}%"))
        
    products = query.order_by(Product.created_at.desc()).all()
    return render_template('shop/products.html', products=products, search_query=search_query)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('shop/product_detail.html', product=product)

@main_bp.route('/about')
def about():
    return render_template('shop/about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message_body = request.form.get('message')
        
        if name and email and message_body:
            msg = Message(name=name, email=email, message=message_body)
            db.session.add(msg)
            db.session.commit()
            flash('Your message has been sent successfully! We will get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
        else:
            flash('Please fill in all fields.', 'danger')
            
    return render_template('shop/contact.html')
