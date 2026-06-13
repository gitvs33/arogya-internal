import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, ShieldCheck, ShieldAlert, Building2,
  User, Activity,
  Users, CreditCard,
} from 'lucide-react';
import { internalApi } from '../api/internalApi';

export default function HospitalDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: hospital, isLoading } = useQuery({
    queryKey: ['hospital', id],
    queryFn: async () => {
      const res = await internalApi.getHospital(id!);
      return res.data;
    },
    enabled: !!id,
  });

  const activateMutation = useMutation({
    mutationFn: () => internalApi.activateHospital(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hospital', id] }),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => internalApi.deactivateHospital(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hospital', id] }),
  });

  const impersonateMutation = useMutation({
    mutationFn: () => internalApi.impersonateHospital(id!),
    onSuccess: (res) => {
      const data = res.data;
      alert(
        `Impersonation token generated for ${data.user.first_name || data.user.username}\n\n` +
        `Token: ${data.token}\n\n` +
        `Use this token to log into the hospital app as this admin.`
      );
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!hospital) {
    return <div className="text-gray-500">Hospital not found.</div>;
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Back */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to hospitals
      </button>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${
              hospital.is_active ? 'bg-[#E8F5F2]' : 'bg-gray-100'
            }`}>
              <Building2 className={`w-7 h-7 ${hospital.is_active ? 'text-[#0A6253]' : 'text-gray-400'}`} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{hospital.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <span className={`inline-flex items-center gap-1 text-sm font-medium px-2.5 py-0.5 rounded-full ${
                  hospital.is_active
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                }`}>
                  {hospital.is_active ? <ShieldCheck className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
                  {hospital.is_active ? 'Active' : 'Inactive'}
                </span>
                <span className="text-sm text-gray-500">{hospital.slug}</span>
                <span className="text-sm px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium uppercase">
                  {hospital.plan}
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {hospital.is_active ? (
              <button
                onClick={() => deactivateMutation.mutate()}
                className="px-4 py-2 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
              >
                Deactivate
              </button>
            ) : (
              <button
                onClick={() => activateMutation.mutate()}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Activate
              </button>
            )}
            <button
              onClick={() => impersonateMutation.mutate()}
              className="px-4 py-2 text-sm bg-[#0A6253] text-white rounded-lg hover:bg-[#08705E] transition-colors"
            >
              Impersonate
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Users className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{hospital.stats.patients}</p>
              <p className="text-sm text-gray-500">Total Patients</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
              <Activity className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{hospital.stats.encounters_30d}</p>
              <p className="text-sm text-gray-500">Encounters (30d)</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{hospital.stats.invoices}</p>
              <p className="text-sm text-gray-500">Invoices</p>
            </div>
          </div>
        </div>
      </div>

      {/* Admin */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Admin Account</h2>
        {hospital.admin ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-[#E8F5F2] flex items-center justify-center">
                <User className="w-6 h-6 text-[#0A6253]" />
              </div>
              <div>
                <p className="font-medium text-gray-900">
                  {hospital.admin.first_name} {hospital.admin.last_name}
                </p>
                <p className="text-sm text-gray-500">{hospital.admin.email}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Last login: {hospital.admin.last_login ? new Date(hospital.admin.last_login).toLocaleString() : 'Never'}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">No admin account configured.</p>
        )}
      </div>

      {/* Staff Breakdown */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Staff <span className="text-gray-400 font-normal">({hospital.staff_breakdown.total} total)</span>
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(hospital.staff_breakdown.by_role).map(([role, count]) => (
            <div key={role} className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-gray-900">{count as number}</p>
              <p className="text-xs text-gray-500">{role}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
