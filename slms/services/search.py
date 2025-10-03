"""Universal search service with typeahead support."""
from __future__ import annotations

from typing import Dict, List, Any
from sqlalchemy import or_, and_, func, select
from sqlalchemy.orm import joinedload

from slms.extensions import db
from slms.models.models import (
    Team, Player, Coach, Referee, Venue, Game, League, Season,
    Sponsor, Article, Registration
)


class SearchService:
    """Service for universal search across all domain objects."""

    # Define searchable models and their configurations
    SEARCHABLE_MODELS = {
        'teams': {
            'model': Team,
            'fields': ['name', 'coach_name'],
            'icon': 'ph-shield',
            'url_template': '/teams/{id}',
            'display': lambda obj: obj.name,
            'subtitle': lambda obj: f"{obj.wins}-{obj.losses}" if obj.wins is not None else None,
        },
        'players': {
            'model': Player,
            'fields': ['first_name', 'last_name', 'email'],
            'icon': 'ph-user',
            'url_template': '/players/{id}',
            'display': lambda obj: f"{obj.first_name} {obj.last_name}",
            'subtitle': lambda obj: f"#{obj.jersey_number}" if obj.jersey_number else None,
        },
        'coaches': {
            'model': Coach,
            'fields': ['first_name', 'last_name', 'email'],
            'icon': 'ph-chalkboard-teacher',
            'url_template': '/coaches/{id}',
            'display': lambda obj: f"{obj.first_name} {obj.last_name}",
            'subtitle': lambda obj: obj.certification_level if obj.certification_level else None,
        },
        'referees': {
            'model': Referee,
            'fields': ['first_name', 'last_name', 'email', 'license_number'],
            'icon': 'ph-whistle',
            'url_template': '/referees/{id}',
            'display': lambda obj: f"{obj.first_name} {obj.last_name}",
            'subtitle': lambda obj: obj.license_number if obj.license_number else None,
        },
        'venues': {
            'model': Venue,
            'fields': ['name', 'address', 'city'],
            'icon': 'ph-map-pin',
            'url_template': '/venues/{id}',
            'display': lambda obj: obj.name,
            'subtitle': lambda obj: f"{obj.city}" if obj.city else None,
        },
        'leagues': {
            'model': League,
            'fields': ['name', 'description'],
            'icon': 'ph-trophy',
            'url_template': '/leagues/{id}',
            'display': lambda obj: obj.name,
            'subtitle': lambda obj: obj.sport.value if hasattr(obj.sport, 'value') else obj.sport,
        },
        'seasons': {
            'model': Season,
            'fields': ['name'],
            'icon': 'ph-calendar',
            'url_template': '/seasons/{id}',
            'display': lambda obj: obj.name,
            'subtitle': lambda obj: f"{obj.start_date.strftime('%Y')}" if obj.start_date else None,
        },
        'articles': {
            'model': Article,
            'fields': ['title', 'excerpt'],
            'icon': 'ph-article',
            'url_template': '/articles/{slug}',
            'display': lambda obj: obj.title,
            'subtitle': lambda obj: obj.excerpt[:50] + '...' if obj.excerpt and len(obj.excerpt) > 50 else obj.excerpt,
        },
    }

    @staticmethod
    def search(
        query: str,
        org_id: str,
        types: List[str] | None = None,
        limit: int = 10,
        filters: Dict[str, Any] | None = None
    ) -> Dict[str, List[Dict]]:
        """
        Perform universal search across multiple entity types.

        Args:
            query: Search query string
            org_id: Organization ID
            types: List of entity types to search (None = all)
            limit: Maximum results per type
            filters: Additional filters per type

        Returns:
            Dictionary with results grouped by type
        """
        if not query or len(query) < 2:
            return {}

        results = {}
        search_types = types or list(SearchService.SEARCHABLE_MODELS.keys())

        for search_type in search_types:
            if search_type not in SearchService.SEARCHABLE_MODELS:
                continue

            config = SearchService.SEARCHABLE_MODELS[search_type]
            model = config['model']

            # Build search conditions
            search_conditions = []
            for field in config['fields']:
                if hasattr(model, field):
                    column = getattr(model, field)
                    search_conditions.append(column.ilike(f'%{query}%'))

            # Base query with org filter
            stmt = select(model).where(
                and_(
                    model.org_id == org_id,
                    or_(*search_conditions)
                )
            )

            # Apply additional filters
            if filters and search_type in filters:
                for key, value in filters[search_type].items():
                    if hasattr(model, key):
                        stmt = stmt.where(getattr(model, key) == value)

            # Execute query
            stmt = stmt.limit(limit)
            items = db.session.execute(stmt).scalars().all()

            # Format results
            if items:
                results[search_type] = [
                    SearchService._format_result(item, config)
                    for item in items
                ]

        return results

    @staticmethod
    def typeahead(
        query: str,
        org_id: str,
        types: List[str] | None = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Quick typeahead search returning flat list of results.

        Args:
            query: Search query string
            org_id: Organization ID
            types: List of entity types to search
            limit: Total maximum results

        Returns:
            Flat list of results sorted by relevance
        """
        results = SearchService.search(query, org_id, types, limit=limit)

        # Flatten results into single list
        flat_results = []
        for search_type, items in results.items():
            flat_results.extend(items)

        # Sort by relevance (exact match first, then starts with)
        query_lower = query.lower()

        def relevance_score(item):
            display = item['display'].lower()
            if display == query_lower:
                return 0  # Exact match
            elif display.startswith(query_lower):
                return 1  # Starts with
            else:
                return 2  # Contains

        flat_results.sort(key=relevance_score)

        return flat_results[:limit]

    @staticmethod
    def advanced_search(
        org_id: str,
        entity_type: str,
        filters: Dict[str, Any],
        sort_by: str | None = None,
        sort_order: str = 'asc',
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Advanced search with filtering, sorting, and pagination.

        Args:
            org_id: Organization ID
            entity_type: Type of entity to search
            filters: Filter conditions
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
            page: Page number (1-indexed)
            per_page: Results per page

        Returns:
            Dictionary with results and pagination info
        """
        if entity_type not in SearchService.SEARCHABLE_MODELS:
            raise ValueError(f"Unknown entity type: {entity_type}")

        config = SearchService.SEARCHABLE_MODELS[entity_type]
        model = config['model']

        # Build query
        stmt = select(model).where(model.org_id == org_id)

        # Apply filters
        for key, value in filters.items():
            if not hasattr(model, key):
                continue

            column = getattr(model, key)

            if isinstance(value, dict):
                # Handle operators like gt, lt, contains, etc.
                if 'eq' in value:
                    stmt = stmt.where(column == value['eq'])
                elif 'ne' in value:
                    stmt = stmt.where(column != value['ne'])
                elif 'gt' in value:
                    stmt = stmt.where(column > value['gt'])
                elif 'gte' in value:
                    stmt = stmt.where(column >= value['gte'])
                elif 'lt' in value:
                    stmt = stmt.where(column < value['lt'])
                elif 'lte' in value:
                    stmt = stmt.where(column <= value['lte'])
                elif 'contains' in value:
                    stmt = stmt.where(column.ilike(f'%{value["contains"]}%'))
                elif 'in' in value:
                    stmt = stmt.where(column.in_(value['in']))
            else:
                # Direct equality
                stmt = stmt.where(column == value)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.session.execute(count_stmt).scalar()

        # Apply sorting
        if sort_by and hasattr(model, sort_by):
            sort_column = getattr(model, sort_by)
            if sort_order.lower() == 'desc':
                stmt = stmt.order_by(sort_column.desc())
            else:
                stmt = stmt.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        # Execute query
        items = db.session.execute(stmt).scalars().all()

        return {
            'results': [SearchService._format_result(item, config) for item in items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def _format_result(obj: Any, config: Dict) -> Dict:
        """Format search result object."""
        display = config['display'](obj)
        subtitle = config['subtitle'](obj) if config['subtitle'] else None

        # Build URL
        url_template = config['url_template']
        if '{slug}' in url_template and hasattr(obj, 'slug'):
            url = url_template.format(slug=obj.slug)
        else:
            url = url_template.format(id=obj.id)

        return {
            'id': obj.id,
            'type': obj.__tablename__,
            'display': display,
            'subtitle': subtitle,
            'icon': config['icon'],
            'url': url,
        }

    @staticmethod
    def get_filters_for_type(entity_type: str) -> Dict[str, Any]:
        """
        Get available filters for an entity type.

        Returns:
            Dictionary describing available filters
        """
        if entity_type not in SearchService.SEARCHABLE_MODELS:
            return {}

        model = SearchService.SEARCHABLE_MODELS[entity_type]['model']

        # Introspect model to get filterable fields
        filters = {}

        # Get all columns
        for column in model.__table__.columns:
            column_name = column.name
            column_type = str(column.type)

            filter_config = {
                'type': column_type,
                'nullable': column.nullable,
            }

            # Add operators based on type
            if 'INTEGER' in column_type or 'NUMERIC' in column_type:
                filter_config['operators'] = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in']
            elif 'VARCHAR' in column_type or 'TEXT' in column_type:
                filter_config['operators'] = ['eq', 'ne', 'contains', 'in']
            elif 'BOOLEAN' in column_type:
                filter_config['operators'] = ['eq']
            elif 'DATE' in column_type:
                filter_config['operators'] = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte']

            filters[column_name] = filter_config

        return filters


def search_players_by_team(team_id: str, org_id: str) -> List[Player]:
    """Helper: Search players by team."""
    return db.session.query(Player).filter_by(
        org_id=org_id,
        team_id=team_id
    ).order_by(Player.jersey_number, Player.last_name).all()


def search_games_by_team(team_id: str, org_id: str, limit: int | None = None) -> List[Game]:
    """Helper: Search games by team."""
    stmt = select(Game).where(
        and_(
            Game.org_id == org_id,
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id)
        )
    ).order_by(Game.start_time.desc())

    if limit:
        stmt = stmt.limit(limit)

    return db.session.execute(stmt).scalars().all()


def search_games_by_venue(venue_id: str, org_id: str, limit: int | None = None) -> List[Game]:
    """Helper: Search games by venue."""
    stmt = select(Game).where(
        and_(
            Game.org_id == org_id,
            Game.venue_id == venue_id
        )
    ).order_by(Game.start_time.desc())

    if limit:
        stmt = stmt.limit(limit)

    return db.session.execute(stmt).scalars().all()


def get_related_content(entity_type: str, entity_id: str, org_id: str) -> Dict[str, List]:
    """
    Get related content for an entity.

    Args:
        entity_type: Type of entity (team, player, venue, etc.)
        entity_id: Entity ID
        org_id: Organization ID

    Returns:
        Dictionary with related content
    """
    related = {}

    if entity_type == 'team':
        related['players'] = search_players_by_team(entity_id, org_id)
        related['games'] = search_games_by_team(entity_id, org_id, limit=10)

    elif entity_type == 'player':
        player = db.session.get(Player, entity_id)
        if player and player.team_id:
            related['team'] = db.session.get(Team, player.team_id)

    elif entity_type == 'venue':
        related['games'] = search_games_by_venue(entity_id, org_id, limit=10)

    return related
