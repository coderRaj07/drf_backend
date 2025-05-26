from rest_framework.pagination import PageNumberPagination, CursorPagination

class CustomVideoPagination(PageNumberPagination):
    """
    Custom pagination class for videos using page number-based pagination.

    Attributes:
        page_size (int): Default number of items per page.
        page_size_query_param (str): Query param to override page size (?page_size=20).
        max_page_size (int): Maximum limit for items per page.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CursorVideoPagination(CursorPagination):
    """
    Custom pagination class for videos using cursor-based pagination.
    This is useful for large datasets and provides stable pagination for real-time data.

    Attributes:
        page_size (int): Number of items per page.
        ordering (str): Field used to order results, descending by published_at.
        cursor_query_param (str): Query param used to navigate via cursor (?cursor=<val>).
    """
    def paginate_queryset(self, queryset, request, view=None):
        order_param = request.query_params.get('order', 'desc')
        sort_param = request.query_params.get('sort', 'published_at')
        
        # Allow only safe fields
        allowed_sort_fields = ['published_at', 'title', 'rank', 'similarity']
        if sort_param not in allowed_sort_fields:
            sort_param = 'published_at'

        prefix = '-' if order_param == 'desc' else ''
        self.ordering = f'{prefix}{sort_param}'

        return super().paginate_queryset(queryset, request, view=view)


