from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    try:
        if str(user_id).startswith('admin_'):
            return Admin.query.get(int(user_id.split('_')[1]))
        elif str(user_id).startswith('user_'):
            return User.query.get(int(user_id.split('_')[1]))
        else:
            # Fallback for old sessions
            return User.query.get(int(user_id))
    except (ValueError, AttributeError):
        return getattr(User.query, 'get')(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer') # 'customer' or 'farmer'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def get_id(self):
        return f"user_{self.id}"
    
    products = db.relationship('Product', backref='seller', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False) # e.g., 'fertilizers', 'pesticides', 'irrigation', 'seeds'
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255), nullable=True, default='images/default.jpg')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Admin/Farmer who added it
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        return sum([r.rating for r in self.reviews]) / len(self.reviews)

    @property
    def total_reviews(self):
        return len(self.reviews)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    user = db.relationship('User', backref='reviews', lazy=True)
    product = db.relationship('Product', backref='reviews', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Confirmed, Shipped, Delivered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    payment = db.relationship('Payment', backref='order', uselist=False, lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False) # Price at the time of purchase

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    @property
    def role(self):
        return 'admin'
        
    def get_id(self):
        return f"admin_{self.id}"

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    razorpay_order_id = db.Column(db.String(100), nullable=False)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    razorpay_signature = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Success, Failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    user = db.relationship('User', backref='payments', lazy=True)
    # order relationship is now defined in the Order model
