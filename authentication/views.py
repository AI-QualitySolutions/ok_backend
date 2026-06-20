from django.core.exceptions import FieldError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.generics import CreateAPIView, GenericAPIView, ListAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from authentication.models import MyUser, Company
from authentication.serializers import UserLoginSerializer, UserRegistrationSerializer, MyUserSerializer, PermissionListSerializer, CompanySerializer, UserPermissionListSerializer
from authentication.utils import get_token_for_user, standard_response
from django.shortcuts import get_object_or_404


from tent.utils import CustomPagination
from utils.time import Current_saudi_time


class CompanyListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = None
        try:
            company = Company.objects.only('name', 'logo').all()
            serializer = CompanySerializer(company, many=True)
        except Company.DoesNotExist:  # pylint: disable=no-member
            return Response({
                'success': False,
                'message': 'Company not found.',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'message': 'Company retrieved successfully.',
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class CompanyWithLogo(APIView):
    """API view to retrieve a company's name and logo by company name or user email.

        GET /endpoint/?name=<company_name> or /endpoint/?user=<user_email>
        Returns:
            - 200: Company details with name and logo URL (if available).
            - 400: Missing or invalid query parameters.
            - 404: Company or user not found.
        """

    def get(self, request, *args, **kwargs):
        name = request.query_params.get('name')
        company = None

        # Option 1: If 'name' param is provided
        if name:
            try:
                company = Company.objects.only(
                    'name', 'logo', 'icon').get(name=name)
            except Company.DoesNotExist:  # pylint: disable=no-member
                return Response({
                    'success': False,
                    'message': 'Company not found.',
                    'data': None
                }, status=status.HTTP_404_NOT_FOUND)

        # Option 2: If user is authenticated and has a company
        elif request.user and request.user.is_authenticated:
            if request.user.company:
                company = Company.objects.only('name', 'logo', 'icon').filter(
                    id=request.user.company_id).first()
            else:
                return Response({
                    'success': False,
                    'message': 'Authenticated user has no associated company.',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

        # If neither condition is met
        else:
            return Response({
                'success': False,
                'message': 'Provide a company name or authenticate the user.',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Return response
        return Response({
            'success': True,
            'message': 'Company retrieved successfully.',
            'data': CompanySerializer(company, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class PermissionList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        company = user.company
        serializer = None

        if user.is_admin:
            serializer = PermissionListSerializer(company)
        elif user.is_staff:
            serializer = UserPermissionListSerializer(user)

        return Response({
            "success": True,
            "message": "Company retrieved successfully.",
            "data": serializer.data
        })


class UserPermissionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserPermissionListSerializer(request.user)
        return Response({
            "success": True,
            "message": "User permissions retrieved successfully.",
            "data": serializer.data
        })


class CompanyWithPerm(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.company:
            return Response({
                "success": False,
                "message": "User is not assigned to any company.",
                "data": None
            }, status=404)
        company = user.company
        serializer = PermissionListSerializer(
            company, context={'request': request})
        return Response({
            "success": True,
            "message": "Company retrieved successfully.",
            "data": serializer.data
        })


@method_decorator(csrf_exempt, name='dispatch')
class UserRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(company=request.user.company)
            return Response(*standard_response(True, 'User registered successfully.', serializer.data, status.HTTP_201_CREATED))
        else:
            return Response(*standard_response(False, 'Validation failed.', serializer.errors, status.HTTP_400_BAD_REQUEST))


@method_decorator(csrf_exempt, name='dispatch')
class UserLoginView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        return Response(*standard_response(True, 'User logged in successfully.', {
            'token': get_token_for_user(user),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
        }))


@method_decorator(csrf_exempt, name='dispatch')
class UserView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    serializer_class = MyUserSerializer

    def get(self, request, *args, **kwargs):
        queryset = MyUser.objects.filter(
            company=request.user.company
        ).order_by('id')

        paginate = request.query_params.get(
            'paginate', 'true').lower() == 'true'

        if paginate:
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(
                queryset, request, view=self)
            serializer = self.serializer_class(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True)
        return Response({
            "success": True,
            "message": "User list retrieved successfully without pagination.",
            "data": serializer.data
        })

    def delete(self, request, pk, *args, **kwargs):
        try:
            user = MyUser.objects.get(id=pk)
            if user.company != request.user.company:
                return Response({
                    "success": False,
                    "message": f"User with ID {pk} does not belong to your company."
                }, status=403)

            user.delete()
            return Response({
                "success": True,
                "message": f"User with ID {pk} deleted successfully."
            }, status=200)

        except MyUser.DoesNotExist:
            return Response({
                "success": False,
                "message": f"User with ID {pk} not found."
            }, status=404)

    def patch(self, request, pk, *args, **kwargs):
        try:
            user = MyUser.objects.get(id=pk)
            if user.company != request.user.company:
                return Response({
                    "success": False,
                    "message": f"User with ID {pk} does not belong to your company."
                }, status=403)

            serializer = UserRegistrationSerializer(
                user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(company=request.user.company)

            return Response({
                "success": True,
                "message": f"User with ID {pk} updated successfully.",
                "results": serializer.data
            }, status=200)

        except MyUser.DoesNotExist:
            return Response({
                "success": False,
                "message": f"User with ID {pk} not found."
            }, status=404)


class ServerTime(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_time, end_time = Current_saudi_time()
        return Response({"server_time": end_time.isoformat()})
