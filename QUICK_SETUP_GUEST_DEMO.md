# Quick Setup: Guest Demo Feature

## Backend Setup (5 minutes)

### 1. Run Database Migration

Connect to your Neon database and run:

```sql
-- Add is_guest column
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE NOT NULL;

-- Create index for faster cleanup queries
CREATE INDEX IF NOT EXISTS idx_users_is_guest_created 
ON users(is_guest, created_at) 
WHERE is_guest = TRUE;
```

Or use the migration file:
```bash
cd backend/migrations
psql $DATABASE_URL -f 001_add_is_guest_column.sql
```

### 2. Test Guest Endpoint

```bash
# Test guest account creation
curl -X POST https://your-api.com/auth/guest

# Expected response:
{
  "id": "a1b2c3d4-...",
  "email": "guest_a1f2e4b8c9d0e1f2@demo.local",
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "is_guest": true
}
```

### 3. Setup Cleanup Cron Job

**Option A: Railway**
```bash
# In Railway dashboard:
# Settings > Cron Jobs > Add Job
# Command: python cleanup_guests.py
# Schedule: 0 2 * * * (daily at 2am)
```

**Option B: Manual Testing**
```bash
# Test cleanup (dry run)
cd backend
python cleanup_guests.py --dry-run

# Show guest stats
python cleanup_guests.py --stats

# Actually cleanup guests older than 24 hours
python cleanup_guests.py
```

---

## Frontend Setup (10 minutes)

### 1. Add "Try Demo" Button to Login Page

```jsx
// src/pages/AuthPage.jsx (or your auth component)
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

const AuthPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const API_URL = import.meta.env.VITE_API_URL;

  const handleTryDemo = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/guest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error('Failed to create demo account');
      }
      
      const data = await response.json();
      
      // Store auth info (same as regular login)
      sessionStorage.setItem('authToken', data.access_token);
      sessionStorage.setItem('userEmail', data.email);
      sessionStorage.setItem('userId', data.id);
      sessionStorage.setItem('isGuest', 'true'); // NEW
      
      // Redirect to main app
      navigate('/');
    } catch (error) {
      console.error('Demo creation failed:', error);
      alert('Failed to create demo account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      {/* Your existing login/signup form */}
      <form className="auth-form">
        {/* ... email, password inputs, login button ... */}
      </form>

      {/* NEW: Demo section */}
      <div className="demo-section">
        <div className="divider">
          <span>or</span>
        </div>
        
        <button 
          onClick={handleTryDemo}
          disabled={loading}
          className="btn-demo"
          type="button"
        >
          {loading ? '⏳ Creating demo...' : '🚀 Try Demo (No signup required)'}
        </button>
        
        <p className="demo-note">
          ✨ Full access • 🔒 Your own workspace • ⏰ 24 hours
        </p>
      </div>
    </div>
  );
};
```

### 2. Add Guest Banner

```jsx
// src/components/GuestBanner.jsx
import { useNavigate } from 'react-router-dom';

const GuestBanner = () => {
  const navigate = useNavigate();
  const isGuest = sessionStorage.getItem('isGuest') === 'true';

  if (!isGuest) return null;

  const handleSignup = () => {
    // Clear guest session
    sessionStorage.clear();
    // Go to signup page
    navigate('/signup');
  };

  return (
    <div className="guest-banner">
      <div className="banner-content">
        <span className="banner-icon">🧪</span>
        <span className="banner-text">
          <strong>Demo Mode</strong> — Your data will be deleted in 24 hours
        </span>
      </div>
      <button onClick={handleSignup} className="banner-btn">
        Create Permanent Account
      </button>
    </div>
  );
};

export default GuestBanner;
```

```jsx
// In your main App.jsx or Layout component
import GuestBanner from './components/GuestBanner';

function App() {
  return (
    <div className="app">
      <GuestBanner />
      {/* rest of your app */}
    </div>
  );
}
```

### 3. Add Styles

```css
/* Add to your main CSS file */

/* Demo button section */
.demo-section {
  margin-top: 32px;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 24px 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #e2e8f0;
}

.divider span {
  padding: 0 16px;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
}

.btn-demo {
  width: 100%;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25);
}

.btn-demo:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(102, 126, 234, 0.35);
}

.btn-demo:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.demo-note {
  margin-top: 12px;
  font-size: 13px;
  color: #64748b;
  text-align: center;
  line-height: 1.5;
}

/* Guest banner */
.guest-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: linear-gradient(90deg, #fef3c7 0%, #fde68a 100%);
  border-bottom: 2px solid #f59e0b;
  font-size: 14px;
  gap: 16px;
  flex-wrap: wrap;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-icon {
  font-size: 20px;
}

.banner-text strong {
  font-weight: 700;
  color: #92400e;
}

.banner-btn {
  padding: 8px 20px;
  background: white;
  border: 2px solid #f59e0b;
  border-radius: 6px;
  font-weight: 600;
  color: #92400e;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.banner-btn:hover {
  background: #f59e0b;
  color: white;
  transform: translateY(-1px);
}

/* Responsive */
@media (max-width: 640px) {
  .guest-banner {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
  
  .banner-content {
    justify-content: center;
  }
  
  .banner-btn {
    width: 100%;
  }
}
```

---

## Testing Checklist

### Backend Tests
- [ ] ✅ Migration ran successfully
- [ ] ✅ `POST /auth/guest` returns `is_guest: true`
- [ ] ✅ Guest can upload documents
- [ ] ✅ Guest can query documents
- [ ] ✅ Guest can't see other users' documents
- [ ] ✅ Cleanup script runs without errors
- [ ] ✅ `GET /auth/me` includes `is_guest` field

### Frontend Tests
- [ ] ✅ "Try Demo" button visible on auth page
- [ ] ✅ Clicking demo button creates guest account
- [ ] ✅ User redirected to main app after demo creation
- [ ] ✅ Guest banner shows at top of app
- [ ] ✅ "Create Permanent Account" button works
- [ ] ✅ Auth token stored correctly
- [ ] ✅ Demo works on mobile (responsive)

### End-to-End Test
1. Visit login page
2. Click "Try Demo"
3. Upload a sample PDF
4. Ask "What is this document about?"
5. See answer with sources
6. Click "Create Permanent Account" in banner
7. Sign up with real email
8. Verify you're now logged in as permanent user

---

## Deployment Steps

### 1. Deploy Backend
```bash
# Already pushed to main and HF Spaces ✅
git push origin main
git subtree push --prefix backend hf main
```

### 2. Run Migration
```bash
# Connect to Neon database
psql $DATABASE_URL

# Run migration
\i backend/migrations/001_add_is_guest_column.sql

# Verify
SELECT COUNT(*) FROM users WHERE is_guest = true;
-- Should return 0 (no guests yet)
```

### 3. Setup Cron Job

**Railway:**
1. Go to your Railway project dashboard
2. Select your backend service
3. Settings → Add Cron Job
4. Command: `python cleanup_guests.py`
5. Schedule: `0 2 * * *` (daily at 2am)

**Render:**
1. Create new Cron Job service
2. Connect to same repo
3. Build Command: (none)
4. Start Command: `python backend/cleanup_guests.py`
5. Schedule: Daily at 2am

**Manual (first time):**
```bash
# SSH into your server and test
cd /path/to/backend
python cleanup_guests.py --stats
```

### 4. Deploy Frontend

Update your frontend with the new components and styles, then deploy:

```bash
cd frontend
npm run build
# Deploy to Vercel (or your hosting)
vercel --prod
```

---

## Quick Fixes

### "Column already exists" Error
```sql
-- Use IF NOT EXISTS in migration
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE NOT NULL;
```

### Frontend Not Connecting
Check `VITE_API_URL` environment variable:
```bash
# .env.local
VITE_API_URL=https://your-backend.hf.space
```

### Cleanup Script Errors
```bash
# Make sure .env is in backend folder
cd backend
ls -la .env

# Test with dry run first
python cleanup_guests.py --dry-run --age-hours 0
```

### Guest Banner Not Showing
```jsx
// Debug in console
console.log('isGuest:', sessionStorage.getItem('isGuest'));
// Should log 'true' for guest accounts
```

---

## Monitoring

### Check Guest Activity
```bash
# See current guests
python cleanup_guests.py --stats

# Output example:
# Guest Account Statistics:
#   Total guests: 5
#   Age distribution:
#     < 1h: 2
#     1-6h: 1
#     6-12h: 1
#     12-24h: 1
#     > 24h: 0
#   Total documents: 8
#   Average documents per guest: 1.6
```

### Database Query
```sql
-- See all guests
SELECT 
  email, 
  created_at,
  EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as age_hours
FROM users 
WHERE is_guest = true 
ORDER BY created_at DESC;

-- Count guests by age
SELECT 
  CASE 
    WHEN EXTRACT(EPOCH FROM (NOW() - created_at))/3600 < 1 THEN '< 1h'
    WHEN EXTRACT(EPOCH FROM (NOW() - created_at))/3600 < 6 THEN '1-6h'
    WHEN EXTRACT(EPOCH FROM (NOW() - created_at))/3600 < 12 THEN '6-12h'
    WHEN EXTRACT(EPOCH FROM (NOW() - created_at))/3600 < 24 THEN '12-24h'
    ELSE '> 24h'
  END as age_bucket,
  COUNT(*) as count
FROM users 
WHERE is_guest = true
GROUP BY age_bucket
ORDER BY age_bucket;
```

---

## Success! 🎉

Your guest demo feature is live. Users can now:
- ✅ Try your RAG assistant without signing up
- ✅ Get their own isolated workspace
- ✅ See full functionality (upload, query, chat history)
- ✅ Convert to permanent account anytime

Next: Monitor conversion rates and adjust the demo experience based on user feedback!
