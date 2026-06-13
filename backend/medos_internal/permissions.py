"""Permission classes for MedOS Internal Operations.

Every endpoint in this project requires the user to be a staff member
(is_staff=True). This is enforced globally via the DEFAULT_PERMISSION_CLASSES
setting in settings.py.
"""
from rest_framework.permissions import BasePermission


class IsStaffUser(BasePermission):
    """Only allow users with is_staff=True (MedOS operations staff).

    This is the default permission for every endpoint in the internal ops
    project. Endpoints that need to be public (like login) override this
    with @permission_classes([]).
    """
    message = "Access restricted to MedOS operations staff."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )


def get_hospital_from_user(user):
    """Return the Hospital for a staff user, or None for superusers.

    HospitalUserProfile.user has ``related_name='+'`` so the reverse
    relation does not exist on the User model. We must query the
    profile table directly.
    """
    if user.is_superuser:
        return None
    from .models import HospitalUserProfile
    profile = (HospitalUserProfile.objects
               .filter(user=user)
               .select_related('hospital')
               .first())
    return profile.hospital if profile else None
