# Overdue Game Notification & User Ban System

This document explains the new overdue game tracking, notification system, and user ban functionality added to the Gaming Store application.

## Features Overview

### 1. Overdue Game Tracking
- Automatically detects games that are past their return date
- Marks games as overdue in the database
- Sends immediate notifications to borrowers
- Alerts admins about overdue users

### 2. User Notification System
- **Borrowers**: Receive warnings about overdue games
- **Admins**: Get notified about users with overdue games
- **Real-time**: Notifications appear immediately when games become overdue
- **Persistent**: Notifications are stored and can be marked as read

### 3. Admin User Management
- View all users and their status
- See users with overdue games prominently
- Ban users for repeated violations
- Unban users when appropriate
- View admin-specific notifications

### 4. User Ban System
- Admins can ban users for overdue games or other violations
- Banned users cannot access the platform
- Ban reasons are recorded and tracked
- Users can be unbanned by admins

## Database Changes

### New Fields Added

#### User Table
- `is_banned` (BOOLEAN): Whether the user is banned
- `banned_at` (DATETIME): When the user was banned
- `banned_by` (INTEGER): Admin ID who banned the user
- `ban_reason` (TEXT): Reason for the ban

#### GameLending Table
- `is_overdue` (BOOLEAN): Whether the game is overdue
- `overdue_notification_sent` (BOOLEAN): Whether overdue notification was sent

#### Notification Table
- `notification_type` (VARCHAR): Type of notification ('overdue', 'admin', 'general')

#### New AdminNotification Table
- Stores admin-specific notifications
- Links to related users when applicable
- Tracks read/unread status

## How It Works

### 1. Automatic Overdue Detection
```python
# Called before each request for logged-in users
@app.before_request
def check_overdue_before_request():
    if current_user.is_authenticated and not current_user.is_admin:
        check_overdue_games()
```

### 2. Overdue Check Process
1. Finds games past their return date
2. Marks them as overdue
3. Sends notifications to borrowers
4. Alerts admins about overdue users
5. Updates database flags

### 3. Notification Flow
```
Game becomes overdue → Borrower notification + Admin notification
↓
Borrower sees warning on lend_games page
↓
Admin sees overdue user in admin panel
↓
Admin can ban user if necessary
```

## Setup Instructions

### 1. Run Database Migration
```bash
cd scripts
python migrate_overdue_system.py
```

### 2. Restart Application
The new functionality will be available immediately after restart.

### 3. Test the System
1. Create a game lending with a short duration (1 day)
2. Wait for it to become overdue
3. Check notifications for both borrower and admin
4. Test ban/unban functionality

## Admin Features

### User Management (`/admin/users`)
- **Overview**: See all users and their status
- **Overdue Users**: Highlighted section showing users with overdue games
- **Ban Actions**: Ban/unban users with reason tracking
- **Overdue Check**: Manual button to check for overdue games

### Admin Notifications (`/admin/notifications`)
- **System Alerts**: Overdue user notifications
- **Read Status**: Mark notifications as read
- **User Context**: See which user each notification relates to

### Quick Actions
- **Check Overdue**: Manually trigger overdue detection
- **Manage Users**: Direct access to user management
- **View Notifications**: Access admin notification center

## User Experience

### For Regular Users
- **Notifications Page**: View all notifications (`/notifications`)
- **Overdue Warnings**: Prominent warnings on lend_games page
- **Clear Notifications**: Mark individual or all notifications as read

### For Borrowers with Overdue Games
- **Immediate Warning**: Flash message when overdue
- **Persistent Alert**: Warning banner on lend_games page
- **Notification**: Stored notification about overdue status

## API Endpoints

### Admin Routes
- `GET /admin/users` - User management interface
- `POST /admin/ban_user/<user_id>` - Ban a user
- `POST /admin/unban_user/<user_id>` - Unban a user
- `GET /admin/notifications` - Admin notifications
- `POST /admin/mark_notification_read/<id>` - Mark notification as read
- `GET /admin/check_overdue` - Manually check for overdue games

### User Routes
- `GET /notifications` - User notifications
- `POST /mark_notification_read/<id>` - Mark notification as read
- `POST /clear_all_notifications` - Clear all notifications

### Test Routes (Development Only)
- `GET /test/create_overdue/<lending_id>` - Create overdue game for testing

## Configuration

### Automatic Checks
- Overdue checks happen automatically on each page load
- No additional configuration needed
- Can be disabled by commenting out the `@app.before_request` decorator

### Notification Types
- `overdue`: Game overdue warnings
- `admin`: Administrative actions
- `general`: General system notifications

## Security Features

### User Ban Protection
- Admins cannot ban other admins
- Ban reasons are required and logged
- Banned users cannot access any protected routes
- `is_active()` method automatically checks ban status

### Access Control
- Admin routes require admin privileges
- User notifications are user-specific
- Admin notifications are admin-only

## Monitoring and Maintenance

### Regular Tasks
1. **Daily**: Check admin notifications for overdue users
2. **Weekly**: Review banned users and consider unbans
3. **Monthly**: Analyze overdue patterns and adjust policies

### Database Maintenance
- Notifications accumulate over time
- Consider archiving old notifications
- Monitor database size growth

## Troubleshooting

### Common Issues

#### Migration Errors
- Ensure database file is writable
- Check SQLite version compatibility
- Verify table structure before migration

#### Notifications Not Working
- Check if `check_overdue_games()` is being called
- Verify notification tables exist
- Check user authentication status

#### Ban System Issues
- Ensure `is_banned` field exists in User table
- Verify `is_active()` method is working
- Check admin privileges

### Debug Mode
Enable debug logging to see overdue check operations:
```python
app.logger.setLevel(logging.DEBUG)
```

## Future Enhancements

### Potential Improvements
1. **Email Notifications**: Send overdue warnings via email
2. **SMS Alerts**: Text message reminders for overdue games
3. **Automatic Bans**: Auto-ban after multiple overdue incidents
4. **Grace Periods**: Configurable grace periods before overdue
5. **Fine System**: Monetary penalties for overdue games
6. **Escalation**: Progressive warning system

### Integration Ideas
1. **Calendar Integration**: Sync return dates with user calendars
2. **Mobile App**: Push notifications for mobile users
3. **Analytics Dashboard**: Overdue statistics and trends
4. **Automated Reports**: Daily/weekly overdue summaries

## Support

For issues or questions about the overdue system:
1. Check this documentation
2. Review the migration script output
3. Check application logs for errors
4. Verify database schema matches expectations

---

**Note**: This system is designed to be robust and user-friendly while maintaining security and accountability. Regular monitoring and maintenance will ensure optimal performance.
