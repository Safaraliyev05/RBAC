from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page-number pagination that lets clients request a larger page via
    ?page_size=N (capped), so UIs can load full lists for selection."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000
