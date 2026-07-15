# Guest Demo Feature - Implementation Guide

## Overview

The "Try Demo" feature allows visitors to instantly try your RAG Research Assistant without creating an account. Each click creates a fresh, isolated guest account with full functionality and automatic cleanup.

## Features

### ✅ What Guest Users Get
- **Instant access** - No email verification, no signup form
- **Full functionality** - Upload PDFs, ask questions, view conversations
- **Data isolation** - Each guest has their own workspace, can't see other users' data
- **Proper auth** - Uses the same JWT auth system as regular users
- **24-hour access** - Account and data auto-deleted after 24 hours

### 🔒 Security & Isolation
- **Unique credentials** - Each guest gets `guest_<random16chars>@demo.local`
- **Strong password** - Random 32-character token (never shown to user)
- **Database isolation** - Standard user_id filtering prevents cross-user data access
- **Qdrant isolation** - Vector points tagged with user_id, filtered on retrieval
- **No escalation** - Guests can't upgrade to permanent accounts (prevents abuse)

## Backend Changes

### 1. Database Schema (`db/models.py`)
```python
class User(Base):
    # ... existing fields ...
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

**Migration:**
```sql
ALTER TABLE users ADD COLUMN is_guest BOOLEAN DEFAULT FALSE NOT NULL;
```

### 2. New Endpoint (`api/routes_auth.py`)

**POST `/auth/guest`**
- Creates a new guest account
- Returns `AuthResponse` with token and `is_guest: true`
- No parameters needed

**Example Response:**
```json
{
  "id": "a1b2c3d4-...",
  "email": "guest_a1f2e4b8c9d0e1f2@demo.local",
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "is_guest": true
}
```

### 3. Updated Responses

All auth endpoints now return `is_guest` flag:
- `POST /auth/signup` → `is_guest: false`
- `POST /auth/login` → `is_guest: true/false` (depends on account type)
- `POST /auth/guest` → `is_guest: true`
- `GET /auth/me` → includes `is_guest` field

### 4. Cleanup Script (`cleanup_guests.py`)

Automated script to delete old guest accounts.

**Usage:**
```bash
# Dry run (see what would be deleted)
python cleanup_guests.py --dry-run

# Delete guests older than 24 hours (default)
python cleanup_guests.py

# Delete guests older than 12 hours
python cleanup_guests.py --age-hours 12

# Show guest statistics
python cleanup_guests.py --stats
```

**What it deletes:**
1. Guest user records from PostgreSQL
2. All documents uploaded by guest (via CASCADE)
3. All conversations and messages (via CASCADE)
4. All Qdrant vector points tagged with guest's user_id

**Scheduling:**
- **Railway**: Add cron job in dashboard
- **Render**: Use Render Cron Jobs (separate service)
- **HuggingFace Spaces**: Manual trigger or GitHub Actions
- **Local/Docker**: Add to crontab
  ```bash
  0 2 * * * cd /app/backend && python cleanup_guests.py
  ```

## Frontend Integration

### 1. Add "Try Demo" Button

**Login/Signup Page:**
```jsx
// In your auth page component
const handleTryDemo = async () => {
  try {
    const response = await fetch(`${API_URL}/auth/guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      throw new Error('Failed to create demo account');
    }
    
    const data = await response.json();
    
    // Store auth token (same as regular login)
    sessionStorage.setItem('authToken', data.access_token);
    sessionStorage.setItem('userEmail', data.email);
    sessionStorage.setItem('isGuest', 'true'); // NEW: mark as guest
    
    // Redirect to main app
    navigate('/');
  } catch (error) {
    console.error('Demo creation failed:', error);
    // Show error toast
  }
};

return (
  <div className="auth-page">
    {/* Existing login/signup form */}
    
    <div className="demo-section">
      <div className="divider">
        <span>or</span>
      </div>
      
      <button 
        onClick={handleTryDemo}
        className="btn-demo"
      >
        🚀 Try Demo (No signup required)
      </button>
      
      <p className="demo-note">
        Demo accounts are deleted after 24 hours
      </p>
    </div>
  </div>
);
```

### 2. Show Guest Banner

Display a banner when user is in guest mode:

```jsx
// In your app layout or header
const isGuest = sessionStorage.getItem('isGuest') === 'true';

{isGuest && (
  <div className="guest-banner">
    <span>🧪 Demo Mode</span>
    <span>Your data will be deleted in 24 hours</span>
    <button onClick={handleSignup}>
      Create Permanent Account
    </button>
  </div>
)}
```

### 3. Optional: Limit Guest Features

```jsx
// Example: Limit document uploads for guests
const MAX_GUEST_UPLOADS = 3;

const handleUpload = async (file) => {
  if (isGuest && documentCount >= MAX_GUEST_UPLOADS) {
    showToast('Demo accounts limited to 3 documents. Sign up for unlimited access!');
    return;
  }
  
  // ... normal upload logic
};
```

## Styling Recommendations

### "Try Demo" Button

Make it prominent and inviting:

```css
.btn-demo {
  width: 100%;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-demo:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
}

.demo-note {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
  text-align: center;
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
  border-bottom: 1px solid #ddd;
}

.divider span {
  padding: 0 16px;
  color: #888;
  font-size: 14px;
}
```

### Guest Banner

```css
.guest-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: linear-gradient(90deg, #ffeaa7 0%, #fdcb6e 100%);
  border-bottom: 2px solid #f39c12;
  font-size: 14px;
  font-weight: 500;
}

.guest-banner button {
  padding: 6px 16px;
  background: white;
  border: 2px solid #f39c12;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.guest-banner button:hover {
  background: #f39c12;
  color: white;
}
```

## User Experience Flow

### Typical Guest Journey

1. **Landing**: User arrives at login page
2. **Discovery**: Sees "Try Demo" button below login form
3. **One-click access**: Clicks button → instantly logged in (no form)
4. **Exploration**: 
   - Uploads a sample PDF (or you can pre-load one)
   - Asks questions
   - Sees how RAG works
5. **Conversion**: 
   - Impressed with demo
   - Sees guest banner reminder
   - Clicks "Create Permanent Account"
6. **Signup**: Creates real account to keep their data

### Conversion Optimization

**Option A: Seamless upgrade**
```jsx
const handleConvertGuest = async () => {
  // Prompt for email/password
  const { email, password } = await showSignupModal();
  
  // Create permanent account
  const newUser = await signup(email, password);
  
  // Optional: Transfer guest data to new account
  await transferGuestData(currentGuestId, newUser.id);
  
  // Switch to new account
  sessionStorage.setItem('authToken', newUser.access_token);
  sessionStorage.removeItem('isGuest');
};
```

**Option B: Fresh start**
```jsx
// Just redirect to signup, guest data stays separate
const handleSignup = () => {
  navigate('/signup');
  // Guest session remains until 24h cleanup
};
```

## Analytics & Monitoring

### Metrics to Track

```python
# Add to your analytics/logging
{
  "event": "guest_account_created",
  "guest_id": user.id,
  "timestamp": datetime.now()
}

{
  "event": "guest_converted",
  "guest_id": old_guest_id,
  "new_user_id": new_user.id,
  "time_as_guest_seconds": elapsed_time
}

{
  "event": "guest_cleaned_up",
  "guest_id": user.id,
  "age_hours": age_hours,
  "documents_deleted": doc_count
}
```

### Dashboard Queries

```sql
-- Guest conversion rate
SELECT 
  COUNT(*) FILTER (WHERE is_guest = false) as permanent_users,
  COUNT(*) FILTER (WHERE is_guest = true) as current_guests,
  -- Add tracking for converted guests
FROM users;

-- Average guest lifetime
SELECT 
  AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/3600) as avg_hours_alive
FROM users
WHERE is_guest = true;

-- Guest engagement
SELECT 
  u.email,
  COUNT(DISTINCT d.id) as documents_uploaded,
  COUNT(DISTINCT c.id) as conversations_started
FROM users u
LEFT JOIN documents d ON d.user_id = u.id
LEFT JOIN conversations c ON c.user_id = u.id
WHERE u.is_guest = true
GROUP BY u.id
ORDER BY documents_uploaded DESC;
```

## Security Considerations

### Abuse Prevention

**1. Rate Limiting**
```python
# Add to routes_auth.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/guest")
@limiter.limit("5/hour")  # Max 5 guest accounts per IP per hour
async def create_guest_account(request: Request, db: AsyncSession = Depends(get_db)):
    # ... existing code
```

**2. Resource Limits**
```python
# In routes_upload.py, check if user is guest
if user.is_guest:
    # Count existing documents
    doc_count = await db.scalar(
        select(func.count(Document.id)).where(Document.user_id == user.id)
    )
    if doc_count >= 3:  # Limit guests to 3 documents
        raise HTTPException(
            status_code=403, 
            detail="Demo accounts limited to 3 documents. Sign up for unlimited access."
        )
```

**3. Cleanup Monitoring**
```python
# Add alerting if cleanup fails
try:
    deleted_count = await cleanup_old_guests()
    if deleted_count > 100:
        send_alert(f"Unusually high guest cleanup: {deleted_count} accounts")
except Exception as e:
    send_alert(f"Guest cleanup failed: {e}")
```

### Privacy Compliance

**GDPR/Privacy:**
- ✅ No PII collected (email is fake: `guest_xxx@demo.local`)
- ✅ Automatic deletion after 24 hours
- ✅ Clear disclosure: "Demo accounts are deleted after 24 hours"
- ✅ No tracking beyond standard analytics

**Terms of Service:**
Add to your ToS:
> Demo accounts are temporary and will be automatically deleted after 24 hours. Any data uploaded during a demo session will be permanently removed at that time.

## Testing

### Manual Testing

```bash
# 1. Create guest account
curl -X POST https://your-api.com/auth/guest

# Expected: Returns access_token and is_guest=true

# 2. Use guest token to upload document
curl -X POST https://your-api.com/upload \
  -H "Authorization: Bearer <guest_token>" \
  -F "file=@test.pdf"

# Expected: Document uploads successfully

# 3. Query as guest
curl -X POST https://your-api.com/query \
  -H "Authorization: Bearer <guest_token>" \
  -d '{"query": "What is this document about?"}'

# Expected: Gets answer from uploaded document

# 4. Try to access another user's document
# Expected: Empty results (proper isolation)

# 5. Run cleanup (dry run)
python cleanup_guests.py --dry-run --age-hours 0

# Expected: Shows the guest account would be deleted
```

### Automated Tests

```python
# tests/test_guest_accounts.py
async def test_guest_creation():
    response = await client.post("/auth/guest")
    assert response.status_code == 201
    data = response.json()
    assert data["is_guest"] == True
    assert data["email"].startswith("guest_")
    assert "access_token" in data

async def test_guest_isolation():
    # Create two guests
    guest1 = await create_guest()
    guest2 = await create_guest()
    
    # Guest1 uploads document
    await upload_pdf(guest1.token, "test.pdf")
    
    # Guest2 tries to query guest1's document
    response = await query(guest2.token, "test.pdf", "What is this about?")
    
    # Should get empty results (no access to guest1's data)
    assert len(response["sources"]) == 0

async def test_guest_cleanup():
    # Create guest with old timestamp
    guest = await create_guest()
    await set_created_at(guest.id, datetime.now() - timedelta(hours=25))
    
    # Run cleanup
    deleted = await cleanup_old_guests(age_hours=24)
    
    # Verify guest is deleted
    assert deleted == 1
    assert await get_user(guest.id) is None
```

## Deployment Checklist

- [ ] Add `is_guest` column to `users` table
  ```sql
  ALTER TABLE users ADD COLUMN is_guest BOOLEAN DEFAULT FALSE NOT NULL;
  ```

- [ ] Deploy backend with new `/auth/guest` endpoint

- [ ] Add cleanup script to scheduled tasks:
  - [ ] Railway: Add cron job (daily at 2am)
  - [ ] Render: Create Cron Job service
  - [ ] HF Spaces: Manual or GitHub Actions

- [ ] Update frontend:
  - [ ] Add "Try Demo" button to auth page
  - [ ] Add guest banner to app header
  - [ ] Store `isGuest` flag in session storage
  - [ ] Optional: Add guest-to-permanent conversion flow

- [ ] Test end-to-end:
  - [ ] Guest creation works
  - [ ] Guest can upload and query
  - [ ] Data isolation verified
  - [ ] Cleanup script runs successfully

- [ ] Monitor:
  - [ ] Track guest creation rate
  - [ ] Track conversion rate (guest → permanent)
  - [ ] Alert on cleanup failures
  - [ ] Monitor storage (ensure old guests are being cleaned up)

## Future Enhancements

### Pre-loaded Demo Documents
Instead of having guests upload, pre-load interesting documents:

```python
@router.post("/guest")
async def create_guest_account(db: AsyncSession = Depends(get_db)):
    # ... create guest user ...
    
    # Pre-load sample document
    sample_pdf = "samples/research_paper.pdf"
    await preload_document_for_user(user.id, sample_pdf)
    
    return AuthResponse(...)
```

### Guided Tour
Show a tutorial overlay for first-time guests:
```jsx
{isGuest && isFirstVisit && (
  <TourOverlay steps={[
    "This is a demo with a pre-loaded research paper",
    "Try asking: 'What is this paper about?'",
    "Click here to upload your own PDF",
    "Questions are answered using RAG technology"
  ]} />
)}
```

### Data Transfer on Conversion
Allow guests to keep their demo data when signing up:
```python
async def convert_guest_to_permanent(
    guest_id: uuid.UUID,
    email: str,
    password: str,
    db: AsyncSession
):
    # Update guest record to permanent
    guest = await get_user_by_id(db, str(guest_id))
    guest.email = email
    guest.hashed_pw = hash_password(password)
    guest.is_guest = False
    await db.commit()
    
    # Qdrant vectors already tagged with user_id, so they Just Work™
```

## Summary

The guest demo feature provides:
- ✅ **Instant access** for visitors to try your RAG system
- ✅ **Full isolation** showcases your auth/security implementation
- ✅ **Automatic cleanup** prevents database bloat
- ✅ **Conversion funnel** from demo → signup
- ✅ **No abuse risk** with rate limiting and resource caps

It's a win-win: visitors get to try before committing, and you get more signups from people who've already seen value in the product.
