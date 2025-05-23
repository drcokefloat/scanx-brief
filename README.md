# ScanX Clinical Trial Intelligence Platform

A professional clinical trial analysis platform that fetches real-time data from ClinicalTrials.gov and generates AI-powered insights for pharmaceutical strategy and business development.

## 🚀 Features

### Core Functionality
- **Real-time Clinical Trial Data**: Fetches latest trial information from ClinicalTrials.gov API
- **AI-Powered Analysis**: Uses OpenAI GPT-4 to generate comprehensive market intelligence
- **Professional Dashboard**: Clean, modern interface designed for pharmaceutical professionals
- **User Management**: Secure authentication with user-specific brief management
- **Advanced Filtering**: Search and filter trials by phase, status, sponsor, and more

### Key Improvements Made
- **Security Enhanced**: Environment variable management, secure API key handling
- **Performance Optimized**: Database indexing, query optimization, caching layer
- **Error Handling**: Comprehensive logging and graceful error recovery
- **Code Quality**: Type hints, documentation, clean architecture
- **User Experience**: Modern UI/UX with professional styling
- **Data Integrity**: Better validation and duplicate handling

## 🛠 Installation & Setup

### Prerequisites
- Python 3.11+
- pip
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
   ```bash
   cp .env.example .env
   # Edit .env file with your settings:
   # - OPENAI_API_KEY=your-openai-api-key
   # - DJANGO_SECRET_KEY=your-secret-key
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

## 📊 Architecture

### Models
- **Brief**: Core model representing a clinical trial analysis
  - Topic-based organization
  - Status tracking (generating, completed, failed)
  - User ownership and permissions
  - Automatic expiration handling

- **Trial**: Individual clinical trial records
  - NCT ID tracking
  - Phase and status information
  - Sponsor and timeline data
  - Linked to parent Brief

### Key Components
- **ClinicalTrialsAPI**: Robust API client with retry logic and rate limiting
- **AIAnalyzer**: OpenAI integration for intelligent analysis
- **Custom Managers**: Efficient database queries and filtering
- **Template Tags**: Professional UI components and data formatting

### Security Features
- Environment variable configuration
- CSRF protection
- User authentication and authorization
- Secure session management
- Rate limiting and input validation

## 🔧 Configuration

### Environment Variables
```bash
# Required
DJANGO_SECRET_KEY=your-django-secret-key
OPENAI_API_KEY=your-openai-api-key

# Optional
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### Django Settings
The application includes production-ready settings:
- Comprehensive logging
- Security middleware
- Static file handling
- Database optimization
- Cache configuration

## 📈 Usage

### Creating a Brief
1. Log in to your account
2. Click "Create New Brief"
3. Enter a medical condition or therapeutic area
4. Wait for AI analysis to complete (1-5 minutes)
5. Review comprehensive insights and trial data

### Dashboard Features
- **Summary Statistics**: Phase distribution, active trials, sponsor analysis
- **Trial Filtering**: Filter by phase, status, sponsor, date ranges
- **Export Options**: Data export for further analysis
- **Real-time Updates**: AJAX status checking for brief generation

### Analysis Insights
The AI generates professional insights including:
- Market landscape overview
- Competitive intelligence
- Development patterns and trends
- Strategic opportunities
- Regulatory considerations

## 🧪 Development

### Code Style
- Type hints throughout
- Comprehensive docstrings
- PEP 8 compliance
- Clean architecture principles

### Testing
```bash
python manage.py test
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Logging
Logs are written to `scanx.log` and console:
- INFO level for general operations
- DEBUG level for detailed troubleshooting
- ERROR level for exceptions and failures

## 🚀 Production Deployment

### Environment Setup
1. Set `DJANGO_DEBUG=False`
2. Configure proper `DJANGO_ALLOWED_HOSTS`
3. Set up SSL/HTTPS
4. Configure production database
5. Set up static file serving
6. Configure logging aggregation

### Security Checklist
- [ ] Environment variables secured
- [ ] Secret key rotated
- [ ] HTTPS enabled
- [ ] Database credentials secured
- [ ] API rate limiting configured
- [ ] Monitoring and alerting set up

## 📝 API Endpoints

### Authentication
- `POST /accounts/signup/` - User registration
- `POST /accounts/login/` - User login
- `POST /accounts/logout/` - User logout

### Briefs
- `GET /briefs/` - List user's briefs
- `POST /briefs/create/` - Create new brief
- `GET /briefs/<id>/` - Brief dashboard
- `GET /briefs/<id>/status/` - Check generation status
- `POST /briefs/<id>/delete/` - Delete brief

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the logs in `scanx.log`
2. Review environment variable configuration
3. Ensure OpenAI API key is valid and has credits
4. Check ClinicalTrials.gov API availability

## 📚 Documentation

### Key Files
- `brief/models.py` - Data models and business logic
- `brief/views.py` - Request handling and business logic
- `brief/utils.py` - External API integration and AI analysis
- `brief/forms.py` - Form validation and user input
- `scanx/settings.py` - Django configuration
- `scanx/urls.py` - URL routing

### Database Schema
- Optimized with indexes for performance
- Foreign key relationships for data integrity
- Automatic timestamping and audit trails
- Flexible field constraints for data quality

---

**ScanX Clinical Trial Intelligence Platform** - Empowering pharmaceutical strategy with AI-driven insights. 