# from rest_framework.views import exception_handler
# from rest_framework.response import Response
# from rest_framework import status

# import logging

# logger = logging.getLogger(__name__)

# def custom_exception_handler(exc, context):
#     # Use DRF's default exception handler to get the initial response
#     response = exception_handler(exc, context)

#     if response is not None:
#         # Log the detailed error for backend developers
#         logger.error(f"Exception occurred: {exc}", exc_info=True)

#         # Customize the structure of the response data for frontend
#         response_data = {
#             'success': False,
#             'status_code': response.status_code,
#         }

#         # Handle validation errors specifically
#         if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(response.data, dict):
#             # Create user-friendly error messages
#             error_messages = []
#             for field, messages in response.data.items():
#                 # Generate a message for required fields
#                 if isinstance(messages, list) and len(messages) > 0:
#                     if hasattr(messages[0], 'code') and messages[0].code == 'required':
#                         error_messages.append(f"{field.replace('_', ' ').title()} is required.")
#                     else:
#                         # Add other error messages (like unique constraint or validation errors)
#                         error_messages.append(str(messages[0]))

#             # Combine error messages into a single string
#             response_data['error'] = ' '.join(error_messages) if error_messages else 'Invalid data provided.'
#         else:
#             # Handle other types of errors (like 404, 403, etc.)
#             response_data['error'] = response.data.get('detail', str(exc))

#         response.data = response_data
#     else:
#         # Log the error for backend analysis
#         logger.error(f"Unhandled Exception: {exc}", exc_info=True)

#         # Handle server errors where no response was generated
#         response = Response({
#             'success': False,
#             'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
#             'error': 'Internal server error. Please try again later.'
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     return response