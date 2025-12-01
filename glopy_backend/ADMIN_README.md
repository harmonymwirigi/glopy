# Glopy Admin System

## Overview
The Glopy Admin System provides comprehensive management capabilities for users, advertisements, categories, and pricing. It includes Stripe payment integration for premium ad posting.

## Features

### 🔐 Admin Authentication
- Secure admin-only routes with `@_require_admin` decorator
- Admin user management with toggle capabilities
- Audit logging for all admin actions

### 📊 Dashboard
- Real-time statistics (users, ads, categories, revenue)
- Recent activity overview
- Quick navigation to all admin sections

### 👥 User Management
- View all users with pagination and search
- Toggle admin privileges
- Toggle premium status
- View user statistics (free ads used, Glopy points)

### 🏠 Ad Management
- View all advertisements
- Delete inappropriate ads
- Search and filter functionality

### 🏷️ Category Management
- Manage real estate categories
- Add/edit/delete categories

### 💰 Pricing Configuration
- Set price per premium ad
- Configure free ad limits
- Real-time pricing updates

### 💳 Payment Management
- View all Stripe payments
- Track payment status
- Revenue analytics

## Setup Instructions

### 1. Environment Variables
Add these to your `.env` file:
```bash
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2. Create First Admin
Run the admin creation script:
```bash
python create_admin.py
```

### 3. Database Migration
The admin system requires these new tables:
- `pricing_plans` - Pricing configuration
- `payments` - Stripe payment records
- `premium_ads` - Premium ad purchases
- `admin_logs` - Admin action audit trail

Run migrations:
```bash
flask db upgrade
```

## Admin Routes

### Main Admin Panel
- `/admin` - Dashboard overview
- `/admin/users` - User management
- `/admin/ads` - Ad management
- `/admin/categories` - Category management
- `/admin/pricing` - Pricing configuration
- `/admin/payments` - Payment overview

### API Endpoints
- `POST /api/admin/users/<id>/toggle-admin` - Toggle admin status
- `POST /api/admin/users/<id>/toggle-premium` - Toggle premium status
- `POST /api/admin/ads/<id>/delete` - Delete ad
- `POST /api/admin/pricing/update` - Update pricing

## Payment System

### Stripe Integration
- Secure payment processing with Stripe Elements
- Payment intent creation and confirmation
- Automatic premium ad posting after successful payment

### Ad Limits
- Users get 100,000 free ads by default (during launch period)
- Additional ads require payment (configurable price)
- Premium users have unlimited ad posting

### API Endpoints
- `POST /api/create-payment-intent` - Create Stripe payment intent
- `POST /api/confirm-payment` - Confirm payment and grant access
- `GET /api/check-ad-limit` - Check user's ad posting limits

## Security Features

### Admin Protection
- All admin routes require authentication
- Admin-only decorator checks user privileges
- IP address logging for admin actions

### Payment Security
- Stripe handles all payment processing
- No sensitive payment data stored locally
- Webhook verification for payment confirmations

## Usage Examples

### Creating an Admin User
```python
from models import User
from app import app, db

with app.app_context():
    admin = User(
        name="Admin Name",
        email="admin@example.com",
        is_admin=True,
        is_verified=True
    )
    admin.set_password("secure_password")
    db.session.add(admin)
    db.session.commit()
```

### Updating Pricing
```python
from models import PricingPlan

plan = PricingPlan.query.filter_by(is_active=True).first()
plan.price_per_ad = 7.50  # €7.50 per premium ad
plan.max_free_ads = 5     # 5 free ads
db.session.commit()
```

## Monitoring

### Admin Logs
All admin actions are logged in the `admin_logs` table:
- Action performed
- Target type and ID
- Admin user who performed the action
- IP address
- Timestamp

### Payment Tracking
- All payments tracked in `payments` table
- Stripe payment intent IDs stored
- Payment status monitoring
- Revenue analytics

## Troubleshooting

### Common Issues

1. **Admin can't access admin panel**
   - Check if `is_admin=True` in database
   - Verify user is logged in
   - Check admin route decorators

2. **Stripe payments not working**
   - Verify Stripe keys in environment
   - Check webhook endpoints
   - Ensure HTTPS in production

3. **Ad limits not enforced**
   - Check `free_ads_used` counter
   - Verify pricing plan configuration
   - Check ad creation API endpoint

### Database Queries

Check admin users:
```sql
SELECT id, name, email, is_admin, is_premium FROM users WHERE is_admin = 1;
```

Check pricing configuration:
```sql
SELECT * FROM pricing_plans WHERE is_active = 1;
```

Check payment status:
```sql
SELECT status, COUNT(*) FROM payments GROUP BY status;
```

## Support

For technical support or questions about the admin system, please contact the development team or create an issue in the repository.
