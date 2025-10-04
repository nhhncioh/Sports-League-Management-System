"""
AI-powered financial services using OpenAI
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import current_app
import openai


def _get_openai_client():
    """Get configured OpenAI client"""
    # Try to get from Flask app config first, then environment
    api_key = None
    try:
        api_key = current_app.config.get('OPENAI_API_KEY')
    except RuntimeError:
        pass

    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        raise ValueError("OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file.")

    return openai.OpenAI(api_key=api_key)


def categorize_expense(description: str, vendor: Optional[str] = None, amount: Optional[float] = None) -> Dict:
    """
    Use AI to suggest an expense category based on description and vendor

    Args:
        description: Expense description
        vendor: Vendor/payee name
        amount: Expense amount (optional, for context)

    Returns:
        Dict with 'category', 'confidence', 'reasoning'
    """
    try:
        client = _get_openai_client()

        # Build prompt with context
        prompt = f"Categorize this sports league expense:\n"
        prompt += f"Description: {description}\n"
        if vendor:
            prompt += f"Vendor: {vendor}\n"
        if amount:
            prompt += f"Amount: ${amount:.2f}\n"

        prompt += """
Valid categories:
- equipment: Sports equipment, balls, goals, nets, etc.
- facilities: Field rental, gym rental, venue costs
- officials: Referee fees, umpire payments
- insurance: League insurance, liability coverage
- marketing: Advertising, promotional materials, social media
- admin: Office supplies, software, administrative costs
- travel: Transportation, team travel expenses
- uniforms: Jerseys, team apparel, uniforms
- utilities: Water, electricity, internet for facilities
- other: Anything else

Respond with JSON only:
{
    "category": "one of the categories above",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial categorization assistant for sports league management. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            result = json.loads(result_text)
            return {
                'category': result.get('category', 'other'),
                'confidence': float(result.get('confidence', 0.5)),
                'reasoning': result.get('reasoning', 'AI categorization')
            }
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                'category': 'other',
                'confidence': 0.0,
                'reasoning': 'Failed to parse AI response'
            }

    except Exception as e:
        return {
            'category': 'other',
            'confidence': 0.0,
            'reasoning': f'AI categorization failed: {str(e)}'
        }


def detect_expense_anomalies(expenses: List[Dict], new_expense: Dict) -> Dict:
    """
    Detect if a new expense is anomalous compared to historical expenses

    Args:
        expenses: List of historical expense records
        new_expense: The new expense to check

    Returns:
        Dict with 'is_anomaly', 'anomaly_score', 'reasons'
    """
    try:
        if not expenses:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'reasons': ['Insufficient historical data']
            }

        client = _get_openai_client()

        # Prepare expense summary for AI
        category = new_expense.get('category', 'unknown')
        amount = new_expense.get('amount_cents', 0) / 100.0
        description = new_expense.get('description', '')

        # Get similar category expenses
        similar_expenses = [e for e in expenses if e.get('category') == category]

        if not similar_expenses:
            # No historical data for this category
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'reasons': [f'First expense in category: {category}']
            }

        # Calculate basic stats
        amounts = [e.get('amount_cents', 0) / 100.0 for e in similar_expenses]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        max_amount = max(amounts) if amounts else 0

        prompt = f"""Analyze this new expense for anomalies:

New Expense:
- Category: {category}
- Amount: ${amount:.2f}
- Description: {description}

Historical Data for {category}:
- Average amount: ${avg_amount:.2f}
- Maximum amount: ${max_amount:.2f}
- Number of transactions: {len(similar_expenses)}
- Recent transactions: {json.dumps([{'amount': a, 'desc': e.get('description', '')[:50]} for a, e in zip(amounts[-5:], similar_expenses[-5:])], indent=2)}

Detect if this expense is anomalous. Consider:
1. Is the amount significantly higher than average?
2. Is the description unusual for this category?
3. Are there any red flags?

Respond with JSON only:
{{
    "is_anomaly": true/false,
    "anomaly_score": 0.0-1.0,
    "reasons": ["reason1", "reason2"]
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial fraud detection assistant. Analyze expenses for anomalies and respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return {
            'is_anomaly': result.get('is_anomaly', False),
            'anomaly_score': float(result.get('anomaly_score', 0.0)),
            'reasons': result.get('reasons', [])
        }

    except Exception as e:
        return {
            'is_anomaly': False,
            'anomaly_score': 0.0,
            'reasons': [f'Anomaly detection failed: {str(e)}']
        }


def suggest_vendor_info(description: str) -> Dict:
    """
    Suggest vendor name and other details based on description

    Args:
        description: Expense description

    Returns:
        Dict with suggested vendor, category, and tags
    """
    try:
        client = _get_openai_client()

        prompt = f"""Based on this expense description, suggest the vendor and category:

Description: {description}

Respond with JSON only:
{{
    "vendor": "suggested vendor name or null if unclear",
    "category_suggestions": ["category1", "category2"],
    "is_recurring": true/false (guess if this might be a recurring expense),
    "tags": ["tag1", "tag2"] (useful tags for this expense)
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts vendor and categorization info from expense descriptions. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return {
            'vendor': result.get('vendor'),
            'category_suggestions': result.get('category_suggestions', []),
            'is_recurring': result.get('is_recurring', False),
            'tags': result.get('tags', [])
        }

    except Exception as e:
        return {
            'vendor': None,
            'category_suggestions': [],
            'is_recurring': False,
            'tags': [],
            'error': str(e)
        }


def generate_budget_insights(revenue_breakdown: Dict, expense_breakdown: Dict,
                            total_revenue: float, total_expenses: float) -> Dict:
    """
    Generate AI-powered insights and recommendations for budget management

    Args:
        revenue_breakdown: Dict of revenue by type
        expense_breakdown: Dict of expenses by category
        total_revenue: Total revenue amount
        total_expenses: Total expense amount

    Returns:
        Dict with insights, recommendations, and warnings
    """
    # Handle case with no data
    if total_revenue == 0 and total_expenses == 0:
        return {
            'overall_health': 'unknown',
            'key_insights': ['No financial data recorded yet. Start by adding expenses and revenue to get AI-powered insights.'],
            'recommendations': [
                'Begin tracking expenses to understand spending patterns',
                'Record all revenue sources for comprehensive financial overview',
                'Categorize transactions consistently for better insights'
            ],
            'warnings': [],
            'expense_optimization': []
        }

    try:
        client = _get_openai_client()

        net_profit = total_revenue - total_expenses

        prompt = f"""Analyze this sports league's financial data and provide insights:

REVENUE (Total: ${total_revenue:.2f}):
{json.dumps(revenue_breakdown, indent=2)}

EXPENSES (Total: ${total_expenses:.2f}):
{json.dumps(expense_breakdown, indent=2)}

Net Profit/Loss: ${net_profit:.2f}

Provide financial insights and recommendations. Consider:
1. Are expenses balanced across categories?
2. Is the league financially healthy?
3. Any concerning spending patterns?
4. Recommendations for improvement

Respond with JSON only:
{{
    "overall_health": "excellent/good/fair/poor",
    "key_insights": ["insight1", "insight2", "insight3"],
    "recommendations": ["recommendation1", "recommendation2"],
    "warnings": ["warning1"] or [],
    "expense_optimization": ["suggestion1", "suggestion2"]
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor specializing in sports league management. Provide actionable insights. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return {
            'overall_health': result.get('overall_health', 'unknown'),
            'key_insights': result.get('key_insights', []),
            'recommendations': result.get('recommendations', []),
            'warnings': result.get('warnings', []),
            'expense_optimization': result.get('expense_optimization', [])
        }

    except Exception as e:
        return {
            'overall_health': 'unknown',
            'key_insights': [],
            'recommendations': [],
            'warnings': [f'AI insights failed: {str(e)}'],
            'expense_optimization': []
        }


def generate_news_article(topic: str, recent_matches: List[Dict] = None, context: str = None) -> Dict:
    """
    Generate a news article using AI

    Args:
        topic: The topic/title for the article
        recent_matches: Optional list of recent match data
        context: Optional additional context

    Returns:
        Dict with 'title', 'content', 'summary'
    """
    try:
        client = _get_openai_client()

        # Build prompt based on available data
        prompt = f"Write a professional sports league news article.\n\n"

        if topic:
            prompt += f"Topic: {topic}\n\n"

        if recent_matches and len(recent_matches) > 0:
            prompt += "Recent Match Results:\n"
            for match in recent_matches[:10]:  # Limit to 10 most recent
                home_team = match.get('home_team', 'Team A')
                away_team = match.get('away_team', 'Team B')
                home_score = match.get('home_score', 0)
                away_score = match.get('away_score', 0)
                match_date = match.get('match_date', '')

                prompt += f"- {home_team} {home_score} - {away_score} {away_team} ({match_date})\n"
            prompt += "\n"

        if context:
            prompt += f"Additional Context: {context}\n\n"

        prompt += """
Write a compelling news article (300-500 words) that:
1. Has an engaging headline
2. Includes a brief summary (1-2 sentences)
3. Covers the main story with relevant details
4. Uses an enthusiastic but professional tone
5. Includes quotes or highlights if applicable

Respond with JSON only:
{
    "title": "Compelling headline",
    "summary": "Brief 1-2 sentence summary",
    "content": "Full article content in markdown format"
}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional sports journalist writing engaging articles for a sports league. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return {
            'title': result.get('title', topic),
            'summary': result.get('summary', ''),
            'content': result.get('content', ''),
            'success': True
        }

    except Exception as e:
        return {
            'title': topic or 'News Article',
            'summary': '',
            'content': '',
            'success': False,
            'error': str(e)
        }


def generate_match_recap(match_data: Dict) -> Dict:
    """
    Generate a match recap article

    Args:
        match_data: Match information including teams, scores, stats

    Returns:
        Dict with article content
    """
    try:
        client = _get_openai_client()

        home_team = match_data.get('home_team', 'Home Team')
        away_team = match_data.get('away_team', 'Away Team')
        home_score = match_data.get('home_score', 0)
        away_score = match_data.get('away_score', 0)
        match_date = match_data.get('match_date', '')
        scorers = match_data.get('scorers', [])

        prompt = f"""Write an exciting match recap article for:

{home_team} {home_score} - {away_score} {away_team}
Date: {match_date}

"""
        if scorers:
            prompt += "Scorers:\n"
            for scorer in scorers:
                prompt += f"- {scorer.get('player_name', 'Unknown')} ({scorer.get('team_name', 'Unknown')})\n"
            prompt += "\n"

        prompt += """
Create a 200-300 word match recap that:
1. Describes the match outcome and key moments
2. Highlights standout performances
3. Captures the excitement and atmosphere
4. Uses vivid sports journalism language

Respond with JSON only:
{
    "title": "Match recap headline",
    "summary": "One sentence match summary",
    "content": "Full recap content"
}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an enthusiastic sports journalist writing match recaps. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=800
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return {
            'title': result.get('title', f'{home_team} vs {away_team} - Match Recap'),
            'summary': result.get('summary', ''),
            'content': result.get('content', ''),
            'success': True
        }

    except Exception as e:
        return {
            'title': f'{match_data.get("home_team", "Home")} vs {match_data.get("away_team", "Away")} - Match Recap',
            'summary': '',
            'content': '',
            'success': False,
            'error': str(e)
        }


def generate_waiver(waiver_type: str, organization_name: str, sport: str = None,
                   custom_requirements: str = None) -> Dict:
    """
    Generate a liability waiver using AI

    Args:
        waiver_type: Type of waiver ('general', 'youth', 'adult', 'tournament')
        organization_name: Name of the sports organization
        sport: Specific sport (optional)
        custom_requirements: Any custom clauses or requirements

    Returns:
        Dict with 'title', 'content', 'version'
    """
    try:
        client = _get_openai_client()

        waiver_templates = {
            'general': 'a comprehensive general liability waiver',
            'youth': 'a youth participant waiver with parental consent sections',
            'adult': 'an adult participant liability waiver',
            'tournament': 'a tournament/event-specific waiver'
        }

        template_desc = waiver_templates.get(waiver_type, 'a general liability waiver')

        prompt = f"""Create {template_desc} for a sports league organization.

Organization: {organization_name}
Sport: {sport or 'General Sports'}
Waiver Type: {waiver_type.title()}

"""
        if custom_requirements:
            prompt += f"Special Requirements:\n{custom_requirements}\n\n"

        prompt += """
The waiver MUST include:
1. Clear assumption of risk language
2. Release of liability and indemnification
3. Medical emergency authorization
4. Photography/media release
5. Code of conduct acknowledgment
6. Severability clause
7. Signature and date fields (with placeholders)

For youth waivers, include:
- Parent/guardian consent section
- Emergency contact information
- Medical conditions disclosure

Format the waiver professionally with:
- Clear section headings
- Numbered clauses
- Legal language appropriate for liability protection
- HTML formatting for web display (<p>, <strong>, <ul>, etc.)

Generate a version number based on current year (e.g., 2025.1)

Respond with JSON only:
{
    "title": "Appropriate waiver title",
    "content": "Complete waiver content in HTML format",
    "version": "2025.1",
    "summary": "Brief description of what this waiver covers"
}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a legal document specialist creating liability waivers for sports organizations. Always respond with valid JSON. The waivers should be legally sound and comprehensive."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return {
            'title': result.get('title', f'{waiver_type.title()} Waiver'),
            'content': result.get('content', ''),
            'version': result.get('version', '2025.1'),
            'summary': result.get('summary', ''),
            'success': True
        }

    except Exception as e:
        return {
            'title': f'{waiver_type.title()} Waiver',
            'content': '',
            'version': '1.0',
            'summary': '',
            'success': False,
            'error': str(e)
        }


def search_expenses_natural_language(query: str, expenses: List[Dict]) -> List[Dict]:
    """
    Search expenses using natural language query

    Args:
        query: Natural language search query
        expenses: List of all expenses

    Returns:
        Filtered list of relevant expenses
    """
    try:
        client = _get_openai_client()

        # Prepare expense summaries for AI
        expense_summaries = []
        for idx, exp in enumerate(expenses[:100]):  # Limit to 100 for token limits
            expense_summaries.append({
                'index': idx,
                'date': exp.get('date', ''),
                'category': exp.get('category', ''),
                'vendor': exp.get('vendor', ''),
                'description': exp.get('description', ''),
                'amount': exp.get('amount_display', '')
            })

        prompt = f"""Given this natural language query: "{query}"

Find matching expenses from this list:
{json.dumps(expense_summaries, indent=2)}

Return the indices of matching expenses. Consider the query semantically - match on meaning, not just keywords.

Respond with JSON only:
{{
    "matching_indices": [0, 3, 5, ...],
    "explanation": "why these match"
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a search assistant. Find expenses that match the user's natural language query. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        matching_indices = result.get('matching_indices', [])
        return [expenses[i] for i in matching_indices if i < len(expenses)]

    except Exception as e:
        # Fallback to simple keyword search
        query_lower = query.lower()
        return [
            exp for exp in expenses
            if query_lower in exp.get('description', '').lower()
            or query_lower in exp.get('vendor', '').lower()
            or query_lower in exp.get('category', '').lower()
        ]
