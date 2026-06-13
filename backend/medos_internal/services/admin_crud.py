"""Factory for admin CRUD ViewSets and Serializers.

Collapses 11 nearly-identical ModelSerializers and 9 nearly-identical
HospitalScopedViewSets into parameterised factory calls, eliminating
~130 lines of boilerplate.

Usage in urls.py registration::

    admin_router.register(
        'departments',
        make_admin_viewset(Department),
        basename='admin-departments',
    )
"""
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import serializers, viewsets

from ..permissions import get_hospital_from_user


# ═══════════════════════════════════════════════════════════════════════════════
#  BASE VIEWSET
# ═══════════════════════════════════════════════════════════════════════════════


class HospitalScopedViewSet(viewsets.ModelViewSet):
    """ViewSet that filters queryset by hospital for non-superusers.

    Subclasses set ``serializer_class`` and may provide ``queryset`` or
    ``get_queryset()``.  The ``hospital_field`` attribute controls which
    field is used for the filter (default ``'hospital'``).
    """
    hospital_field = 'hospital'

    def get_queryset(self):
        qs: QuerySet = super().get_queryset()
        hospital = get_hospital_from_user(self.request.user)
        if hospital is not None:
            qs = qs.filter(**{self.hospital_field: hospital})
        return qs


# ═══════════════════════════════════════════════════════════════════════════════
#  FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def make_admin_serializer(model_class):
    """Build a ModelSerializer with ``fields = '__all__'`` for *model_class*.

    This replaces the standard boilerplate::

        class XSerializer(serializers.ModelSerializer):
            class Meta:
                model = X
                fields = '__all__'
    """
    meta = type('Meta', (), {
        'model': model_class,
        'fields': '__all__',
    })
    return type(
        f'{model_class.__name__}Serializer',
        (serializers.ModelSerializer,),
        {'Meta': meta},
    )


def make_admin_viewset(model_class):
    """Build a ``HospitalScopedViewSet`` for *model_class*.

    Returns a ViewSet subclass with an auto-generated serializer
    (``fields = '__all__'``) and a default queryset of all objects.
    """
    serializer_class = make_admin_serializer(model_class)
    return type(
        f'{model_class.__name__}ViewSet',
        (HospitalScopedViewSet,),
        {
            'serializer_class': serializer_class,
            'queryset': model_class.objects.all(),
        },
    )
