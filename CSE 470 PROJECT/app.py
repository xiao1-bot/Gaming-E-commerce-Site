from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gaming_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'games'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'setups'), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    popularity_points = db.Column(db.Integer, default=0)
    profile_picture = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)
    banned_at = db.Column(db.DateTime)
    banned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    ban_reason = db.Column(db.Text)
    ban_duration_days = db.Column(db.Integer)  # NULL for permanent, number for temporary
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        if not self.is_banned:
            return True
        
        # Check if temporary ban has expired
        if self.ban_duration_days and self.banned_at:
            ban_end_date = self.banned_at + timedelta(days=self.ban_duration_days)
            if datetime.utcnow() > ban_end_date:
                # Ban has expired, auto-unban
                self.is_banned = False
                self.banned_at = None
                self.banned_by = None
                self.ban_reason = None
                self.ban_duration_days = None
                db.session.commit()
                return True
        
        return False
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    genre = db.Column(db.String(100))
    platform = db.Column(db.String(100))
    release_date = db.Column(db.Date)
    image_url = db.Column(db.String(200))
    voice_preview_url = db.Column(db.String(200))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    content = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='reviews')
    game = db.relationship('Game', backref='reviews')

class ReviewVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'

class ReviewComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='comments')
    review = db.relationship('Review', backref='comments')

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    user = db.relationship('User', backref='cart_items')
    game = db.relationship('Game', backref='cart_items')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    price_paid = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='purchases')
    game = db.relationship('Game', backref='purchases')

class GameLending(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    lend_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime)
    is_returned = db.Column(db.Boolean, default=False)
    is_overdue = db.Column(db.Boolean, default=False)
    overdue_notification_sent = db.Column(db.Boolean, default=False)
    
    lender = db.relationship('User', foreign_keys=[lender_id], backref='lent_games')
    borrower = db.relationship('User', foreign_keys=[borrower_id], backref='borrowed_games')
    game = db.relationship('Game', backref='lending_records')

class SetupPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    cleanest_votes = db.Column(db.Integer, default=0)
    rgb_votes = db.Column(db.Integer, default=0)
    budget_votes = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='setup_posts')

class SetupVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    setup_id = db.Column(db.Integer, db.ForeignKey('setup_post.id'), nullable=False)
    vote_type = db.Column(db.String(20), nullable=False)  # 'like', 'dislike', 'cleanest', 'rgb', 'budget'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), default='general')  # 'overdue', 'admin', 'general'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')

class AdminNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), default='general')  # 'overdue_user', 'system'
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    related_user = db.relationship('User', backref='admin_notifications')

class NotifyRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    discount_amount = db.Column(db.Float, nullable=False)  # Amount in dollars
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='vouchers')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utility functions for overdue games and notifications
def check_overdue_games():
    """Check for overdue games and send notifications"""
    current_time = datetime.utcnow()
    overdue_lendings = GameLending.query.filter(
        GameLending.borrower_id.isnot(None),
        GameLending.is_returned == False,
        GameLending.return_date < current_time,
        GameLending.overdue_notification_sent == False
    ).all()
    
    for lending in overdue_lendings:
        # Mark as overdue
        lending.is_overdue = True
        lending.overdue_notification_sent = True
        
        # Send notification to borrower
        borrower_notification = Notification(
            user_id=lending.borrower_id,
            title="Game Overdue - Return Required",
            message=f"Your borrowed game '{lending.game.title}' is overdue. Please return it immediately to avoid penalties.",
            notification_type='overdue'
        )
        db.session.add(borrower_notification)
        
        # Send notification to admin
        admin_notification = AdminNotification(
            title="User Overdue - Action Required",
            message=f"User {lending.borrower.username} has not returned '{lending.game.title}' on time. Consider banning if this continues.",
            notification_type='overdue_user',
            related_user_id=lending.borrower_id
        )
        db.session.add(admin_notification)
        
        # Flash message for borrower if they're currently logged in
        if lending.borrower.is_authenticated():
            flash(f'WARNING: Your borrowed game "{lending.game.title}" is overdue! Please return it immediately.', 'warning')
    
    db.session.commit()
    return len(overdue_lendings)

def send_overdue_warning(user_id, game_title):
    """Send a warning notification to a user about an overdue game"""
    notification = Notification(
        user_id=user_id,
        title="Final Warning - Game Overdue",
        message=f"Your borrowed game '{game_title}' is still overdue. This is your final warning before potential account suspension.",
        notification_type='overdue'
    )
    db.session.add(notification)
    db.session.commit()

def ban_user(user_id, admin_id, reason, duration_days=None):
    """Ban a user from the system"""
    user = User.query.get(user_id)
    if user and not user.is_admin:
        user.is_banned = True
        user.banned_at = datetime.utcnow()
        user.banned_by = admin_id
        user.ban_reason = reason
        user.ban_duration_days = duration_days  # None for permanent, number for temporary
        
        # Send notification to banned user
        if duration_days:
            ban_message = f"Your account has been temporarily banned for {duration_days} days. Reason: {reason}. Contact support for more information."
        else:
            ban_message = f"Your account has been permanently banned. Reason: {reason}. Contact support for more information."
        
        notification = Notification(
            user_id=user_id,
            title="Account Banned",
            message=ban_message,
            notification_type='admin'
        )
        db.session.add(notification)
        
        # Send notification to admin
        duration_text = f"for {duration_days} days" if duration_days else "permanently"
        admin_notification = AdminNotification(
            title="User Banned Successfully",
            message=f"User {user.username} has been banned {duration_text}. Reason: {reason}",
            notification_type='system',
            related_user_id=user_id
        )
        db.session.add(admin_notification)
        
        db.session.commit()
        return True
    return False

def unban_user(user_id, admin_id):
    """Unban a user from the system"""
    user = User.query.get(user_id)
    if user and user.is_banned:
        user.is_banned = False
        user.banned_at = None
        user.banned_by = None
        user.ban_reason = None
        user.ban_duration_days = None
        
        # Send notification to unbanned user
        notification = Notification(
            user_id=user_id,
            title="Account Unbanned",
            message="Your account has been unbanned. You can now access the platform again.",
            notification_type='admin'
        )
        db.session.add(notification)
        
        # Send notification to admin
        admin_notification = AdminNotification(
            title="User Unbanned Successfully",
            message=f"User {user.username} has been unbanned.",
            notification_type='system',
            related_user_id=user_id
        )
        db.session.add(admin_notification)
        
        db.session.commit()
        return True
    return False

def schedule_overdue_check():
    """Scheduled task to check for overdue games (can be called by a cron job or scheduler)"""
    try:
        overdue_count = check_overdue_games()
        print(f"Scheduled overdue check completed. Found {overdue_count} overdue items.")
        return overdue_count
    except Exception as e:
        print(f"Error in scheduled overdue check: {e}")
        return 0

def check_expired_bans():
    """Check for expired temporary bans and auto-unban users"""
    current_time = datetime.utcnow()
    expired_bans = User.query.filter(
        User.is_banned == True,
        User.ban_duration_days.isnot(None),
        User.banned_at.isnot(None)
    ).all()
    
    for user in expired_bans:
        ban_end_date = user.banned_at + timedelta(days=user.ban_duration_days)
        if current_time > ban_end_date:
            # Ban has expired, auto-unban
            user.is_banned = False
            user.banned_at = None
            user.banned_by = None
            user.ban_reason = None
            user.ban_duration_days = None
            
            # Send notification to user
            notification = Notification(
                user_id=user.id,
                title="Account Unbanned",
                message="Your temporary ban has expired. Your account is now active again.",
                notification_type='admin'
            )
            db.session.add(notification)
            
            # Send notification to admin
            admin_notification = AdminNotification(
                title="User Auto-Unbanned",
                message=f"User {user.username} has been automatically unbanned after their temporary ban expired.",
                notification_type='system',
                related_user_id=user.id
            )
            db.session.add(admin_notification)
    
    if expired_bans:
        db.session.commit()
        return len(expired_bans)
    return 0

# Utility: Build ban context for template

def build_ban_context(user: User):
    reason = user.ban_reason or 'No reason provided'
    is_permanent = user.ban_duration_days is None
    remaining_days = None
    until_date_str = None
    if user.ban_duration_days and user.banned_at:
        ban_end_date = user.banned_at + timedelta(days=user.ban_duration_days)
        delta = ban_end_date - datetime.utcnow()
        # Ceiling of days remaining
        remaining_days = max(1, delta.days + (1 if delta.seconds > 0 else 0))
        until_date_str = ban_end_date.strftime('%Y-%m-%d')
    return {
        'reason': reason,
        'is_permanent': is_permanent,
        'remaining_days': remaining_days,
        'until_date': until_date_str,
    }

@app.route('/banned')
@login_required
def banned():
    # Auto-unban if expired
    check_expired_bans()
    if not current_user.is_banned:
        return redirect(url_for('index'))
    ctx = build_ban_context(current_user)
    return render_template(
        'banned.html',
        user=current_user,
        reason=ctx['reason'],
        is_permanent=ctx['is_permanent'],
        remaining_days=ctx['remaining_days'],
        until_date=ctx['until_date']
    )

# Routes
@app.before_request
def check_overdue_before_request():
    """Check for overdue games and expired bans before each request"""
    # Skip for static and early cases without endpoint
    if request.endpoint in (None, 'static'):
        return

    # Always process expired bans first
    if current_user.is_authenticated:
        check_expired_bans()
        # Enforce ban site-wide by redirecting to banned page, except for allowed endpoints
        if getattr(current_user, 'is_banned', False):
            allowed_endpoints = {
                'logout', 'banned', 'static', 'mark_notification_read', 'clear_all_notifications'
            }
            if request.endpoint not in allowed_endpoints:
                return redirect(url_for('banned'))

    if current_user.is_authenticated and not current_user.is_admin:
        check_overdue_games()

@app.route('/')
def index():
    # Check for overdue games if user is logged in
    if current_user.is_authenticated and not current_user.is_admin:
        check_overdue_games()
    
    games = Game.query.filter_by(is_available=True).limit(8).all()
    featured_setup = SetupPost.query.filter_by(is_featured=True).first()
    if not featured_setup:
        # Feature the setup with most likes
        featured_setup = SetupPost.query.order_by(SetupPost.likes.desc()).first()
        if featured_setup:
            featured_setup.is_featured = True
            db.session.commit()
    
    return render_template('index.html', games=games, featured_setup=featured_setup)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # If user was temporarily banned, check if ban expired and auto-unban
            if user.is_banned and user.ban_duration_days and user.banned_at:
                ban_end_date = user.banned_at + timedelta(days=user.ban_duration_days)
                if datetime.utcnow() > ban_end_date:
                    # Auto-unban
                    user.is_banned = False
                    user.banned_at = None
                    user.banned_by = None
                    user.ban_reason = None
                    user.ban_duration_days = None
                    db.session.commit()
            
            # If still banned, show banned notice page and block login
            if user.is_banned:
                remaining_days = None
                until_date_str = None
                if user.ban_duration_days and user.banned_at:
                    ban_end_date = user.banned_at + timedelta(days=user.ban_duration_days)
                    delta = ban_end_date - datetime.utcnow()
                    remaining_days = max(1, delta.days + (1 if delta.seconds > 0 else 0))
                    until_date_str = ban_end_date.strftime('%Y-%m-%d')
                return render_template(
                    'banned.html',
                    user=user,
                    reason=user.ban_reason or 'No reason provided',
                    is_permanent=(user.ban_duration_days is None),
                    remaining_days=remaining_days,
                    until_date=until_date_str
                )
            
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    purchased_games = [purchase.game for purchase in current_user.purchases]
    
    # Get user's active vouchers (not used)
    active_vouchers = Voucher.query.filter_by(
        user_id=current_user.id, 
        is_used=False
    ).order_by(Voucher.created_at.desc()).all()
    
    return render_template('profile.html', 
                         notifications=notifications, 
                         purchased_games=purchased_games,
                         active_vouchers=active_vouchers)

@app.route('/redeem_voucher', methods=['POST'])
@login_required
def redeem_voucher():
    voucher_type = request.form.get('voucher_type')
    
    # Define voucher costs and amounts
    voucher_costs = {
        'small': {'cost': 50, 'amount': 5.00},    # 50 points for $5 voucher
        'medium': {'cost': 100, 'amount': 12.00}, # 100 points for $12 voucher
        'large': {'cost': 200, 'amount': 25.00}   # 200 points for $25 voucher
    }
    
    if voucher_type not in voucher_costs:
        flash('Invalid voucher type')
        return redirect(url_for('profile'))
    
    cost = voucher_costs[voucher_type]['cost']
    amount = voucher_costs[voucher_type]['amount']
    
    if current_user.popularity_points < cost:
        flash(f'You need {cost} popularity points to redeem this voucher. You currently have {current_user.popularity_points} points.')
        return redirect(url_for('profile'))
    
    # Deduct points and create voucher
    current_user.popularity_points -= cost
    voucher = Voucher(
        user_id=current_user.id,
        discount_amount=amount
    )
    db.session.add(voucher)
    db.session.commit()
    
    flash(f'Voucher worth ${amount:.2f} redeemed successfully! {cost} popularity points deducted.')
    return redirect(url_for('redeem_vouchers_page'))

@app.route('/redeem_vouchers')
@login_required
def redeem_vouchers_page():
    return render_template('redeem_vouchers.html')

@app.route('/clear_notifications', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All notifications cleared!')
    return redirect(url_for('profile'))

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.bio = request.form.get('bio', '')
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Make filename unique by prefixing with user id and timestamp
                import time
                unique_filename = f"user_{current_user.id}_{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                current_user.profile_picture = unique_filename
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html')

@app.route('/games')
def games():
    page = request.args.get('page', 1, type=int)
    genre = request.args.get('genre')
    query = Game.query
    if genre:
        query = query.filter(Game.genre.ilike(f'%{genre.strip()}%'))
    games = query.order_by(Game.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('games.html', games=games, NotifyRequest=NotifyRequest)

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    reviews = Review.query.filter_by(game_id=game_id).all()
    user_review = None
    notify_requested = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(user_id=current_user.id, game_id=game_id).first()
        if not current_user.is_admin:
            notify_requested = NotifyRequest.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    return render_template('game_detail.html', game=game, reviews=reviews, user_review=user_review, notify_requested=notify_requested)

@app.route('/add_to_cart/<int:game_id>')
@login_required
def add_to_cart(game_id):
    if current_user.is_admin:
        flash('Admins cannot buy games.')
        return redirect(url_for('game_detail', game_id=game_id))
    # Prevent adding if already owned
    already_owned = Purchase.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if already_owned:
        flash('You already own this game.')
        return redirect(url_for('game_detail', game_id=game_id))
    existing_item = Cart.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if existing_item:
        flash('This game is already in your cart.')
        return redirect(url_for('game_detail', game_id=game_id))
    else:
        cart_item = Cart(user_id=current_user.id, game_id=game_id)
        db.session.add(cart_item)
    db.session.commit()
    flash('Game added to cart')
    return redirect(url_for('game_detail', game_id=game_id))

@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.game.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout')
@login_required
def checkout():
    if current_user.is_admin:
        flash('Admins cannot buy games.')
        return redirect(url_for('cart'))
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))
    
    total = sum(item.game.price * item.quantity for item in cart_items)
    
    # Get user's active vouchers
    active_vouchers = Voucher.query.filter_by(
        user_id=current_user.id, 
        is_used=False
    ).all()
    
    return render_template('checkout.html', 
                         cart_items=cart_items, 
                         total=total,
                         active_vouchers=active_vouchers)

@app.route('/process_checkout', methods=['POST'])
@login_required
def process_checkout():
    if current_user.is_admin:
        flash('Admins cannot buy games.')
        return redirect(url_for('cart'))
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))
    
    total = sum(item.game.price * item.quantity for item in cart_items)
    voucher_id = request.form.get('voucher_id')
    
    # Apply voucher if selected
    discount_amount = 0
    if voucher_id:
        voucher = Voucher.query.filter_by(
            id=voucher_id,
            user_id=current_user.id,
            is_used=False
        ).first()
        
        if voucher:
            discount_amount = voucher.discount_amount
            voucher.is_used = True
            voucher.used_at = datetime.utcnow()
        else:
            flash('Invalid voucher selected')
            return redirect(url_for('checkout'))
    
    final_total = max(0, total - discount_amount)
    
    # Process purchases
    for item in cart_items:
        purchase = Purchase(
            user_id=current_user.id,
            game_id=item.game_id,
            price_paid=item.game.price
        )
        db.session.add(purchase)
    
    # Clear cart
    Cart.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    if discount_amount > 0:
        flash(f'Purchase successful! ${discount_amount:.2f} discount applied. Total paid: ${final_total:.2f}')
    else:
        flash('Purchase successful!')
    
    return redirect(url_for('profile'))

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    Cart.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Cart cleared!')
    return redirect(url_for('cart'))

@app.route('/review_game/<int:game_id>', methods=['POST'])
@login_required
def review_game(game_id):
    if current_user.is_admin:
        flash('Admins cannot post reviews.')
        return redirect(url_for('game_detail', game_id=game_id))
    # Only allow review if user owns the game
    owns_game = Purchase.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if not owns_game:
        flash('You can only review games you own.')
        return redirect(url_for('game_detail', game_id=game_id))
    rating = int(request.form['rating'])
    content = request.form['content']
    existing_review = Review.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if existing_review:
        existing_review.rating = rating
        existing_review.content = content
    else:
        review = Review(
            user_id=current_user.id,
            game_id=game_id,
            rating=rating,
            content=content
        )
        db.session.add(review)
        # Award popularity points
        current_user.popularity_points += 50
    db.session.commit()
    flash('Review submitted successfully')
    return redirect(url_for('game_detail', game_id=game_id))

@app.route('/vote_review', methods=['POST'])
@login_required
def vote_review():
    review_id = int(request.form['review_id'])
    vote_type = request.form['vote_type']
    
    existing_vote = ReviewVote.query.filter_by(user_id=current_user.id, review_id=review_id).first()
    review = Review.query.get(review_id)
    
    if existing_vote:
        # Remove old vote
        if existing_vote.vote_type == 'like':
            review.likes -= 1
        else:
            review.dislikes -= 1
        
        if existing_vote.vote_type == vote_type:
            # Remove vote entirely
            db.session.delete(existing_vote)
        else:
            # Change vote
            existing_vote.vote_type = vote_type
            if vote_type == 'like':
                review.likes += 1
            else:
                review.dislikes += 1
    else:
        # New vote
        vote = ReviewVote(user_id=current_user.id, review_id=review_id, vote_type=vote_type)
        db.session.add(vote)
        
        if vote_type == 'like':
            review.likes += 1
        else:
            review.dislikes += 1
    
    # Award points to review author
    if vote_type == 'like':
        review.user.popularity_points += 5
    
    # Create notification
    if review.user_id != current_user.id:
        notification = Notification(
            user_id=review.user_id,
            title='Review Interaction',
            message=f'{current_user.username} {vote_type}d your review'
        )
        db.session.add(notification)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/comment_review', methods=['POST'])
@login_required
def comment_review():
    review_id = int(request.form['review_id'])
    content = request.form['content']
    
    comment = ReviewComment(
        user_id=current_user.id,
        review_id=review_id,
        content=content
    )
    db.session.add(comment)
    
    # Create notification
    review = Review.query.get(review_id)
    if review.user_id != current_user.id:
        notification = Notification(
            user_id=review.user_id,
            title='New Comment',
            message=f'{current_user.username} commented on your review'
        )
        db.session.add(notification)
    
    db.session.commit()
    return redirect(url_for('game_detail', game_id=review.game_id))

@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = ReviewComment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        flash('You are not authorized to edit this comment.')
        return redirect(url_for('game_detail', game_id=comment.review.game_id))
    if request.method == 'POST':
        new_content = request.form['content']
        comment.content = new_content
        db.session.commit()
        flash('Comment updated successfully!')
        return redirect(url_for('game_detail', game_id=comment.review.game_id))
    return render_template('edit_comment.html', comment=comment)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = ReviewComment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        flash('You are not authorized to delete this comment.')
        return redirect(url_for('game_detail', game_id=comment.review.game_id))
    game_id = comment.review.game_id
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted successfully!')
    return redirect(url_for('game_detail', game_id=game_id))

@app.route('/leaderboard')
def leaderboard():
    users = User.query.filter_by(is_admin=False).order_by(User.popularity_points.desc()).limit(20).all()
    return render_template('leaderboard.html', users=users)

@app.route('/lend_games')
@login_required
def lend_games():
    # Get user's purchased games that are PS3, PS4, or PS5
    purchased_games = db.session.query(Game).join(Purchase).filter(
        Purchase.user_id == current_user.id
    ).all()
    
    # Filter games by platform (PS3, PS4, PS5)
    ps_games = []
    for game in purchased_games:
        if game.platform:
            platforms = [p.strip() for p in game.platform.split(',')]
            if any(p in ['PS3', 'PS4', 'PS5'] for p in platforms):
                ps_games.append(game)
    
    # Get available lendings (not borrowed yet)
    available_lendings = GameLending.query.filter_by(borrower_id=None).all()
    
    # Get user's current lending posts
    user_lendings = GameLending.query.filter_by(lender_id=current_user.id).all()
    
    # Get borrowed games (games borrowed by current user)
    borrowed_games = GameLending.query.filter_by(borrower_id=current_user.id, is_returned=False).all()
    
    return render_template('lend_games.html', 
                         ps_games=ps_games, 
                         available_lendings=available_lendings,
                         user_lendings=user_lendings,
                         borrowed_games=borrowed_games)

@app.route('/lend_game/<int:game_id>')
@login_required
def lend_game(game_id):
    # Check if user owns the game
    purchase = Purchase.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if not purchase:
        flash('You do not own this game')
        return redirect(url_for('lend_games'))
    
    # Check if game is already being lent
    existing_lending = GameLending.query.filter_by(
        lender_id=current_user.id, 
        game_id=game_id,
        borrower_id=None
    ).first()
    
    if existing_lending:
        flash('This game is already available for lending')
        return redirect(url_for('lend_games'))
    
    # Check if game is currently borrowed
    borrowed_lending = GameLending.query.filter_by(
        lender_id=current_user.id, 
        game_id=game_id,
        is_returned=False
    ).filter(GameLending.borrower_id.isnot(None)).first()
    
    if borrowed_lending:
        flash('This game is currently borrowed and cannot be lent again')
        return redirect(url_for('lend_games'))
    
    # Check if game platform is supported (PS3, PS4, PS5)
    game = Game.query.get(game_id)
    if not game.platform:
        flash('This game does not have a platform specified')
        return redirect(url_for('lend_games'))
    
    platforms = [p.strip() for p in game.platform.split(',')]
    if not any(p in ['PS3', 'PS4', 'PS5'] for p in platforms):
        flash('Only PS3, PS4, and PS5 games can be lent')
        return redirect(url_for('lend_games'))
    
    lending = GameLending(lender_id=current_user.id, game_id=game_id)
    db.session.add(lending)
    db.session.commit()
    
    flash('Game is now available for lending')
    return redirect(url_for('lend_games'))

@app.route('/borrow_game/<int:lending_id>')
@login_required
def borrow_game(lending_id):
    lending = GameLending.query.get_or_404(lending_id)
    
    # Check if user is trying to borrow their own game
    if lending.lender_id == current_user.id:
        flash('You cannot borrow your own game')
        return redirect(url_for('lend_games'))
    
    if lending.borrower_id:
        flash('Game is already borrowed')
        return redirect(url_for('lend_games'))
    
    # Redirect to duration selection page
    return render_template('select_duration.html', lending=lending)

@app.route('/process_borrow/<int:lending_id>', methods=['POST'])
@login_required
def process_borrow(lending_id):
    lending = GameLending.query.get_or_404(lending_id)
    
    # Check if user is trying to borrow their own game
    if lending.lender_id == current_user.id:
        flash('You cannot borrow your own game')
        return redirect(url_for('lend_games'))
    
    if lending.borrower_id:
        flash('Game is already borrowed')
        return redirect(url_for('lend_games'))
    
    # Get duration from form
    duration_days = request.form.get('duration_days', type=int)
    if not duration_days or duration_days < 1 or duration_days > 30:
        flash('Please select a valid duration between 1 and 30 days')
        return redirect(url_for('borrow_game', lending_id=lending_id))
    
    # Calculate return date
    return_date = datetime.utcnow() + timedelta(days=duration_days)
    
    # Process the borrowing
    lending.borrower_id = current_user.id
    lending.return_date = return_date
    db.session.commit()
    
    flash(f'Game borrowed successfully for {duration_days} days. Please return by {return_date.strftime("%Y-%m-%d")}')
    return redirect(url_for('lend_games'))

@app.route('/delete_lending/<int:lending_id>', methods=['POST'])
@login_required
def delete_lending(lending_id):
    lending = GameLending.query.get_or_404(lending_id)
    
    # Check if user owns this lending post
    if lending.lender_id != current_user.id:
        flash('You can only delete your own lending posts')
        return redirect(url_for('lend_games'))
    
    # Check if game is currently borrowed
    if lending.borrower_id and not lending.is_returned:
        flash('Cannot delete lending post while game is borrowed')
        return redirect(url_for('lend_games'))
    
    db.session.delete(lending)
    db.session.commit()
    
    flash('Lending post deleted successfully')
    return redirect(url_for('lend_games'))

@app.route('/return_game/<int:lending_id>', methods=['POST'])
@login_required
def return_game(lending_id):
    lending = GameLending.query.get_or_404(lending_id)
    
    # Check if user is the borrower
    if lending.borrower_id != current_user.id:
        flash('You can only return games you borrowed')
        return redirect(url_for('lend_games'))
    
    # Check if game is already returned
    if lending.is_returned:
        flash('This game is already returned')
        return redirect(url_for('lend_games'))
    
    # Mark game as returned
    lending.is_returned = True
    db.session.commit()
    
    flash('Game returned successfully')
    return redirect(url_for('lend_games'))

@app.route('/ai_recommendations')
@login_required
def ai_recommendations():
    # Simple AI recommendation based on user's purchase history and ratings
    user_purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    user_reviews = Review.query.filter_by(user_id=current_user.id).all()
    
    # Get genres from purchased games
    purchased_genres = []
    for purchase in user_purchases:
        if purchase.game.genre:
            purchased_genres.append(purchase.game.genre)
    
    # Get highly rated genres from reviews
    high_rated_genres = []
    for review in user_reviews:
        if review.rating >= 4 and review.game.genre:
            high_rated_genres.append(review.game.genre)
    
    # Combine and find most common genres
    all_genres = purchased_genres + high_rated_genres
    if all_genres:
        most_common_genre = max(set(all_genres), key=all_genres.count)
        recommendations = Game.query.filter_by(genre=most_common_genre, is_available=True).limit(6).all()
    else:
        # Fallback to popular games
        recommendations = Game.query.filter_by(is_available=True).limit(6).all()
    
    return render_template('ai_recommendations.html', recommendations=recommendations)

@app.route('/setups')
def setups():
    setups = SetupPost.query.order_by(SetupPost.created_at.desc()).all()
    return render_template('setups.html', setups=setups)

@app.route('/post_setup', methods=['GET', 'POST'])
@login_required
def post_setup():
    if current_user.is_admin:
        flash('Admins cannot post setups.')
        return redirect(url_for('setups'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image_url = '/static/uploads/setups/default_setup.jpg'  # Default image
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                import time
                filename = secure_filename(file.filename)
                unique_filename = f"setup_{current_user.id}_{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'setups', unique_filename))
                image_url = f'/static/uploads/setups/{unique_filename}'
        setup = SetupPost(
            user_id=current_user.id,
            title=title,
            description=description,
            image_url=image_url
        )
        db.session.add(setup)
        db.session.commit()
        flash('Setup posted successfully')
        return redirect(url_for('setups'))
    return render_template('post_setup.html')

@app.route('/vote_setup', methods=['POST'])
@login_required
def vote_setup():
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admins cannot vote on setups.'}), 403
    setup_id = int(request.form['setup_id'])
    vote_type = request.form['vote_type']
    
    setup = SetupPost.query.get(setup_id)
    if not setup:
        return jsonify({'success': False, 'message': 'Setup not found'}), 404

    # Initialize counters to 0 if somehow None
    setup.likes = setup.likes or 0
    setup.dislikes = setup.dislikes or 0
    setup.cleanest_votes = setup.cleanest_votes or 0
    setup.rgb_votes = setup.rgb_votes or 0
    setup.budget_votes = setup.budget_votes or 0

    reaction_types = ['like', 'dislike']
    badge_types = ['cleanest', 'rgb', 'budget']

    def clamp_non_negative(value: int) -> int:
        return value if value > 0 else 0

    if vote_type in reaction_types:
        # Handle like/dislike independently from badges
        existing_reaction = SetupVote.query.filter(
            SetupVote.user_id == current_user.id,
            SetupVote.setup_id == setup_id,
            SetupVote.vote_type.in_(reaction_types)
        ).first()

        if existing_reaction:
            # remove previous reaction
            if existing_reaction.vote_type == 'like':
                setup.likes = clamp_non_negative(setup.likes - 1)
            elif existing_reaction.vote_type == 'dislike':
                setup.dislikes = clamp_non_negative(setup.dislikes - 1)

            if existing_reaction.vote_type == vote_type:
                # toggle off
                db.session.delete(existing_reaction)
            else:
                # switch reaction
                existing_reaction.vote_type = vote_type
                if vote_type == 'like':
                    setup.likes += 1
                else:
                    setup.dislikes += 1
        else:
            # new reaction
            db.session.add(SetupVote(user_id=current_user.id, setup_id=setup_id, vote_type=vote_type))
            if vote_type == 'like':
                setup.likes += 1
            else:
                setup.dislikes += 1

    elif vote_type in badge_types:
        # Handle cleanest/rgb/budget independently from reactions
        existing_badge = SetupVote.query.filter(
            SetupVote.user_id == current_user.id,
            SetupVote.setup_id == setup_id,
            SetupVote.vote_type.in_(badge_types)
        ).first()

        if existing_badge:
            # remove previous badge vote
            if existing_badge.vote_type == 'cleanest':
                setup.cleanest_votes = clamp_non_negative(setup.cleanest_votes - 1)
            elif existing_badge.vote_type == 'rgb':
                setup.rgb_votes = clamp_non_negative(setup.rgb_votes - 1)
            elif existing_badge.vote_type == 'budget':
                setup.budget_votes = clamp_non_negative(setup.budget_votes - 1)

            if existing_badge.vote_type == vote_type:
                # toggle off
                db.session.delete(existing_badge)
            else:
                # switch badge vote
                existing_badge.vote_type = vote_type
                if vote_type == 'cleanest':
                    setup.cleanest_votes += 1
                elif vote_type == 'rgb':
                    setup.rgb_votes += 1
                else:
                    setup.budget_votes += 1
        else:
            # new badge vote
            db.session.add(SetupVote(user_id=current_user.id, setup_id=setup_id, vote_type=vote_type))
            if vote_type == 'cleanest':
                setup.cleanest_votes += 1
            elif vote_type == 'rgb':
                setup.rgb_votes += 1
            else:
                setup.budget_votes += 1
    else:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    db.session.commit()
    return jsonify({'success': True})

@app.route('/edit_setup/<int:setup_id>', methods=['GET', 'POST'])
@login_required
def edit_setup(setup_id):
    setup = SetupPost.query.get_or_404(setup_id)
    if current_user.id != setup.user_id and not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('setups'))
    if request.method == 'POST':
        setup.title = request.form['title']
        setup.description = request.form['description']
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                import time
                filename = secure_filename(file.filename)
                unique_filename = f"setup_{current_user.id}_{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'setups', unique_filename))
                setup.image_url = f'/static/uploads/setups/{unique_filename}'
        db.session.commit()
        flash('Setup updated successfully')
        return redirect(url_for('setups'))
    return render_template('edit_setup.html', setup=setup)

@app.route('/delete_setup/<int:setup_id>', methods=['POST'])
@login_required
def delete_setup(setup_id):
    setup = SetupPost.query.get_or_404(setup_id)
    if current_user.id != setup.user_id and not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('setups'))
    db.session.delete(setup)
    db.session.commit()
    flash('Setup deleted successfully')
    return redirect(url_for('setups'))

@app.route('/notify_when_available/<int:game_id>', methods=['POST'])
@login_required
def notify_when_available(game_id):
    existing = NotifyRequest.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if not existing:
        req = NotifyRequest(user_id=current_user.id, game_id=game_id)
        db.session.add(req)
        db.session.commit()
        flash('You will be notified when this game is available.')
    else:
        flash('You have already requested notification for this game.')
    return redirect(url_for('game_detail', game_id=game_id))

# Admin Routes
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    games = Game.query.order_by(Game.created_at.desc()).all()
    users = User.query.all()
    notify_counts = {g.id: NotifyRequest.query.filter_by(game_id=g.id).count() for g in games}
    return render_template('admin.html', games=games, users=users, notify_counts=notify_counts)

@app.route('/admin/add_game', methods=['GET', 'POST'])
@login_required
def add_game():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    if request.method == 'POST':
        genre = request.form.getlist('genre')
        genre_str = ', '.join(genre)
        game = Game(
            title=request.form['title'],
            description=request.form['description'],
            price=float(request.form['price']),
            genre=genre_str,
            platform=request.form['platform'],
            image_url=request.form.get('image_url', '/static/images/default_game.jpg'),
            voice_preview_url=request.form.get('voice_preview_url', '')
        )
        db.session.add(game)
        db.session.commit()
        # Send notification to all users
        users = User.query.all()
        for user in users:
            notification = Notification(
                user_id=user.id,
                title='New Game Added!',
                message=f'Check out the new game: {game.title}'
            )
            db.session.add(notification)
        db.session.commit()
        flash('Game added successfully and notifications sent')
        return redirect(url_for('admin'))
    return render_template('add_game.html')

@app.route('/admin/edit_game/<int:game_id>', methods=['GET', 'POST'])
@login_required
def edit_game(game_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    game = Game.query.get_or_404(game_id)
    if request.method == 'POST':
        genre = request.form.getlist('genre')
        genre_str = ', '.join(genre)
        game.genre = genre_str
        game.price = float(request.form['price'])
        game.platform = request.form['platform']
        game.description = request.form['description']
        game.image_url = request.form['image_url']
        game.voice_preview_url = request.form['voice_preview_url']
        prev_available = game.is_available
        game.is_available = request.form['is_available'] == 'True'
        db.session.commit()
        # Notify users if status changed from not available to available
        if not prev_available and game.is_available:
            notify_requests = NotifyRequest.query.filter_by(game_id=game.id).all()
            for req in notify_requests:
                notification = Notification(
                    user_id=req.user_id,
                    title='Game Available!',
                    message=f'The game "{game.title}" is now available!'
                )
                db.session.add(notification)
                db.session.delete(req)
            db.session.commit()
        flash('Game updated successfully')
        return redirect(url_for('admin'))
    return render_template('edit_game.html', game=game)

@app.route('/admin/notify_users/<int:game_id>', methods=['POST'])
@login_required
def admin_notify_users(game_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('admin'))
    
    game = Game.query.get_or_404(game_id)
    users = User.query.filter_by(is_banned=False).all()
    for user in users:
        notification = Notification(
            user_id=user.id,
            title='Game Update',
            message=f'Check out updates for: {game.title}'
        )
        db.session.add(notification)
    db.session.commit()
    flash(f'Notifications sent to {len(users)} users')
    return redirect(url_for('admin'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    # Check for overdue games
    overdue_count = check_overdue_games()
    
    users = User.query.all()
    overdue_users = []
    
    # Get users with overdue games
    for user in users:
        overdue_games = GameLending.query.filter(
            GameLending.borrower_id == user.id,
            GameLending.is_overdue == True,
            GameLending.is_returned == False
        ).all()
        if overdue_games:
            overdue_users.append({
                'user': user,
                'overdue_games': overdue_games,
                'overdue_count': len(overdue_games)
            })
    
    return render_template('admin_users.html', users=users, overdue_users=overdue_users, overdue_count=overdue_count, timedelta=timedelta)

@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
@login_required
def admin_ban_user(user_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    reason = request.form.get('reason', 'No reason provided')
    ban_type = request.form.get('ban_type', 'permanent')
    duration_days = None
    
    if ban_type == 'temporary':
        duration_days = request.form.get('duration_days', type=int)
        if not duration_days or duration_days < 1 or duration_days > 365:
            flash('Please enter a valid duration between 1 and 365 days')
            return redirect(url_for('admin_users'))
    
    if ban_user(user_id, current_user.id, reason, duration_days):
        if duration_days:
            flash(f'User banned successfully for {duration_days} days')
        else:
            flash('User banned permanently')
    else:
        flash('Failed to ban user')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/ban_user_page/<int:user_id>')
@login_required
def admin_ban_user_page(user_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot ban admin users')
        return redirect(url_for('admin_users'))
    
    return render_template('ban_user.html', user=user)

@app.route('/admin/unban_user/<int:user_id>', methods=['POST'])
@login_required
def admin_unban_user(user_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    if unban_user(user_id, current_user.id):
        flash('User unbanned successfully')
    else:
        flash('Failed to unban user')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/notifications')
@login_required
def admin_notifications():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    notifications = AdminNotification.query.order_by(AdminNotification.created_at.desc()).all()
    return render_template('admin_notifications.html', notifications=notifications)

@app.route('/admin/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def admin_mark_notification_read(notification_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    notification = AdminNotification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    
    return redirect(url_for('admin_notifications'))

@app.route('/admin/check_overdue')
@login_required
def admin_check_overdue():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    overdue_count = check_overdue_games()
    flash(f'Checked for overdue games. Found {overdue_count} overdue items.')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/check_expired_bans')
@login_required
def admin_check_expired_bans():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    expired_count = check_expired_bans()
    flash(f'Checked for expired bans. Unbanned {expired_count} users.')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/send_global_notification', methods=['POST'])
@login_required
def send_global_notification():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    message = request.form.get('message', '').strip()
    if not message:
        flash('Please enter a message for the notification')
        return redirect(url_for('admin'))
    
    # Get all non-banned users
    users = User.query.filter_by(is_banned=False).all()
    
    # Create notification for each user
    for user in users:
        notification = Notification(
            user_id=user.id,
            title='Global Notification',
            message=message,
            notification_type='general'
        )
        db.session.add(notification)
    
    db.session.commit()
    flash(f'Global notification sent to {len(users)} users')
    return redirect(url_for('admin'))

@app.route('/notifications')
@login_required
def user_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
    
    return redirect(url_for('user_notifications'))

@app.route('/clear_all_notifications', methods=['POST'])
@login_required
def clear_all_notifications():
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All notifications cleared')
    return redirect(url_for('user_notifications'))

# Test route for creating overdue games (remove in production)
@app.route('/test/create_overdue/<int:lending_id>')
@login_required
def test_create_overdue(lending_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    lending = GameLending.query.get_or_404(lending_id)
    if lending.borrower_id and not lending.is_returned:
        # Set return date to yesterday to make it overdue
        lending.return_date = datetime.utcnow() - timedelta(days=1)
        lending.overdue_notification_sent = False
        db.session.commit()
        
        # Trigger overdue check
        check_overdue_games()
        flash(f'Made game "{lending.game.title}" overdue for testing')
    else:
        flash('Game is not currently borrowed')
    
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@gaming.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True)
