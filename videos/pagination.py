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
    Custom cursor-based pagination class for video listings.

    This paginator allows dynamic ordering based on query parameters and 
    is optimized for large or real-time datasets.

    Query Parameters:
        - sort (str): The field to sort by. Allowed values: 'published_at', 'title', 'rank', 'similarity'.
                      Defaults to 'published_at'.
        - order (str): The order direction. Can be 'asc' or 'desc'. Defaults to 'desc'.
        - cursor (str): The pagination cursor provided by the response to fetch the next page.

    Notes:
        - The actual pagination behavior (like page size and cursor handling) is inherited 
          from `CursorPagination`.
        - The `ordering` is set dynamically per request based on the query parameters.
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


