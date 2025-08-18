#!/usr/bin/env python3
"""
Migration script to add overdue game tracking and user ban functionality
Run this script to update existing databases with new fields
"""

import sqlite3
import os
import sys

def migrate_database():
    """Migrate the database to add new overdue and ban fields"""
    
    # Get the database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'gaming_store.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting database migration...")
        
        # Check if new fields already exist
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        # Add new fields to User table if they don't exist
        if 'is_banned' not in user_columns:
            print("Adding ban fields to User table...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_banned BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE user ADD COLUMN banned_at DATETIME")
            cursor.execute("ALTER TABLE user ADD COLUMN banned_by INTEGER")
            cursor.execute("ALTER TABLE user ADD COLUMN ban_reason TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN ban_duration_days INTEGER")
            print("✓ Added ban fields to User table")
        
        # Check GameLending table
        cursor.execute("PRAGMA table_info(game_lending)")
        lending_columns = [column[1] for column in cursor.fetchall()]
        
        # Add new fields to GameLending table if they don't exist
        if 'is_overdue' not in lending_columns:
            print("Adding overdue fields to GameLending table...")
            cursor.execute("ALTER TABLE game_lending ADD COLUMN is_overdue BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE game_lending ADD COLUMN overdue_notification_sent BOOLEAN DEFAULT 0")
            print("✓ Added overdue fields to GameLending table")
        
        # Check Notification table
        cursor.execute("PRAGMA table_info(notification)")
        notification_columns = [column[1] for column in cursor.fetchall()]
        
        # Add notification_type field if it doesn't exist
        if 'notification_type' not in notification_columns:
            print("Adding notification_type field to Notification table...")
            cursor.execute("ALTER TABLE notification ADD COLUMN notification_type VARCHAR(50) DEFAULT 'general'")
            print("✓ Added notification_type field to Notification table")
        
        # Create AdminNotification table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                notification_type VARCHAR(50) DEFAULT 'general',
                related_user_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_user_id) REFERENCES user (id)
            )
        """)
        print("✓ Created AdminNotification table")
        
        # Commit changes
        conn.commit()
        print("✓ Database migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM game_lending WHERE borrower_id IS NOT NULL AND is_returned = 0")
        active_lendings = cursor.fetchone()[0]
        
        print(f"\nDatabase Summary:")
        print(f"- Total users: {user_count}")
        print(f"- Active game lendings: {active_lendings}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Migration error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Overdue Game System Migration Script")
    print("=" * 40)
    
    if migrate_database():
        print("\nMigration completed successfully!")
        print("You can now run the application with overdue tracking and user ban functionality.")
    else:
        print("\nMigration failed!")
        sys.exit(1)
