from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response

def get_token_for_user(user):
    refresh  = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }

def new_token_for_user(refresh_token):
    refresh = RefreshToken(refresh_token)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }


def standard_response(success, message, data=None, status_code=status.HTTP_200_OK):
    return {
        'success': success,
        'message': message,
        'data': data if data is not None else {},
    }, status_code

def standard_response_api(success, message, data=None, status_code=status.HTTP_200_OK):
    response_data = {
        'success': success,
        'message': message,
        'data': data if data is not None else {},
    }
    return Response(response_data, status=status_code)