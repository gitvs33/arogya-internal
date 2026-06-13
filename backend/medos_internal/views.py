"""Internal operations API — staff-only endpoints for the MedOS ops panel.

All endpoints require request.user.is_staff == True.
Hospital staff and regular users cannot access these.
"""
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .auth import token_is_expired, regenerate_token, ExpiringTokenAuthentication
from .permissions import IsStaffUser, get_hospital_from_user
from .models import (
    Hospital, Role, HospitalUserProfile, SystemActivityLog,
    AdminModule, BackupRecord, Department, DeviceIntegration,
    LicenseInfo, MasterDataEntry, SecurityPolicy, SystemSetting, WorkflowDefinition,
)
from .serializers import (
    InternalLoginSerializer, HospitalListSerializer, HospitalDetailSerializer,
    HospitalCreateSerializer, HospitalUpdateSerializer,
    AdminUserSerializer, AdminUserCreateSerializer, AdminRoleSerializer,
)
from .services import dashboard as dashboard_service
from .services.admin_crud import HospitalScopedViewSet, make_admin_viewset
from .services import hospital_onboarding as onboarding_service
from .services import user_management
from .services import hospital_detail as hospital_detail_service

User = get_user_model()





# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════


@api_view(['POST'])
@permission_classes([])
def internal_login(request):
    """Staff login — only users with is_staff=True can proceed."""
    serializer = InternalLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(
        request,
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
    )
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_staff:
        return Response({'error': 'Access denied. Staff privileges required.'}, status=status.HTTP_403_FORBIDDEN)

    token, _ = Token.objects.get_or_create(user=user)
    if token_is_expired(token):
        token = regenerate_token(token)
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        },
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  HOSPITAL MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_list(request):
    """List all hospitals with staff counts (paginated)."""
    hospitals = Hospital.objects.annotate(
        staff_count=Count('staff_profiles', filter=Q(staff_profiles__is_active=True))
    ).order_by('-created_at')

    # N+1 fix: fetch all admin profiles in one query instead of 2 per hospital
    admin_profiles = {
        p.hospital_id: p
        for p in HospitalUserProfile.objects.filter(
            role__name__iexact='Admin'
        ).select_related('user')
    }

    paginator = PageNumberPagination()
    paginator.page_size = 50
    page = paginator.paginate_queryset(hospitals, request)

    serializer = HospitalListSerializer(
        page, many=True,
        context={'admin_profiles': admin_profiles},
    )
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_create(request):
    """Create a new hospital with its admin account."""
    serializer = HospitalCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        hospital = onboarding_service.onboard_hospital(
            name=data['name'],
            slug=data['slug'],
            plan=data['plan'],
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            admin_name=data['admin_name'],
            admin_email=data['admin_email'],
            admin_password=data['admin_password'],
            performed_by=request.user,
        )
        # Fetch the just-created admin profile so the serializer doesn't
        # need to query separately.
        admin_profile = HospitalUserProfile.objects.filter(
            hospital=hospital, role__name__iexact='Admin',
        ).select_related('user').first()
        admin_profiles = {hospital.pk: admin_profile} if admin_profile else {}
        result = HospitalListSerializer(
            hospital, context={'admin_profiles': admin_profiles},
        )
        return Response(result.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_detail_get(request, pk):
    """Full hospital detail with staff breakdown, admin info, stats."""
    try:
        hospital = Hospital.objects.get(pk=pk)
    except Hospital.DoesNotExist:
        return Response({'error': 'Hospital not found'}, status=status.HTTP_404_NOT_FOUND)

    detail_data = hospital_detail_service.read_hospital_detail(hospital)
    serializer = HospitalDetailSerializer(hospital, context=detail_data)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_detail_update(request, pk):
    """Update hospital fields."""
    try:
        hospital = Hospital.objects.get(pk=pk)
    except Hospital.DoesNotExist:
        return Response({'error': 'Hospital not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = HospitalUpdateSerializer(hospital, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(HospitalDetailSerializer(
        hospital, context=hospital_detail_service.read_hospital_detail(hospital),
    ).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_activate(request, pk):
    """Set hospital.is_active = True."""
    try:
        hospital = Hospital.objects.get(pk=pk)
    except Hospital.DoesNotExist:
        return Response({'error': 'Hospital not found'}, status=status.HTTP_404_NOT_FOUND)
    hospital.is_active = True
    hospital.save(update_fields=['is_active'])
    return Response({'status': 'activated', 'name': hospital.name})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_deactivate(request, pk):
    """Set hospital.is_active = False."""
    try:
        hospital = Hospital.objects.get(pk=pk)
    except Hospital.DoesNotExist:
        return Response({'error': 'Hospital not found'}, status=status.HTTP_404_NOT_FOUND)
    hospital.is_active = False
    hospital.save(update_fields=['is_active'])
    return Response({'status': 'deactivated', 'name': hospital.name})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffUser])
def hospital_impersonate(request, pk):
    """Return a token for the hospital's admin user."""
    try:
        hospital = Hospital.objects.get(pk=pk)
    except Hospital.DoesNotExist:
        return Response({'error': 'Hospital not found'}, status=status.HTTP_404_NOT_FOUND)

    admin_profile = HospitalUserProfile.objects.filter(
        hospital=hospital,
        role__name__iexact='Admin',
    ).select_related('user').first()

    if not admin_profile:
        return Response({'error': 'No admin user found for this hospital'}, status=status.HTTP_404_NOT_FOUND)

    token, _ = Token.objects.get_or_create(user=admin_profile.user)
    if token_is_expired(token):
        token = regenerate_token(token)

    SystemActivityLog.objects.create(
        event_type='impersonation',
        description=f'{request.user.username} impersonated {admin_profile.user.username} at {hospital.name}',
        author_name=request.user.username,
        hospital=hospital,
    )

    return Response({
        'token': token.key,
        'user': {
            'id': admin_profile.user.id,
            'username': admin_profile.user.username,
            'email': admin_profile.user.email,
            'first_name': admin_profile.user.first_name,
            'last_name': admin_profile.user.last_name,
            'hospital_id': str(hospital.id),
            'hospital_name': hospital.name,
        },
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  PLATFORM STATS
# ═══════════════════════════════════════════════════════════════════════════════


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffUser])
def platform_stats(request):
    """Platform-wide KPIs for the internal ops dashboard."""
    return Response(dashboard_service.read_platform_stats())


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD  — 3 composite endpoints
# ═══════════════════════════════════════════════════════════════════════════════
#
# Dashboard is always global (no hospital scoping). Per-hospital analytics
# is a separate feature on a different page.


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffUser])
def admin_overview(request):
    """Composite: KPIs + module status + storage + license + system info + security."""
    return Response(dashboard_service.read_overview())


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffUser])
def admin_activity(request):
    """Composite: 7-day chart + user activity + audit summary."""
    return Response(dashboard_service.read_activity())


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffUser])
def admin_alerts(request):
    """Composite: unresolved system alerts + recent activities."""
    return Response(dashboard_service.read_alerts())


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN CRUD VIEWSETS
# ═══════════════════════════════════════════════════════════════════════════════

from rest_framework.routers import DefaultRouter


class HospitalAdminViewSet(HospitalScopedViewSet):
    """Admin panel CRUD for users."""
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.all().select_related(
            'hospital_profile', 'hospital_profile__role'
        )
        hospital = get_hospital_from_user(self.request.user)
        if hospital is not None:
            qs = qs.filter(hospital_profile__hospital=hospital)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = user_management.create_admin_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                hospital_id=data['hospital_id'],
                role_id=data.get('role_id'),
                employee_id=data.get('employee_id'),
                department=data.get('department', ''),
                designation=data.get('designation', ''),
            )
            return Response(AdminUserSerializer(result).data, status=status.HTTP_201_CREATED)
        except Hospital.DoesNotExist:
            return Response({'error': 'Hospital not found'}, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminRoleViewSet(HospitalScopedViewSet):
    """Admin panel CRUD for roles."""
    serializer_class = AdminRoleSerializer

    def get_queryset(self):
        qs = Role.objects.annotate(
            user_count=Count('profiles', filter=Q(profiles__is_active=True))
        )
        hospital = get_hospital_from_user(self.request.user)
        if hospital is not None:
            qs = qs.filter(hospital=hospital)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)





# Build router for admin CRUD endpoints
admin_router = DefaultRouter()
admin_router.register(r'users', HospitalAdminViewSet, basename='admin-users')
admin_router.register(r'roles', AdminRoleViewSet, basename='admin-roles')
admin_router.register(r'departments', make_admin_viewset(Department), basename='admin-departments')
admin_router.register(r'security-policies', make_admin_viewset(SecurityPolicy), basename='admin-security-policies')
admin_router.register(r'system-settings', make_admin_viewset(SystemSetting), basename='admin-system-settings')
admin_router.register(r'workflows', make_admin_viewset(WorkflowDefinition), basename='admin-workflows')
admin_router.register(r'device-integrations', make_admin_viewset(DeviceIntegration), basename='admin-device-integrations')
admin_router.register(r'master-data', make_admin_viewset(MasterDataEntry), basename='admin-master-data')
admin_router.register(r'backups', make_admin_viewset(BackupRecord), basename='admin-backups')
admin_router.register(r'modules', make_admin_viewset(AdminModule), basename='admin-modules')
admin_router.register(r'licenses', make_admin_viewset(LicenseInfo), basename='admin-licenses')
