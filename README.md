# ScanX Clinical Trial Intelligence Platform

A professional clinical trial analysis platform that fetches real-time data from ClinicalTrials.gov and generates AI-powered insights for pharmaceutical strategy and business development.

## 🚀 Features

- **Real-time Clinical Trial Data**: Fetches latest trial information from ClinicalTrials.gov API
- **AI-Powered Analysis**: Uses OpenAI GPT-4 to generate comprehensive market intelligence
- **Professional Dashboard**: Clean, modern interface designed for pharmaceutical professionals
- **User Management**: Secure authentication with user-specific brief management

## 🛠 Installation & Setup

### Prerequisites
- Python 3.11+
- OpenAI API key

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd scanx-brief
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   
   **Option A: Using environment.sh (Development)**
   ```bash
   # Edit environment.sh and replace "your-openai-api-key-here" with your actual OpenAI API key
   nano environment.sh
   # Then source it
   source environment.sh
   ```
   
   **Option B: Using .env file (Recommended)**
   ```bash
   # Create a .env file
   echo 'OPENAI_API_KEY=your-actual-openai-api-key' > .env
   echo 'DEBUG=True' >> .env
   echo 'SECRET_KEY=your-secret-key-here' >> .env
   ```

5. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # Optional: create admin user
   ```

6. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```

7. **Visit the Application**
   - Open http://127.0.0.1:8000 in your browser
   - Sign up for an account
   - Create your first clinical trial brief

## 🔑 API Key Setup

You'll need an OpenAI API key to use the AI analysis features:

1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set it as an environment variable (never commit API keys to git!)
3. The application will automatically detect and use the key

## 📊 Usage

### Creating a Brief
1. Log in to your account
2. Click "Create New Brief"
3. Enter a medical condition or therapeutic area
4. Wait for AI analysis to complete (1-5 minutes)
5. Review comprehensive insights and trial data

## 🛡️ Security Notes

- Never commit API keys or secrets to version control
- Use environment variables or `.env` files for sensitive data
- The `.gitignore` file is configured to exclude `.env` files
- GitHub's secret scanning will block pushes containing exposed API keys

## 🧪 Development

### Recent Updates
- Fixed OpenAI library compatibility issues
- Upgraded from OpenAI 1.42.0 to 1.82.0
- Increased AI response length for more comprehensive analysis
- Improved error handling and logging

## 📄 License

This project is licensed under the MIT License.
