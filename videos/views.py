from rest_framework import generics
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
from .models import Video
from .serializers import VideoSerializer
from .pagination import CursorVideoPagination
from django.shortcuts import render
from django.db.models import Q
from django.utils.dateparse import parse_datetime

class VideoListView(generics.ListAPIView):
    """
    Return a queryset of Video objects optionally filtered by a search query.

    Search Features:
    - Uses PostgreSQL full-text search (SearchVector and SearchQuery) to find videos
      matching all query lexemes in title and description, with weighted ranking (title more important).
    - Incorporates trigram similarity to enable partial and fuzzy matching of the query terms
      anywhere in the title or description. This improves matches for queries with
      words in any order or partial words.
    - Also includes case-insensitive substring matching (icontains) as a fallback for
      partial matches.
    - Combines full-text search and partial match filters using OR to maximize recall.
    - Orders results primarily by full-text relevance rank, then trigram similarity, then
      by published date descending.

    This approach allows:
    - Matching queries like "tea how" to videos titled "How to make tea?" regardless of word order.
    - Partial word matches such as "mak" matching "make".
    - Improved relevance sorting based on exact matches and similarity scores.

    Returns:
        QuerySet: Filtered and ordered Video queryset based on the search query parameter.
    """
    serializer_class = VideoSerializer
    pagination_class = CursorVideoPagination 

    def get_queryset(self):
        queryset = Video.objects.all()
        query_params = self.request.query_params
        search = query_params.get('search', '').strip()
        category = query_params.get('category')
        published_after = query_params.get('published_after')
        published_before = query_params.get('published_before')
        sort_field = query_params.get('sort', 'published_at')
        sort_order = query_params.get('order', 'desc')

        # Full-text search + fuzzy matching
        if search:
            search_query = SearchQuery(search, search_type='plain')
            search_vector = SearchVector('title', weight='A') + SearchVector('description', weight='B')

            queryset = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query),
                similarity=TrigramSimilarity('title', search) + TrigramSimilarity('description', search),
            ).filter(
                Q(search=search_query) | Q(title__icontains=search) | Q(description__icontains=search)
            )
        else:
            queryset = queryset.annotate(
                rank=SearchRank(SearchVector('title', weight='A') + SearchVector('description', weight='B'), SearchQuery('')),
                similarity=TrigramSimilarity('title', '') + TrigramSimilarity('description', '')
            )

        # Apply filters
        if category:
            queryset = queryset.filter(category__iexact=category)
        
        if published_after:
            dt = parse_datetime(published_after)
            if dt:
                queryset = queryset.filter(published_at__gte=dt)

        if published_before:
            dt = parse_datetime(published_before)
            if dt:
                queryset = queryset.filter(published_at__lte=dt)

        # Sorting
        allowed_sort_fields = {
            'title': 'title',
            'published_at': 'published_at',
            'rank': 'rank',
            'similarity': 'similarity',
        }
        sort_field = allowed_sort_fields.get(sort_field, 'published_at')
        if sort_order == 'desc':
            sort_field = f'-{sort_field}'

        queryset = queryset.order_by(sort_field)

        return queryset


def video_table_view(request):
    """
    Renders a template displaying videos in a tabular dashboard format.

    This view serves the 'video_table.html' template where videos can be displayed and users can search their required videos
    """
    return render(request, 'videos/video_table.html')