from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


def custom_array_pagination(data, page, page_size):
    start = (page - 1) * page_size
    end = start + page_size
    return data[start:end], len(data)


def paginate_queryset(queryset, page=1, page_size=10):
    """
    Generic pagination function for Django QuerySets.
    
    Args:
        queryset: Django QuerySet to paginate
        page: Page number (1-based, defaults to 1)
        page_size: Number of items per page (defaults to 10)
    
    Returns:
        tuple: (paginated_queryset, total_count, pagination_info)
    """
    try:
        # Ensure page and page_size are positive integers
        page = max(1, int(page)) if page else 1
        page_size = max(1, int(page_size)) if page_size else 10
        
        # Get total count
        total_count = queryset.count()
        
        # Calculate pagination
        start = (page - 1) * page_size
        end = start + page_size
        
        # Get paginated queryset
        paginated_queryset = queryset[start:end]
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        pagination_info = {
            'current_page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_previous': has_previous,
            'next_page': page + 1 if has_next else None,
            'previous_page': page - 1 if has_previous else None
        }
        
        return paginated_queryset, total_count, pagination_info
        
    except (ValueError, TypeError) as e:
        # Handle invalid page/page_size values
        page = 1
        page_size = 10
        return paginate_queryset(queryset, page, page_size)


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that provides comprehensive pagination parameters
    and appears in DRF API documentation.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Return a paginated style Response object with comprehensive pagination info.
        """
        return Response({
            'success': True,
            'message': 'Data retrieved successfully.',
            'data': data,
            'pagination': {
                'current_page': self.page.number,
                'page_size': self.page.paginator.per_page,
                'total_count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
                'next_page': self.get_next_link(),
                'previous_page': self.get_previous_link(),
                'next_page_number': self.page.next_page_number() if self.page.has_next() else None,
                'previous_page_number': self.page.previous_page_number() if self.page.has_previous() else None,
            }
        })
    
    def get_schema_fields(self, view):
        """
        Add pagination parameters to OpenAPI schema.
        """
        from drf_spectacular.openapi import AutoSchema
        from drf_spectacular.utils import OpenApiParameter
        
        return [
            OpenApiParameter(
                name=self.page_query_param,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description=f'Page number to retrieve (starts from 1). Default: {self.page_size}',
                required=False,
            ),
            OpenApiParameter(
                name=self.page_size_query_param,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description=f'Number of items per page. Default: {self.page_size}, Max: {self.max_page_size}',
                required=False,
            ),
        ]