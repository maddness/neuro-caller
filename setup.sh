#!/bin/bash

echo "🚀 Setting up Neuro-Caller project..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your credentials!"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Twilio and OpenAI credentials"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the server: python src/app.py"
echo "4. Make a test call: python src/scripts/make_call.py +79991234567"
echo ""
