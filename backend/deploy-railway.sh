#!/bin/bash
# Railway deployment script for Multi-Agent RAG Research Assistant

echo "🚂 Deploying to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Login to Railway
echo "🔐 Logging in to Railway..."
railway login

# Initialize project if not already done
if [ ! -f "railway.toml" ]; then
    echo "📦 Initializing Railway project..."
    railway init
fi

# Set environment variables from .env file
echo "⚙️  Setting environment variables..."
echo "📝 Reading from .env file..."

# Load environment variables from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    
    railway variables set DATABASE_URL="$DATABASE_URL"
    railway variables set QDRANT_URL="$QDRANT_URL"
    railway variables set QDRANT_API_KEY="$QDRANT_API_KEY"
    railway variables set GROQ_API_KEY="$GROQ_API_KEY"
    railway variables set JWT_SECRET_KEY="$JWT_SECRET_KEY"
    railway variables set GEMINI_API_KEY="$GEMINI_API_KEY"
    
    echo "✅ Environment variables set from .env file"
else
    echo "❌ .env file not found!"
    echo "Please create a .env file with your secrets or set them manually:"
    echo ""
    echo "  railway variables set DATABASE_URL='your-database-url'"
    echo "  railway variables set QDRANT_URL='your-qdrant-url'"
    echo "  railway variables set QDRANT_API_KEY='your-qdrant-key'"
    echo "  railway variables set GROQ_API_KEY='your-groq-key'"
    echo "  railway variables set JWT_SECRET_KEY='your-jwt-secret'"
    echo "  railway variables set GEMINI_API_KEY='your-gemini-key'"
    echo ""
    exit 1
fi

# Deploy
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo "📊 View your deployment: railway open"
echo "📝 View logs: railway logs"
