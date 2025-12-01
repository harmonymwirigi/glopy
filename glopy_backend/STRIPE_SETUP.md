# Stripe Payment Setup Guide

## 🚀 Quick Setup for Stripe Payments

The Stripe payment system is already fully implemented! You just need to configure your Stripe account and add the API keys.

### 1. Create Stripe Account

1. Go to [https://stripe.com](https://stripe.com)
2. Create a free account
3. Complete the account setup process

### 2. Get Your API Keys

1. **Login to Stripe Dashboard**
2. **Go to Developers > API Keys**
3. **Copy your keys:**
   - **Publishable Key** (starts with `pk_test_` or `pk_live_`)
   - **Secret Key** (starts with `sk_test_` or `sk_live_`)

### 3. Add Keys to Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 4. Test the Payment System

1. **Start your Flask app**
2. **Login as a regular user**
3. **Try to create more than the free limit (currently 100,000 for launch)**
4. **You should see the payment modal**

## 💰 How the Payment System Works

### For Users:
1. **Free Ads**: Users get 100,000 free advertisements (during launch period)
2. **Payment Required**: After free limit, payment is required for additional ads
3. **Payment Modal**: Beautiful Stripe payment interface
4. **Instant Access**: After payment, user can post more ads immediately

### For Admins:
1. **Pricing Control**: Set price per premium ad (default €5.00)
2. **Payment Monitoring**: View all payments in admin dashboard
3. **Revenue Tracking**: See total revenue and payment statistics

## 🔧 Current Configuration

- **Free Ads Limit**: 100,000 ads per user (launch period)
- **Default Price**: €5.00 per premium ad
- **Currency**: EUR (Euros)
- **Payment Method**: Stripe (cards, digital wallets, etc.)

## 🎯 Payment Flow

1. **User tries to create ad beyond free limit**
2. **System checks ad limit**
3. **Payment modal appears**
4. **User enters payment details**
5. **Stripe processes payment**
6. **Payment confirmed**
7. **User can now post more ads**

## 🛠 Admin Features

### Pricing Configuration
- Navigate to `/admin/pricing`
- Set price per premium ad
- Configure free ad limits
- Real-time updates

### Payment Monitoring
- Navigate to `/admin/payments`
- View all payments
- Filter by status
- Track revenue

## 🧪 Testing

### Test Mode (Recommended)
- Use Stripe test keys (`pk_test_` and `sk_test_`)
- Use test card numbers:
  - **Success**: 4242 4242 4242 4242
  - **Decline**: 4000 0000 0000 0002
  - **Requires Authentication**: 4000 0025 0000 3155

### Live Mode
- Use live keys (`pk_live_` and `sk_live_`)
- Real payments will be processed
- Real money will be charged

## 🔒 Security Features

- **Stripe Handles Security**: All payment data is processed by Stripe
- **No Card Storage**: Card details never touch your servers
- **PCI Compliance**: Stripe is PCI DSS compliant
- **Fraud Protection**: Stripe's built-in fraud detection

## 📊 Revenue Tracking

The admin dashboard shows:
- Total payments
- Successful payments
- Pending payments
- Total revenue
- Payment history

## 🚨 Troubleshooting

### Common Issues:

1. **"Stripe no está configurado"**
   - Check that STRIPE_SECRET_KEY is set in .env
   - Restart your Flask app

2. **Payment modal not showing**
   - Check browser console for JavaScript errors
   - Verify STRIPE_PUBLISHABLE_KEY is set

3. **Payment fails**
   - Check Stripe dashboard for error logs
   - Verify webhook endpoints (if using webhooks)

### Debug Mode:
Add this to your app.py for debugging:
```python
import stripe
stripe.api_key = STRIPE_SECRET_KEY
stripe.log = 'debug'  # Enable debug logging
```

## 🎉 Ready to Go!

Once you add your Stripe keys to the `.env` file, the payment system will be fully functional!

The system is designed to be:
- **User-friendly**: Simple payment process
- **Admin-friendly**: Easy management and monitoring
- **Secure**: Stripe handles all security
- **Scalable**: Can handle any number of payments
