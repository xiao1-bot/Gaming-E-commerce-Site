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
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
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
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('profile.html', notifications=notifications)

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
    games = Game.query.filter_by(is_available=True).paginate(
        page=page, per_page=12, error_out=False
    )
    return render_template('games.html', games=games)

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    reviews = Review.query.filter_by(game_id=game_id).all()
    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    
    return render_template('game_detail.html', game=game, reviews=reviews, user_review=user_review)

@app.route('/add_to_cart/<int:game_id>')
@login_required
def add_to_cart(game_id):
    # Prevent adding if already owned
    already_owned = Purchase.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if already_owned:
        flash('You already own this game.')
        return redirect(url_for('game_detail', game_id=game_id))
    existing_item = Cart.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if existing_item:
        existing_item.quantity += 1
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
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
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
    
    flash('Purchase successful!')
    return redirect(url_for('profile'))

@app.route('/review_game/<int:game_id>', methods=['POST'])
@login_required
def review_game(game_id):
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
        current_user.popularity_points += 10
    
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
        review.user.popularity_points += 2
    
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

@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.popularity_points.desc()).limit(20).all()
    return render_template('leaderboard.html', users=users)

@app.route('/lend_games')
@login_required
def lend_games():
    # Get user's purchased games
    purchased_games = db.session.query(Game).join(Purchase).filter(Purchase.user_id == current_user.id).all()
    available_lendings = GameLending.query.filter_by(borrower_id=None).all()
    
    return render_template('lend_games.html', purchased_games=purchased_games, available_lendings=available_lendings)

@app.route('/lend_game/<int:game_id>')
@login_required
def lend_game(game_id):
    # Check if user owns the game
    purchase = Purchase.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if not purchase:
        flash('You do not own this game')
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
    
    if lending.borrower_id:
        flash('Game is already borrowed')
        return redirect(url_for('lend_games'))
    
    lending.borrower_id = current_user.id
    db.session.commit()
    
    flash('Game borrowed successfully')
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
    setup_id = int(request.form['setup_id'])
    vote_type = request.form['vote_type']
    
    existing_vote = SetupVote.query.filter_by(user_id=current_user.id, setup_id=setup_id).first()
    setup = SetupPost.query.get(setup_id)
    
    if existing_vote:
        # Remove old vote
        if existing_vote.vote_type == 'like':
            setup.likes -= 1
        elif existing_vote.vote_type == 'dislike':
            setup.dislikes -= 1
        elif existing_vote.vote_type == 'cleanest':
            setup.cleanest_votes -= 1
        elif existing_vote.vote_type == 'rgb':
            setup.rgb_votes -= 1
        elif existing_vote.vote_type == 'budget':
            setup.budget_votes -= 1
        
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
        else:
            existing_vote.vote_type = vote_type
            if vote_type == 'like':
                setup.likes += 1
            elif vote_type == 'dislike':
                setup.dislikes += 1
            elif vote_type == 'cleanest':
                setup.cleanest_votes += 1
            elif vote_type == 'rgb':
                setup.rgb_votes += 1
            elif vote_type == 'budget':
                setup.budget_votes += 1
    else:
        vote = SetupVote(user_id=current_user.id, setup_id=setup_id, vote_type=vote_type)
        db.session.add(vote)
        
        if vote_type == 'like':
            setup.likes += 1
        elif vote_type == 'dislike':
            setup.dislikes += 1
        elif vote_type == 'cleanest':
            setup.cleanest_votes += 1
        elif vote_type == 'rgb':
            setup.rgb_votes += 1
        elif vote_type == 'budget':
            setup.budget_votes += 1
    
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

# Admin Routes
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    games = Game.query.all()
    users = User.query.all()
    return render_template('admin.html', games=games, users=users)

@app.route('/admin/add_game', methods=['GET', 'POST'])
@login_required
def add_game():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        game = Game(
            title=request.form['title'],
            description=request.form['description'],
            price=float(request.form['price']),
            genre=request.form['genre'],
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
        game.price = float(request.form['price'])
        game.image_url = request.form['image_url']
        game.voice_preview_url = request.form['voice_preview_url']
        db.session.commit()
        flash('Game updated successfully')
        return redirect(url_for('admin'))
    return render_template('edit_game.html', game=game)

@app.route('/mark_notifications_read')
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

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
