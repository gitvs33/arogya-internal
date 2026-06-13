import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Building2, Plus, Users, Mail, ShieldCheck, ShieldAlert,
  Clock, ChevronRight,
} from 'lucide-react';
import { internalApi } from '../api/internalApi';
import type { HospitalListItem } from '../api/internalApi';

const PLAN_BADGES: Record<string, { label: string; color: string }> = {
  basic: { label: 'Basic', color: 'bg-gray-100 text-gray-600' },
  professional: { label: 'Professional', color: 'bg-blue-100 text-blue-700' },
  enterprise: { label: 'Enterprise', color: 'bg-purple-100 text-purple-700' },
};

function HospitalCard({ hospital }: { hospital: HospitalListItem }) {
  const plan = PLAN_BADGES[hospital.plan] || PLAN_BADGES.basic;
  return (
    <Link
      to={`/hospitals/${hospital.id}`}
      className="block bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            hospital.is_active ? 'bg-[#E8F5F2]' : 'bg-gray-100'
          }`}>
            <Building2 className={`w-5 h-5 ${hospital.is_active ? 'text-[#0A6253]' : 'text-gray-400'}`} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 group-hover:text-[#0A6253] transition-colors">
              {hospital.name}
            </h3>
            <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${plan.color}`}>
              {plan.label}
            </span>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" />
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-500 mt-4">
        <div className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5" />
          <span>{hospital.staff_count} staff</span>
        </div>
        {hospital.admin_email && (
          <div className="flex items-center gap-1.5">
            <Mail className="w-3.5 h-3.5" />
            <span className="truncate max-w-[160px]">{hospital.admin_email}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <Clock className="w-3 h-3" />
          {new Date(hospital.created_at).toLocaleDateString()}
        </div>
        {hospital.is_active ? (
          <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
            <ShieldCheck className="w-3 h-3" /> Active
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-red-500 font-medium">
            <ShieldAlert className="w-3 h-3" /> {hospital.is_expired ? 'Expired' : 'Inactive'}
          </span>
        )}
      </div>
    </Link>
  );
}

export default function HospitalsDashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['hospitals'],
    queryFn: async () => {
      const res = await internalApi.getHospitals();
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-6">
        Failed to load hospitals. Make sure you're logged in.
      </div>
    );
  }

  const hospitals = data?.results || [];
  const totalCount = data?.count || 0;
  const activeCount = hospitals.filter((h: HospitalListItem) => h.is_active).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Hospitals</h1>
          <p className="text-gray-500 mt-1">
            {activeCount} active · {totalCount - activeCount} inactive · {totalCount} total
          </p>
        </div>
        <Link
          to="/hospitals/new"
          className="flex items-center gap-2 bg-[#0A6253] hover:bg-[#08705E] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Hospital
        </Link>
      </div>

      {/* Hospital Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {hospitals.map((hospital: HospitalListItem) => (
          <HospitalCard key={hospital.id} hospital={hospital} />
        ))}
      </div>
    </div>
  );
}
