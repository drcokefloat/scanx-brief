# brief/utils.py

"""
Utilities for clinical trial data processing and AI analysis.
"""

import datetime
import logging
import time
from typing import List, Optional, Dict, Any

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from openai import OpenAI

from .models import Brief, Trial

logger = logging.getLogger(__name__)


class ClinicalTrialsAPIError(Exception):
    """Custom exception for ClinicalTrials.gov API errors."""
    pass


class OpenAIError(Exception):
    """Custom exception for OpenAI API errors."""
    pass


class ClinicalTrialsAPI:
    """
    Client for interacting with ClinicalTrials.gov API.
    """
    
    def __init__(self):
        self.base_url = settings.CLINICALTRIALS_API_URL
        self.timeout = settings.CLINICALTRIALS_API_TIMEOUT
        self.max_results = settings.CLINICALTRIALS_MAX_RESULTS
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ScanX Clinical Trial Intelligence Platform',
            'Accept': 'application/json',
        })
    
    def search_studies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for clinical studies based on a query term.
        
        Args:
            query: Search term for clinical trials
            
        Returns:
            List of study dictionaries
            
        Raises:
            ClinicalTrialsAPIError: If API request fails
        """
        all_studies = []
        page_token = None
        page_count = 0
        max_pages = 5  # Limit to prevent infinite loops
        
        logger.info(f"Searching ClinicalTrials.gov for: {query}")
        
        while page_count < max_pages:
            try:
                # Build URL with parameters
                url = f"{self.base_url}?query.term={query}&pageSize=100"
                if page_token:
                    url += f"&pageToken={page_token}"
                
                logger.debug(f"Fetching page {page_count + 1}: {url}")
                
                # Make request with retry logic
                response = self._make_request(url)
                data = response.json()
                
                studies = data.get("studies", [])
                if not studies:
                    logger.info("No more studies found, stopping pagination")
                    break
                
                all_studies.extend(studies)
                logger.info(f"Fetched {len(studies)} studies (total: {len(all_studies)})")
                
                # Check for next page
                page_token = data.get("nextPageToken")
                if not page_token:
                    logger.info("No more pages available")
                    break
                
                page_count += 1
                
                # Respect rate limits
                time.sleep(0.5)
                
                # Stop if we have enough results
                if len(all_studies) >= self.max_results:
                    logger.info(f"Reached maximum results limit: {self.max_results}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching studies page {page_count + 1}: {str(e)}")
                if page_count == 0:  # If first page fails, raise exception
                    raise ClinicalTrialsAPIError(f"Failed to fetch clinical trials: {str(e)}")
                else:  # If subsequent pages fail, just stop
                    logger.warning("Stopping pagination due to error")
                    break
        
        logger.info(f"Total studies fetched: {len(all_studies)}")
        return all_studies
    
    def _make_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response object
            
        Raises:
            ClinicalTrialsAPIError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise ClinicalTrialsAPIError("Request timed out")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise ClinicalTrialsAPIError(f"Request failed: {str(e)}")
                time.sleep(2 ** attempt)


class AIAnalyzer:
    """
    Client for AI analysis using OpenAI GPT.
    """
    
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key or api_key == 'sk-test-key-replace-with-real-key':
            self.demo_mode = True
            self.client = None
            logger.warning("OpenAI API key not configured - running in demo mode")
        else:
            self.demo_mode = False
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4-turbo"
    
    def analyze_trials(self, topic: str, trials: List[Trial]) -> str:
        """
        Generate AI analysis of clinical trials.
        
        Args:
            topic: The medical topic being analyzed
            trials: List of trial objects to analyze
            
        Returns:
            AI-generated analysis text
            
        Raises:
            OpenAIError: If AI analysis fails
        """
        if not trials:
            return "No clinical trials found for analysis."
        
        # Demo mode fallback
        if self.demo_mode:
            return self._generate_demo_analysis(topic, trials)
        
        # Filter and format trials for analysis
        relevant_trials = self._filter_relevant_trials(trials)
        trial_text = self._format_trials_for_analysis(relevant_trials)
        
        prompt = self._build_analysis_prompt(topic, trial_text)
        
        logger.info(f"Generating AI analysis for {len(relevant_trials)} trials")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.7,
            )
            
            analysis = response.choices[0].message.content.strip()
            logger.info("AI analysis generated successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise OpenAIError(f"Failed to generate AI analysis: {str(e)}")
    
    def _filter_relevant_trials(self, trials: List[Trial]) -> List[Trial]:
        """Filter trials to most relevant ones for analysis."""
        # Prioritize Phase 3 and 4 trials, then by recency
        phase_priority = {'PHASE4': 4, 'PHASE3': 3, 'PHASE2': 2, 'PHASE1': 1}
        
        def trial_score(trial):
            phase_score = phase_priority.get(trial.phase, 0)
            # Prefer recent trials
            days_old = (timezone.now().date() - (trial.start_date or datetime.date.min)).days
            recency_score = max(0, 365 - days_old) / 365  # Scale 0-1
            return phase_score + recency_score
        
        sorted_trials = sorted(trials, key=trial_score, reverse=True)
        return sorted_trials[:50]  # Limit to top 50 for analysis
    
    def _format_trials_for_analysis(self, trials: List[Trial]) -> str:
        """Format trials for AI analysis."""
        lines = []
        for trial in trials:
            line = (
                f"{trial.nct_id}: {trial.title} | "
                f"Sponsor: {trial.sponsor_display} | "
                f"Phase: {trial.phase_display} | "
                f"Status: {trial.status or 'N/A'} | "
                f"Start: {trial.start_date or 'N/A'}"
            )
            lines.append(line)
        return "\n".join(lines)
    
    def _build_analysis_prompt(self, topic: str, trial_text: str) -> str:
        """Build the prompt for AI analysis."""
        return f"""You are an expert in clinical development and market access.

Based on these clinical trials for '{topic}', provide a comprehensive analysis including:

1. **Market Landscape Overview**: Key trends and patterns in the clinical trial space
2. **Sponsor Activity**: Major players and their strategic focus areas
3. **Development Patterns**: Common phases, trial designs, and therapeutic approaches
4. **Strategic Signals**: Evidence of indication expansion, new formulations, target populations
5. **Competitive Intelligence**: Gaps and opportunities for differentiation
6. **Market Access Considerations**: Regulatory pathways and approval strategies

Clinical Trial Data:
{trial_text}

Please provide actionable insights for pharmaceutical strategy and business development."""
    
    def _generate_demo_analysis(self, topic: str, trials: List[Trial]) -> str:
        """Generate a demo analysis when OpenAI API is not available."""
        trial_count = len(trials)
        phases = set(trial.phase for trial in trials if trial.phase)
        sponsors = set(trial.sponsor for trial in trials if trial.sponsor)
        active_trials = [t for t in trials if 'recruiting' in (t.status or '').lower()]
        
        return f"""# Clinical Trial Analysis for {topic}

**Note: This is a demo analysis generated without AI. Configure OPENAI_API_KEY for full AI-powered insights.**

## Market Landscape Overview
The {topic} therapeutic area shows significant clinical activity with **{trial_count} trials** identified in our analysis. This indicates a highly active research environment with substantial pharmaceutical interest.

## Trial Distribution
- **Total Trials**: {trial_count}
- **Active/Recruiting Trials**: {len(active_trials)}
- **Unique Sponsors**: {len(sponsors)}
- **Phase Distribution**: {', '.join(sorted(phases)) if phases else 'Mixed phases'}

## Key Sponsors
{'The top sponsors include: ' + ', '.join(list(sponsors)[:5]) + '.' if sponsors else 'Sponsor information is being processed.'}

## Development Trends
Based on the trial data, {topic} research appears to focus on {'recruiting new patients' if active_trials else 'various study phases'} with a diverse portfolio of approaches from multiple pharmaceutical companies.

## Strategic Opportunities
The high level of activity in this space suggests strong market interest and potential for innovative therapeutic approaches. {'Multiple active trials indicate ongoing recruitment opportunities.' if active_trials else 'The completion of trials may indicate upcoming data readouts.'}

## Next Steps
For detailed competitive intelligence and market access strategies, please configure your OpenAI API key to enable full AI-powered analysis.

---
*Demo analysis generated on {timezone.now().strftime('%B %d, %Y')}*"""


def parse_partial_date(date_string: str) -> Optional[datetime.date]:
    """
    Parse partial dates from ClinicalTrials.gov API.
    
    Args:
        date_string: Date string in various formats (YYYY, YYYY-MM, YYYY-MM-DD)
        
    Returns:
        Parsed date object or None if parsing fails
    """
    if not date_string or not date_string.strip():
        return None
    
    try:
        date_string = date_string.strip()
        
        if len(date_string) == 4:  # YYYY
            return datetime.date(int(date_string), 1, 1)
        elif len(date_string) == 7:  # YYYY-MM
            return datetime.date.fromisoformat(f"{date_string}-01")
        else:  # YYYY-MM-DD
            return datetime.date.fromisoformat(date_string)
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse date '{date_string}': {str(e)}")
        return None


def create_trial_from_study(study_data: Dict[str, Any], brief: Brief) -> Optional[Trial]:
    """
    Create a Trial object from ClinicalTrials.gov study data.
    
    Args:
        study_data: Study data from API
        brief: Brief object to associate with
        
    Returns:
        Created Trial object or None if creation fails
    """
    try:
        protocol = study_data.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        design_module = protocol.get("designModule", {})
        
        nct_id = identification.get("nctId", "")
        if not nct_id:
            logger.warning("Skipping study with no NCT ID")
            return None
        
        # Extract trial details
        title = identification.get("briefTitle", "")
        sponsor = sponsor_module.get("leadSponsor", {}).get("name", "")
        phases = design_module.get("phases", [])
        phase = phases[0] if phases else ""
        status = status_module.get("overallStatus", "")
        start_date_raw = status_module.get("startDateStruct", {}).get("date", "")
        start_date = parse_partial_date(start_date_raw)
        
        # Create trial (allow duplicates since we removed unique constraint)
        trial = Trial.objects.create(
            brief=brief,
            nct_id=nct_id,
            title=title,
            sponsor=sponsor,
            phase=phase,
            status=status,
            start_date=start_date,
            url=f"https://clinicaltrials.gov/study/{nct_id}"
        )
        
        return trial
        
    except Exception as e:
        logger.error(f"Error creating trial from study data: {str(e)}")
        return None


def generate_brief(search_term: str, owner=None, display_topic: str = None) -> Brief:
    """
    Generate a complete clinical trial brief with AI analysis.
    
    Args:
        search_term: The actual search term to use for ClinicalTrials.gov API
        owner: User who owns the brief
        display_topic: The topic to display (defaults to search_term if not provided)
        
    Returns:
        Generated Brief object
        
    Raises:
        Exception: If brief generation fails
    """
    # Use display_topic if provided, otherwise use search_term
    topic_for_display = display_topic or search_term
    
    logger.info(f"Starting brief generation for display topic: {topic_for_display} (search: {search_term})")
    
    # Create brief with generating status
    brief = Brief.objects.create(
        topic=topic_for_display,
        owner=owner,
        status=Brief.STATUS_GENERATING
    )
    
    try:
        # Step 1: Fetch clinical trials using the search term
        api_client = ClinicalTrialsAPI()
        studies = api_client.search_studies(search_term)
        
        logger.info(f"Fetched {len(studies)} studies from ClinicalTrials.gov")
        
        # Step 2: Create trial records
        trials_created = 0
        for study in studies:
            trial = create_trial_from_study(study, brief)
            if trial:
                trials_created += 1
        
        logger.info(f"Created {trials_created} trial records")
        
        # Step 3: Generate AI analysis (use display topic for analysis context)
        trials = list(brief.trials.all())
        if trials:
            analyzer = AIAnalyzer()
            brief.gpt_summary = analyzer.analyze_trials(topic_for_display, trials)
        else:
            brief.gpt_summary = f"No clinical trials found for '{topic_for_display}'. This may indicate a very specialized or emerging therapeutic area."
        
        # Step 4: Mark as completed
        brief.status = Brief.STATUS_COMPLETED
        brief.save()
        
        logger.info(f"Brief generation completed successfully: {brief.id}")
        return brief
        
    except Exception as e:
        logger.error(f"Brief generation failed: {str(e)}")
        brief.status = Brief.STATUS_FAILED
        brief.gpt_summary = f"Brief generation failed: {str(e)}"
        brief.save()
        raise

