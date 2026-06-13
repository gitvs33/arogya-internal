# MedOS — Architecture Changes Required

> Two sections. Changes needed in the main hospital app first,
> then changes needed in the internal ops project.
> Each change has the exact file and exact fix.

---

## Project 1 — `medos/` (Main Hospital App)

---

### Change 1 — `Hospital` model must be explicitly marked as the migration owner

**Why:** Both projects currently reference the `medos_hospital` table. The main project must be the single source of truth for this table's migrations. Any ambiguity here risks two projects generating conflicting migrations against the same table — one wrong `migrate` command in production corrupts the database.

**File:** `backend/medos/models.py`

```python
class Hospital(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True         # ← this project owns migrations for this table
        db_table = 'medos_hospital'

    def __str__(self):
        return self.name
```

Adding `managed = True` explicitly documents the intent. Anyone opening this file immediately knows this project owns this table.

---

### Change 2 — Every tenant-scoped model needs a `hospital` FK

**Why:** Currently models like `Patient`, `Encounter`, `Invoice`, `LabOrder`, `ICUWard` have no `hospital_id` column. Two hospitals in the database would see each other's data. This is the core SaaS migration that must happen before onboarding any real hospital.

**File:** `backend/medos/models.py`

Add this field to every model listed below:

```python
hospital = models.ForeignKey(
    'Hospital',
    on_delete=models.CASCADE,
    related_name='%(class)ss'
)
```

Models that need it:

| Model | Table |
|---|---|
| `Patient` | `medos_patient` |
| `Encounter` | `medos_encounter` |
| `Invoice` | `medos_invoice` |
| `Payment` | `medos_payment` |
| `RefundRequest` | `medos_refundrequest` |
| `InsuranceClaim` | `medos_insuranceclaim` |
| `LabOrder` | `medos_laborder` |
| `LabParameterResult` | `medos_labparameterresult` |
| `MedicalAlert` | `medos_medicalalert` |
| `Diagnosis` | `medos_diagnosis` |
| `Allergy` | `medos_allergy` |
| `ServiceOrder` | `medos_serviceorder` |
| `ImagingResult` | `medos_imagingresult` |
| `CarePlan` | `medos_careplan` |
| `ICUWard` | `medos_icuward` |
| `ICUBed` | `medos_icubed` |
| `TeleICUSession` | `medos_teleicusession` |
| `SystemActivityLog` | `medos_systemactivitylog` |

After adding the FK to all models:

```bash
python manage.py makemigrations
python manage.py migrate
```

Because these are non-nullable FKs on existing tables, create a default Hospital row first:

```bash
python manage.py shell
>>> from medos.models import Hospital
>>> Hospital.objects.create(name="Default Hospital", slug="default")
```

Then use its ID as the migration default when Django prompts.

---

### Change 3 — `HospitalUserProfile` must include a `hospital` FK

**Why:** Currently `HospitalUserProfile` links a user to a role but not to a hospital. Without this, there is no way to know which hospital a logged-in user belongs to, which means `HospitalScopedViewSet` cannot filter queries by tenant.

**File:** `backend/medos/models.py`

```python
class HospitalUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hospital = models.ForeignKey(            # ADD THIS
        'Hospital',
        on_delete=models.CASCADE,
        related_name='user_profiles'
    )
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    employee_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True)
    must_change_password = models.BooleanField(default=True)  # ADD THIS TOO
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'medos_hospitaluserprofile'
```

---

### Change 4 — Create `HospitalScopedViewSet` base class

**Why:** Every ViewSet currently queries `objects.all()` with no hospital filter. A base class that automatically scopes every query to the logged-in user's hospital fixes this in one place. Every ViewSet that extends it gets tenant isolation for free.

**File:** `backend/medos/views/base.py` (create this new file)

```python
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, NotFound

class HospitalScopedViewSet(viewsets.ModelViewSet):

    def get_hospital(self):
        profile = getattr(self.request.user, 'hospitaluserprofile', None)
        if not profile or not profile.hospital:
            raise PermissionDenied("No hospital associated with this account.")
        return profile.hospital

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(hospital=self.get_hospital())

    def get_object(self):
        obj = super().get_object()
        # Return 404 not 403 — never reveal that a resource exists
        if obj.hospital != self.get_hospital():
            raise NotFound()
        return obj

    def perform_create(self, serializer):
        # Always attach hospital from the token — never trust request body
        serializer.save(hospital=self.get_hospital())
```

Then update every ViewSet in `views/` to extend it:

```python
# Before
class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()

# After
class PatientViewSet(HospitalScopedViewSet):
    queryset = Patient.objects.all()
```

Apply to all ViewSets in:
- `views/patients.py`
- `views/encounters.py`
- `views/billing.py`
- `views/lab.py`
- `views/clinical.py`
- `views/teleicu.py`
- `views/scribe.py`
- `views/sync.py`
- `views/admin_views.py`

---

### Change 5 — `/auth/me/` must return hospital info

**Why:** The frontend auth store needs to know which hospital the logged-in user belongs to. Currently the response returns role and permissions but no hospital context.

**File:** `backend/medos/views/auth.py`

```python
# Update the /auth/me/ response to include:

return Response({
    "id": user.id,
    "email": user.email,
    "role": profile.role.name,
    "role_permissions": profile.role.permissions,
    "must_change_password": profile.must_change_password,
    "hospital": {
        "id": str(profile.hospital.id),
        "name": profile.hospital.name,
        "slug": profile.hospital.slug,
        "is_active": profile.hospital.is_active,
    }
})
```

---

### Change 6 — Auth token must move from sessionStorage to HttpOnly cookie

**Why:** `sessionStorage` is readable by JavaScript. Any XSS vulnerability exposes the token. In a healthcare app this is a compliance risk.

**File:** `backend/medos/views/auth.py` — login view

```python
response = Response({
    "id": user.id,
    "email": user.email,
    "role": profile.role.name,
    "role_permissions": profile.role.permissions,
    "hospital": {...}
    # token NOT in response body
})
response.set_cookie(
    'auth_token',
    token,
    httponly=True,
    secure=True,
    samesite='Strict',
    max_age=86400
)
return response
```

**File:** `frontend/src/api/client.ts`

```typescript
const client = axios.create({
  baseURL: '/api',
  withCredentials: true,  // browser sends HttpOnly cookie automatically
});

// Remove the sessionStorage token interceptor entirely
```

---

### Change 7 — `update_or_create` on HospitalUserProfile must become `create`

**Why:** `update_or_create` silently overwrites an existing profile. If a user email is reused or a form double-submits, it can silently change a user's `hospital_id`. That is a data breach caused by a silent overwrite.

**File:** `backend/medos/views/admin_views.py`

```python
# Replace update_or_create with:

with transaction.atomic():
    user = User.objects.create_user(
        username=validated['username'],
        email=validated['email'],
        password=validated['password'],
    )
    try:
        HospitalUserProfile.objects.create(
            user=user,
            hospital=hospital,
            role=role,
            employee_id=validated.get('employee_id', ''),
            department=validated.get('department', ''),
            must_change_password=True,
        )
    except IntegrityError:
        raise serializers.ValidationError({
            'email': 'A user with this email already exists.'
        })
```

---

### Change 8 — Write tenant isolation tests

**Why:** Without tests, a missing `.filter(hospital=...)` on any endpoint is invisible until a hospital reports seeing another hospital's data. These tests catch leaks automatically.

**File:** `backend/medos/tests/test_tenant_isolation.py` (create this)

```python
class TenantIsolationTest(TestCase):
    def setUp(self):
        self.hospital_a = Hospital.objects.create(name="Hospital A", slug="hospital-a")
        self.hospital_b = Hospital.objects.create(name="Hospital B", slug="hospital-b")
        self.user_a = create_test_user(self.hospital_a)
        self.user_b = create_test_user(self.hospital_b)
        self.patient_a = Patient.objects.create(hospital=self.hospital_a, ...)

    def test_hospital_b_cannot_list_hospital_a_patients(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get('/api/patients/')
        ids = [p['id'] for p in response.data['results']]
        self.assertNotIn(self.patient_a.id, ids)

    def test_hospital_b_cannot_fetch_hospital_a_patient_directly(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(f'/api/patients/{self.patient_a.id}/')
        self.assertEqual(response.status_code, 404)  # not 403
```

Write this test for every major model: Patient, Encounter, Invoice, LabOrder, ICUWard.

---

## Project 2 — `medos_internal_frontend/` (Internal Ops Panel)

---

### Change 1 — `Hospital` model must be `managed = False`

**Why:** This is the most critical fix in the entire document. The internal ops project currently maps `Hospital` to `medos_hospital` — the same table the main project owns. If `managed = True` here, running `makemigrations` in this project generates a conflicting migration for the same table. One `migrate` command in production could drop columns or alter the table in a way that breaks the main app.

**File:** `medos_internal_frontend/backend/models.py`

```python
class Hospital(models.Model):
    # Mirror the fields from the main project exactly
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False        # ← CRITICAL — never run migrations on this table
        db_table = 'medos_hospital'

    def __str__(self):
        return self.name
```

Do the same for every other shared table:

```python
class Role(models.Model):
    class Meta:
        managed = False
        db_table = 'medos_role'

class HospitalUserProfile(models.Model):
    class Meta:
        managed = False
        db_table = 'medos_hospitaluserprofile'

class SystemActivityLog(models.Model):
    class Meta:
        managed = False
        db_table = 'medos_systemactivitylog'

class Patient(models.Model):
    class Meta:
        managed = False
        db_table = 'medos_patient'

class Encounter(models.Model):
    class Meta:
        managed = False
        db_table = 'medos_encounter'

class Invoice(models.Model):
    class Meta:
        managed = False
        db_table = 'medos_invoice'
```

---

### Change 2 — Consolidate 9 dashboard API calls into 1

**Why:** The internal ops dashboard fires 9 separate API calls on mount. This is the same problem as the hospital admin dashboard. Internal ops dashboards don't need real-time granularity — combine slow-changing data into one endpoint.

**File:** `medos_internal_frontend/backend/views/admin_views.py`

Create one combined endpoint:

```python
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def ops_dashboard(request):
    return Response({
        "kpis": get_platform_kpis(),
        "module_status": get_module_status(),
        "system_info": get_system_info(),
        "license_info": get_license_info(),
        "database_storage": get_storage_metrics(),
        # Keep these separate — they change frequently:
        # system_alerts, user_activity, audit_summary, recent_activities
    })
```

**File:** `medos_internal_frontend/frontend/src/pages/OpsDashboard.tsx`

```typescript
// Replace 9 useQuery hooks with:
const { data, isLoading, isError } = useQuery({
  queryKey: ['ops-dashboard'],
  queryFn: () => internalApi.getOpsDashboard(),
  staleTime: 5 * 60 * 1000,  // cache 5 minutes — this data changes slowly
});

// Keep separate fast-refresh queries only for:
useQuery({ queryKey: ['system-alerts'], staleTime: 30_000 });
useQuery({ queryKey: ['recent-activities'], staleTime: 30_000 });
```

---

### Change 3 — Add `IsSuperAdmin` permission class to every internal endpoint

**Why:** Currently the internal ops endpoints may only check `IsAuthenticated`. Any authenticated user who discovers port 8001 could call these endpoints. Every internal endpoint must verify `is_staff=True`.

**File:** `medos_internal_frontend/backend/permissions.py` (create this)

```python
from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    """
    Only allow users with is_staff=True.
    Applied to every endpoint in the internal ops project.
    """
    message = "Access restricted to MedOS operations staff."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )
```

Apply it as the default permission class for the entire internal project:

```python
# medos_internal_frontend/backend/settings.py

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'medos_internal.permissions.IsSuperAdmin',  # applied everywhere by default
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

---

### Change 4 — Impersonation endpoint must write an audit log

**Why:** Impersonating a hospital admin gives your staff access to real patient data. This must always be logged — who impersonated whom, when, and from which IP. Without this, there is no accountability and no compliance trail.

**File:** `medos_internal_frontend/backend/views/hospitals.py`

```python
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def impersonate_hospital_admin(request, hospital_id):
    hospital = get_object_or_404(Hospital, id=hospital_id)

    admin_profile = HospitalUserProfile.objects.filter(
        hospital=hospital,
        role__name='Admin'
    ).select_related('user').first()

    if not admin_profile:
        return Response({'error': 'No admin found for this hospital'}, status=404)

    token, _ = Token.objects.get_or_create(user=admin_profile.user)

    # Always log impersonation — non-negotiable
    SystemActivityLog.objects.create(
        action='impersonate',
        performed_by_id=request.user.id,
        target_user_id=admin_profile.user.id,
        hospital=hospital,
        ip_address=request.META.get('REMOTE_ADDR'),
        notes=f"Impersonation by staff user {request.user.email}"
    )

    return Response({
        'token': token.key,
        'hospital': hospital.name,
        'admin_email': admin_profile.user.email,
        'expires_in': 3600  # tell frontend this is a short-lived session
    })
```

---

### Change 5 — Both Django admin panels must be IP-restricted before production

**Why:** Both `localhost:8000/admin/` and `localhost:8001/admin/` are publicly accessible by default. In production these must never be reachable from the public internet.

**In production nginx config — apply to both projects:**

```nginx
# For medos/backend Django admin
location /admin/ {
    allow 10.0.0.0/8;      # your VPN or office IP range
    deny all;
}

# Same config on the internal ops server
location /admin/ {
    allow 10.0.0.0/8;
    deny all;
}
```

Or restrict at the Django middleware level:

```python
# settings.py (both projects)
INTERNAL_IPS = ['your.office.ip', '10.0.0.0/8']
```

---

## Change Order — Do These in This Sequence

```
medos/ (main app) first:
  1. Mark Hospital model as managed = True explicitly
  2. Add hospital FK to all tenant-scoped models
  3. Add hospital FK to HospitalUserProfile
  4. Run makemigrations + migrate
  5. Create HospitalScopedViewSet base class
  6. Update all ViewSets to extend it
  7. Update /auth/me/ to return hospital info
  8. Replace update_or_create with create + transaction.atomic
  9. Move token to HttpOnly cookie
  10. Write tenant isolation tests — verify they pass

medos_internal_frontend/ after:
  11. Set managed = False on all shared models
  12. Add IsSuperAdmin as default permission class
  13. Consolidate 9 dashboard calls into 1 endpoint
  14. Add audit log to impersonation endpoint
  15. Plan IP restriction for production deployment
```

Never do step 11 before step 1 — the internal project's `managed = False`
only makes sense after the main project explicitly owns the migrations.
