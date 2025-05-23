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
                
                # Log search analysis on first page
                if page_count == 0:
                    self._log_search_analysis(query, studies[:5])  # Analyze first 5 results
                
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
    
    def _log_search_analysis(self, query: str, sample_studies: List[Dict[str, Any]]):
        """
        Analyze and log how the search query matched the returned studies.
        This helps understand what fields ClinicalTrials.gov actually searches.
        """
        if not sample_studies:
            return
            
        logger.info(f"=== SEARCH ANALYSIS for '{query}' ===")
        
        query_lower = query.lower()
        query_words = query_lower.split()
        
        for i, study in enumerate(sample_studies):
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            description = protocol.get("descriptionModule", {})
            conditions = protocol.get("conditionsModule", {})
            interventions = protocol.get("armsInterventionsModule", {})
            
            # Extract key fields
            nct_id = identification.get("nctId", "")
            title = identification.get("briefTitle", "")
            summary = description.get("briefSummary", "")
            condition_list = conditions.get("conditions", [])
            intervention_list = interventions.get("interventions", [])
            
            # Check where query terms appear
            matches = []
            
            # Check title
            if any(word in title.lower() for word in query_words):
                matches.append("TITLE")
            
            # Check conditions
            condition_text = " ".join(condition_list).lower()
            if any(word in condition_text for word in query_words):
                matches.append("CONDITIONS")
            
            # Check interventions
            intervention_names = []
            for intervention in intervention_list:
                intervention_names.append(intervention.get("name", ""))
            intervention_text = " ".join(intervention_names).lower()
            if any(word in intervention_text for word in query_words):
                matches.append("INTERVENTIONS")
            
            # Check summary
            if any(word in summary.lower() for word in query_words):
                matches.append("SUMMARY")
            
            logger.info(f"Study {i+1} ({nct_id}): Matches in [{', '.join(matches)}]")
            logger.info(f"  Title: {title[:100]}...")
            if condition_list:
                logger.info(f"  Conditions: {', '.join(condition_list[:3])}")
            if intervention_names:
                logger.info(f"  Interventions: {', '.join([name for name in intervention_names[:3] if name])}")
        
        logger.info("=== END SEARCH ANALYSIS ===")

    def search_studies_advanced(self, condition: str = None, intervention: str = None, 
                              operator: str = "AND", include_observational: bool = True) -> List[Dict[str, Any]]:
        """
        Advanced search with specific field targeting.
        
        Args:
            condition: Medical condition to search for
            intervention: Intervention/drug to search for  
            operator: Boolean operator ("AND" or "OR")
            include_observational: Whether to include observational studies
            
        Returns:
            List of study dictionaries
        """
        # Build more specific query using ClinicalTrials.gov search syntax
        query_parts = []
        
        if condition:
            # Search in condition fields specifically
            query_parts.append(f'AREA[ConditionSearch]{condition}')
        
        if intervention:
            # Search in intervention fields specifically
            query_parts.append(f'AREA[InterventionSearch]{intervention}')
        
        if len(query_parts) == 0:
            raise ValueError("At least one of condition or intervention must be provided")
        
        # Combine with boolean operator
        if len(query_parts) == 1:
            search_query = query_parts[0]
        else:
            search_query = f" {operator} ".join(query_parts)
        
        # Add study type filter if needed
        if not include_observational:
            search_query = f"({search_query}) AND AREA[StudyType]Interventional"
        
        logger.info(f"Advanced search query: {search_query}")
        
        return self.search_studies(search_query)
    
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

    def get_search_transparency_report(self, query: str, max_samples: int = 10) -> Dict[str, Any]:
        """
        Generate a transparency report showing exactly how the search works.
        Provides detailed search analysis and field breakdown for understanding search mechanics.
        
        Args:
            query: Search query to analyze
            max_samples: Number of sample studies to analyze
            
        Returns:
            Dictionary with search analysis and field breakdown
        """
        studies = self.search_studies(query)
        sample_studies = studies[:max_samples]
        
        report = {
            'query': query,
            'total_results': len(studies),
            'search_explanation': self._get_search_explanation(),
            'field_analysis': {},
            'sample_matches': []
        }
        
        if not sample_studies:
            return report
        
        # Analyze field matches across sample
        field_counts = {
            'title': 0,
            'conditions': 0, 
            'interventions': 0,
            'summary': 0,
            'other_fields': 0
        }
        
        query_words = query.lower().split()
        
        for study in sample_studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            description = protocol.get("descriptionModule", {})
            conditions = protocol.get("conditionsModule", {})
            interventions = protocol.get("armsInterventionsModule", {})
            
            # Extract fields
            nct_id = identification.get("nctId", "")
            title = identification.get("briefTitle", "")
            summary = description.get("briefSummary", "")
            condition_list = conditions.get("conditions", [])
            intervention_list = interventions.get("interventions", [])
            
            # Track matches
            matches = {
                'nct_id': nct_id,
                'title': title[:150] + "..." if len(title) > 150 else title,
                'matched_fields': []
            }
            
            # Check each field
            if any(word in title.lower() for word in query_words):
                field_counts['title'] += 1
                matches['matched_fields'].append('Study Title')
            
            condition_text = " ".join(condition_list).lower()
            if any(word in condition_text for word in query_words):
                field_counts['conditions'] += 1
                matches['matched_fields'].append('Medical Conditions')
            
            intervention_names = [intervention.get("name", "") for intervention in intervention_list]
            intervention_text = " ".join(intervention_names).lower()
            if any(word in intervention_text for word in query_words):
                field_counts['interventions'] += 1
                matches['matched_fields'].append('Interventions/Drugs')
            
            if any(word in summary.lower() for word in query_words):
                field_counts['summary'] += 1
                matches['matched_fields'].append('Study Summary')
            
            # If no obvious matches found, it's probably in other fields
            if not matches['matched_fields']:
                field_counts['other_fields'] += 1
                matches['matched_fields'].append('Other Fields (keywords, detailed descriptions, etc.)')
            
            report['sample_matches'].append(matches)
        
        # Calculate percentages
        total_samples = len(sample_studies)
        report['field_analysis'] = {
            'total_analyzed': total_samples,
            'title_matches': {'count': field_counts['title'], 'percentage': round(field_counts['title']/total_samples*100, 1)},
            'condition_matches': {'count': field_counts['conditions'], 'percentage': round(field_counts['conditions']/total_samples*100, 1)},
            'intervention_matches': {'count': field_counts['interventions'], 'percentage': round(field_counts['interventions']/total_samples*100, 1)},
            'summary_matches': {'count': field_counts['summary'], 'percentage': round(field_counts['summary']/total_samples*100, 1)},
            'other_matches': {'count': field_counts['other_fields'], 'percentage': round(field_counts['other_fields']/total_samples*100, 1)}
        }
        
        return report
    
    def _get_search_explanation(self) -> str:
        """
        Explain how ClinicalTrials.gov search works based on empirical observation.
        """
        return """
ClinicalTrials.gov's query.term parameter performs a comprehensive full-text search across multiple fields:

**Primary Search Fields:**
• Study Title (Brief Title)
• Medical Conditions (official condition names and synonyms)
• Interventions (drug names, therapies, devices)
• Study Summary/Abstract (brief summary text)

**Additional Search Areas (based on results analysis):**
• Detailed study descriptions
• Keywords and mesh terms
• Sponsor information
• Study design keywords
• Inclusion/exclusion criteria text

**Search Behavior:**
• Case-insensitive matching
• Partial word matching supported
• Searches across synonyms and related terms
• Returns studies where ANY search term matches in ANY field
• Uses ClinicalTrials.gov's internal relevance ranking

**Search Notes:**
• This is a broad "any field" search, not targeted field searching
• May return studies where search terms appear in secondary contexts
• For precision searching, consider using Advanced Search with specific field targeting
• Results ordering is based on ClinicalTrials.gov's relevance algorithm, not chronological
        """.strip()


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
        
        # Add pipeline summary header
        total_trials = len(trials)
        phases = [t.phase for t in trials if t.phase]
        phase_counts = {
            'PHASE1': sum(1 for p in phases if p == 'PHASE1'),
            'PHASE2': sum(1 for p in phases if p == 'PHASE2'), 
            'PHASE3': sum(1 for p in phases if p == 'PHASE3'),
            'PHASE4': sum(1 for p in phases if p == 'PHASE4')
        }
        
        lines.append("=== PIPELINE OVERVIEW ===")
        lines.append(f"Total Trials: {total_trials}")
        lines.append(f"Phase Distribution: Phase 1: {phase_counts['PHASE1']}, Phase 2: {phase_counts['PHASE2']}, Phase 3: {phase_counts['PHASE3']}, Phase 4: {phase_counts['PHASE4']}")
        lines.append("")
        lines.append("=== TRIAL DETAILS ===")
        
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

1. **Market Landscape Overview**: Current development trends, pipeline maturity, and key patterns
2. **Development Phases & Timeline**: Phase distribution analysis with realistic development timelines
3. **Key Players & Sponsor Activity**: Major sponsors, their focus areas, and competitive positioning  
4. **Technology & Mechanism Analysis**: Group interventions by mechanism of action or therapeutic approach
5. **Development Patterns**: Common trial designs, target populations, and regulatory approaches
6. **Pipeline Gaps & Opportunities**: Underserved areas, emerging approaches, and development opportunities

Clinical Trial Data:
{trial_text}

Provide actionable insights for clinical development, focusing on pipeline intelligence, development timelines, and therapeutic opportunities.
"""
    
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
        
        # Step 1.5: Generate search transparency report
        search_report = api_client.get_search_transparency_report(search_term, max_samples=15)
        brief.search_metadata = search_report
        brief.save()
        
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
        brief.last_updated = timezone.now()
        brief.save()
        
        logger.info(f"Brief generation completed successfully: {brief.id}")
        return brief
        
    except Exception as e:
        logger.error(f"Brief generation failed: {str(e)}")
        brief.status = Brief.STATUS_FAILED
        brief.gpt_summary = f"Brief generation failed: {str(e)}"
        brief.save()
        raise


def refresh_brief(brief: Brief) -> Brief:
    """
    Refresh an existing brief with updated clinical trial data and AI analysis.
    
    Args:
        brief: The Brief object to refresh
        
    Returns:
        Updated Brief object
        
    Raises:
        Exception: If refresh fails
    """
    if not brief.can_be_refreshed():
        raise ValueError(f"Brief cannot be refreshed (status: {brief.status})")
    
    logger.info(f"Starting brief refresh for: {brief.topic} (ID: {brief.id})")
    
    # Mark as generating
    original_status = brief.status
    brief.status = Brief.STATUS_GENERATING
    brief.save()
    
    try:
        # Clear existing trials
        brief.trials.all().delete()
        
        # Use the same search logic as original generation
        # If we have search metadata, use the original query
        search_term = brief.search_metadata.get('query', brief.topic) if brief.search_metadata else brief.topic
        
        # Step 1: Fetch fresh clinical trials
        api_client = ClinicalTrialsAPI()
        studies = api_client.search_studies(search_term)
        
        logger.info(f"Fetched {len(studies)} fresh studies from ClinicalTrials.gov")
        
        # Step 1.5: Generate fresh search transparency report
        search_report = api_client.get_search_transparency_report(search_term, max_samples=15)
        brief.search_metadata = search_report
        
        # Step 2: Create fresh trial records
        trials_created = 0
        for study in studies:
            trial = create_trial_from_study(study, brief)
            if trial:
                trials_created += 1
        
        logger.info(f"Created {trials_created} fresh trial records")
        
        # Step 3: Generate fresh AI analysis
        trials = list(brief.trials.all())
        if trials:
            analyzer = AIAnalyzer()
            brief.gpt_summary = analyzer.analyze_trials(brief.topic, trials)
        else:
            brief.gpt_summary = f"No clinical trials found for '{brief.topic}'. This may indicate a very specialized or emerging therapeutic area."
        
        # Step 4: Mark as completed with fresh timestamp
        brief.status = Brief.STATUS_COMPLETED
        brief.last_updated = timezone.now()
        brief.save()
        
        logger.info(f"Brief refresh completed successfully: {brief.id}")
        return brief
        
    except Exception as e:
        logger.error(f"Brief refresh failed: {str(e)}")
        brief.status = original_status  # Restore original status
        brief.save()
        raise

