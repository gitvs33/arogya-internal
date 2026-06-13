import { useQuery } from '@tanstack/react-query';
import {
  Building2, Users, Activity, CreditCard, UserPlus, TrendingUp, Hospital,
} from 'lucide-react';
import { internalApi } from '../api/internalApi';

function StatCard({ title, value, icon: Icon, color }: {
  title: string;
  value: number | string;
  icon: any;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-3">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{title}</p>
        </div>
      </div>
    </div>
  );
}

export default function Stats() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      const res = await internalApi.getStats();
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Platform Statistics</h1>
        <p className="text-gray-500 mt-1">Global KPIs across all hospitals</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Hospitals"
          value={stats.total_hospitals}
          icon={Hospital}
          color="bg-[#0A6253]"
        />
        <StatCard
          title="Active Hospitals"
          value={stats.active_hospitals}
          icon={Building2}
          color="bg-green-600"
        />
        <StatCard
          title="Total Staff"
          value={stats.total_staff}
          icon={Users}
          color="bg-blue-600"
        />
        <StatCard
          title="Total Patients"
          value={stats.total_patients}
          icon={UserPlus}
          color="bg-purple-600"
        />
        <StatCard
          title="Encounters (All Time)"
          value={stats.total_encounters}
          icon={Activity}
          color="bg-orange-600"
        />
        <StatCard
          title="Invoices"
          value={stats.total_invoices}
          icon={CreditCard}
          color="bg-teal-600"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-3">
            <TrendingUp className="w-5 h-5 text-[#0A6253]" />
            <h3 className="font-semibold text-gray-900">Growth (30 days)</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xl font-bold text-gray-900">{stats.patients_30d}</p>
              <p className="text-xs text-gray-500">New Patients</p>
            </div>
            <div>
              <p className="text-xl font-bold text-gray-900">{stats.onboarding_30d}</p>
              <p className="text-xs text-gray-500">New Hospitals</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-3">
            <Activity className="w-5 h-5 text-[#0A6253]" />
            <h3 className="font-semibold text-gray-900">Health</h3>
          </div>
          <p className="text-sm text-gray-600">
            {stats.active_hospitals} of {stats.total_hospitals} hospitals active
            ({stats.total_hospitals > 0
              ? Math.round((stats.active_hospitals / stats.total_hospitals) * 100)
              : 0}%)
          </p>
        </div>
      </div>
    </div>
  );
}
