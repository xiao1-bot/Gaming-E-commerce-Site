# Script to seed the database with sample data

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Game, Review, SetupPost
from werkzeug.security import generate_password_hash
from datetime import datetime, date

def seed_database():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create sample users
        users_data = [
            {'username': 'gamer1', 'email': 'gamer1@example.com', 'password': 'password123', 'bio': 'Love RPG games!'},
            {'username': 'progamer', 'email': 'pro@example.com', 'password': 'password123', 'bio': 'Professional esports player'},
            {'username': 'casualgamer', 'email': 'casual@example.com', 'password': 'password123', 'bio': 'Gaming for fun!'},
            {'username': 'reviewer', 'email': 'reviewer@example.com', 'password': 'password123', 'bio': 'I review games for the community'},
        ]
        
        for user_data in users_data:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    bio=user_data['bio'],
                    popularity_points=50
                )
                db.session.add(user)
        
        # Create sample games
        games_data = [
            {
                'title': 'Cyber Warriors 2077',
                'description': 'A futuristic action RPG set in a cyberpunk world. Experience intense combat and deep storytelling.',
                'price': 59.99,
                'genre': 'RPG',
                'platform': 'Multi-platform',
                'release_date': date(2023, 11, 15),
                'image_url': '/placeholder.svg?height=300&width=400',
                'voice_preview_url': '/static/audio/cyber_warriors_preview.mp3'
            },
            {
                'title': 'Fantasy Quest Adventures',
                'description': 'Embark on an epic fantasy journey with magic, dragons, and ancient mysteries to uncover.',
                'price': 49.99,
                'genre': 'Adventure',
                'platform': 'PC',
                'release_date': date(2023, 10, 20),
                'image_url': '/placeholder.svg?height=300&width=400',
                'voice_preview_url': '/static/audio/fantasy_quest_preview.mp3'
            },
            {
                'title': 'Speed Racer Ultimate',
                'description': 'High-octane racing game with realistic physics and stunning graphics.',
                'price': 39.99,
                'genre': 'Racing',
                'platform': 'Multi-platform',
                'release_date': date(2023, 12, 1),
                'image_url': '/placeholder.svg?height=300&width=400',
                'voice_preview_url': '/static/audio/speed_racer_preview.mp3'
            },
            {
                'title': 'Strategic Warfare',
                'description': 'Command armies and conquer territories in this turn-based strategy masterpiece.',
                'price': 44.99,
                'genre': 'Strategy',
                'platform': 'PC',
                'release_date': date(2023, 9, 15),
                'image_url': '/placeholder.svg?height=300&width=400',
                'voice_preview_url': '/static/audio/strategic_warfare_preview.mp3'
            },
            {
                'title': 'Sports Championship 2024',
                'description': 'The ultimate sports simulation with all your favorite teams and players.',
                'price': 54.99,
                'genre': 'Sports',
                'platform': 'Multi-platform',
                'release_date': date(2024, 1, 10),
                'image_url': '/placeholder.svg?height=300&width=400',
                'voice_preview_url': '/static/audio/sports_championship_preview.mp3'
            },
            {
                'title': 'Puzzle Master Pro',
                'description': 'Challenge your mind with hundreds of unique puzzles and brain teasers.',
                'price': 19.99,
                'genre': 'Puzzle',
                'platform': 'Mobile',
                'release_date': date(2023, 8, 5),
                'image_url': '/placeholder.svg?height=300&width=400',
                'voice_preview_url': '/static/audio/puzzle_master_preview.mp3'
            }
        ]
        
        for game_data in games_data:
            if not Game.query.filter_by(title=game_data['title']).first():
                game = Game(**game_data)
                db.session.add(game)
        
        db.session.commit()
        
        # Create sample reviews
        games = Game.query.all()
        users = User.query.filter(User.username != 'admin').all()
        
        reviews_data = [
            {'rating': 5, 'content': 'Amazing game! The graphics are stunning and the gameplay is addictive.'},
            {'rating': 4, 'content': 'Really enjoyed this game. Great story and characters.'},
            {'rating': 5, 'content': 'Best game I\'ve played this year! Highly recommended.'},
            {'rating': 3, 'content': 'Good game but could use some improvements in the controls.'},
            {'rating': 4, 'content': 'Solid gameplay and great multiplayer features.'},
            {'rating': 5, 'content': 'Incredible attention to detail. Worth every penny!'},
        ]
        
        for i, review_data in enumerate(reviews_data):
            if i < len(games) and i < len(users):
                review = Review(
                    user_id=users[i % len(users)].id,
                    game_id=games[i].id,
                    rating=review_data['rating'],
                    content=review_data['content'],
                    likes=5 + i,
                    dislikes=1
                )
                db.session.add(review)
        
        # Create sample setup posts
        setup_data = [
            {
                'title': 'My RGB Gaming Paradise',
                'description': 'Custom built PC with full RGB lighting setup. Took me months to perfect!',
                'image_url': '/placeholder.svg?height=400&width=600',
                'likes': 25,
                'rgb_votes': 15,
                'cleanest_votes': 5,
                'budget_votes': 2
            },
            {
                'title': 'Minimalist Clean Setup',
                'description': 'Simple, clean, and efficient. Sometimes less is more.',
                'image_url': '/placeholder.svg?height=400&width=600',
                'likes': 30,
                'cleanest_votes': 20,
                'rgb_votes': 3,
                'budget_votes': 8
            },
            {
                'title': 'Budget Beast Build',
                'description': 'Proof that you don\'t need to break the bank for a great gaming experience!',
                'image_url': '/placeholder.svg?height=400&width=600',
                'likes': 18,
                'budget_votes': 25,
                'cleanest_votes': 8,
                'rgb_votes': 2
            }
        ]
        
        for i, setup in enumerate(setup_data):
            if i < len(users):
                setup_post = SetupPost(
                    user_id=users[i].id,
                    title=setup['title'],
                    description=setup['description'],
                    image_url=setup['image_url'],
                    likes=setup['likes'],
                    rgb_votes=setup['rgb_votes'],
                    cleanest_votes=setup['cleanest_votes'],
                    budget_votes=setup['budget_votes']
                )
                db.session.add(setup_post)
        
        # Update user popularity points based on reviews
        for user in users:
            user.popularity_points += len(user.reviews) * 10
        
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
