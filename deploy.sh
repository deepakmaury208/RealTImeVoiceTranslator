#!/bin/bash
# Quick deployment script for Railway.app

echo "=========================================="
echo " Real-Time Voice Translator"
echo " Railway.app Deployment Helper"
echo "=========================================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    exit 1
fi

# Initialize git repository
echo "📦 Initializing Git repository..."
git init
echo "✅ Git repository initialized"
echo ""

# Add all files
echo "📝 Adding files..."
git add .
echo "✅ Files added"
echo ""

# Create first commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit - Real-Time Voice Translator"
echo "✅ Initial commit created"
echo ""

# Instructions
echo "=========================================="
echo " Next Steps"
echo "=========================================="
echo ""
echo "1. Create a GitHub repository at github.com"
echo "   - Name: RealTimeVoiceTranslator"
echo ""
echo "2. Run these commands:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/RealTimeVoiceTranslator.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Go to railway.app and deploy!"
echo ""
echo "=========================================="
