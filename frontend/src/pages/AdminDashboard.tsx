import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Users, Activity, HardDrive, Shield, Cpu, Boxes,
  Server, Database, AlertTriangle, CheckCircle, Clock,
} from 'lucide-react';
import { internalApi } from '../api/internalApi';

function KpiCard({ title, value, subtitle, icon: Icon, color }: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: any;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color} shrink-0`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-2xl font-bold text-gray-900 truncate">{value}</p>
          <p className="text-sm text-gray-500 truncate">{title}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
}

function ModuleBadge({ label, status, is_critical }: {
  name: string;
  label: string;
  status: string;
  is_critical: boolean;
}) {
  const colors: Record<string, string> = {
    Operational: 'bg-green-100 text-green-700 border-green-200',
    Degraded: 'bg-amber-100 text-amber-700 border-amber-200',
    Down: 'bg-red-100 text-red-700 border-red-200',
    Maintenance: 'bg-blue-100 text-blue-700 border-blue-200',
  };
  return (
    <div className={`px-3 py-1.5 rounded-lg border text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      <span className="flex items-center gap-1.5">
        {is_critical && <AlertTriangle className="w-3 h-3" />}
        {label}
      </span>
    </div>
  );
}

function StorageBar({ used, total, percentage }: {
  used: string;
  total: string;
  percentage: number;
}) {
  const barColor = percentage > 85 ? 'bg-red-500' : percentage > 65 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-500">{used} used</span>
        <span className="text-gray-500">{total} total</span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <p className="text-xs text-gray-400">{percentage}% utilised</p>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    warning: 'bg-amber-100 text-amber-700',
    info: 'bg-blue-100 text-blue-700',
    success: 'bg-green-100 text-green-700',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[severity] || 'bg-gray-100 text-gray-600'}`}>
      {severity}
    </span>
  );
}

// ── Sub-sections ─────────────────────────────────────────────────────────────

function KpiGrid({ kpis }: { kpis: import('../api/internalApi').DashboardOverview['kpis'] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <KpiCard
        title="Total Users"
        value={kpis.total_users.count}
        subtitle={kpis.total_users.growth}
        icon={Users}
        color="bg-blue-600"
      />
      <KpiCard
        title="Active Users (30d)"
        value={kpis.active_users.count}
        subtitle={`${kpis.active_users.percentage}% of total`}
        icon={Activity}
        color="bg-emerald-600"
      />
      <KpiCard
        title="Departments"
        value={kpis.departments.count}
        subtitle={kpis.departments.growth}
        icon={Boxes}
        color="bg-purple-600"
      />
      <KpiCard
        title="Roles"
        value={kpis.roles.count}
        subtitle={kpis.roles.growth}
        icon={Shield}
        color="bg-orange-600"
      />
      <KpiCard
        title="System Uptime"
        value={kpis.system_uptime.count}
        subtitle={kpis.system_uptime.growth}
        icon={Cpu}
        color="bg-cyan-600"
      />
      <KpiCard
        title="Storage"
        value={`${kpis.storage_used.percentage}%`}
        subtitle={`${kpis.storage_used.used} / ${kpis.storage_used.total}`}
        icon={HardDrive}
        color="bg-rose-600"
      />
    </div>
  );
}

function ModuleStatusSection({ modules }: { modules: import('../api/internalApi').ModuleStatus[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Boxes className="w-4 h-4 text-gray-400" />
        Module Status
      </h3>
      <div className="flex flex-wrap gap-2">
        {modules.map((m) => (
          <ModuleBadge key={m.name} {...m} />
        ))}
      </div>
    </div>
  );
}

function StorageSection({ storage }: { storage: import('../api/internalApi').DashboardStorage }) {
  const pct = storage.storage_total_gb > 0
    ? Math.round((storage.storage_used_gb / storage.storage_total_gb) * 100)
    : 0;
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Database className="w-4 h-4 text-gray-400" />
        Database Storage
      </h3>
      <StorageBar
        used={`${storage.storage_used_gb.toFixed(2)} GB`}
        total={`${storage.storage_total_gb.toFixed(2)} GB`}
        percentage={pct}
      />
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">Status</span>
          <p className="font-medium">{storage.database_status}</p>
        </div>
        <div>
          <span className="text-gray-500">Last Backup</span>
          <p className="font-medium">{storage.last_backup ? new Date(storage.last_backup).toLocaleDateString() : 'N/A'}</p>
        </div>
      </div>
    </div>
  );
}

function SystemInfoSection({ info }: { info: import('../api/internalApi').SystemInfo }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Server className="w-4 h-4 text-gray-400" />
        System
      </h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Python</span>
          <span className="font-mono">{info.python_version || '—'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Django</span>
          <span className="font-mono">{info.django_version || '—'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Server Time</span>
          <span className="font-mono">{info.server_time ? new Date(info.server_time).toLocaleString() : '—'}</span>
        </div>
      </div>
    </div>
  );
}

// ── Tab section ──────────────────────────────────────────────────────────────

function OverviewTab({ overview }: { overview: import('../api/internalApi').DashboardOverview }) {
  return (
    <div className="space-y-6">
      <KpiGrid kpis={overview.kpis} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <ModuleStatusSection modules={overview.module_status} />
        </div>
        <StorageSection storage={overview.database_storage} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SystemInfoSection info={overview.system_info} />
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Shield className="w-4 h-4 text-gray-400" />
            Security
          </h3>
          <pre className="text-xs text-gray-500 overflow-auto max-h-40">
            {JSON.stringify(overview.security_overview, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}

function ActivityTab({ activity }: { activity: import('../api/internalApi').DashboardActivity }) {
  return (
    <div className="space-y-6">
      {/* 7-day chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-3">Login Activity (7 days)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2 font-medium">Date</th>
                <th className="pb-2 font-medium">Logins</th>
                <th className="pb-2 font-medium">Transactions</th>
                <th className="pb-2 font-medium">Errors</th>
              </tr>
            </thead>
            <tbody>
              {activity.system_overview_chart.map((point) => (
                <tr key={point.date} className="border-b border-gray-50">
                  <td className="py-2">{new Date(point.date).toLocaleDateString()}</td>
                  <td className="py-2">{point.logins}</td>
                  <td className="py-2">{point.transactions}</td>
                  <td className="py-2">{point.errors}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top active users */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-3">Top Active Users (30 days)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2 font-medium">User</th>
                <th className="pb-2 font-medium">Role</th>
                <th className="pb-2 font-medium">Logins</th>
                <th className="pb-2 font-medium">Last Active</th>
              </tr>
            </thead>
            <tbody>
              {activity.user_activity.map((u) => (
                <tr key={u.username} className="border-b border-gray-50">
                  <td className="py-2">
                    <div>
                      <p className="font-medium text-gray-900">{u.username}</p>
                      <p className="text-xs text-gray-400">{u.email}</p>
                    </div>
                  </td>
                  <td className="py-2 text-gray-600">{u.role}</td>
                  <td className="py-2">{u.login_count}</td>
                  <td className="py-2 text-gray-500">
                    {u.last_active ? new Date(u.last_active).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">
            Audit Summary ({activity.audit_summary.total_logs} total)
          </h3>
          <div className="space-y-2">
            {activity.audit_summary.by_category.map((cat) => (
              <div key={cat.category} className="flex justify-between text-sm">
                <span className="text-gray-600">{cat.category}</span>
                <span className="font-medium">{cat.count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Recent Audit Logs</h3>
          <div className="space-y-2">
            {activity.audit_summary.recent.slice(0, 6).map((log) => (
              <div key={log.id} className="text-sm border-b border-gray-50 pb-2 last:border-0">
                <p className="font-medium text-gray-900 truncate">{log.description}</p>
                <p className="text-xs text-gray-400">
                  {log.author_name} · {new Date(log.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function AlertsTab({ alerts }: { alerts: import('../api/internalApi').DashboardAlerts }) {
  const unresolved = alerts.system_alerts.filter((a) => !a.is_resolved);
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* System alerts */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          System Alerts
          {unresolved.length > 0 && (
            <span className="ml-auto text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
              {unresolved.length} unresolved
            </span>
          )}
        </h3>
        <div className="space-y-3">
          {alerts.system_alerts.slice(0, 10).map((alert) => (
            <div
              key={alert.id}
              className={`p-3 rounded-lg border text-sm ${
                alert.is_resolved
                  ? 'border-gray-100 bg-gray-50 opacity-60'
                  : 'border-gray-200 bg-white'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 truncate">{alert.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{alert.description}</p>
                </div>
                <SeverityBadge severity={alert.severity} />
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(alert.created_at).toLocaleString()}
                </span>
                {alert.is_resolved && (
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle className="w-3 h-3" />
                    Resolved
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent activities */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-gray-400" />
          Recent Activities
        </h3>
        <div className="space-y-3">
          {alerts.recent_activities.map((act) => (
            <div key={act.id} className="text-sm border-b border-gray-50 pb-3 last:border-0">
              <p className="font-medium text-gray-900 truncate">{act.description}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {act.author_name}
                {act.hospital_name !== 'System' && ` · ${act.hospital_name}`}
                {' · '}
                {new Date(act.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

type Tab = 'overview' | 'activity' | 'alerts';

const tabs: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'activity', label: 'Activity' },
  { key: 'alerts', label: 'Alerts' },
];

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const overview = useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: async () => (await internalApi.getDashboardOverview()).data,
    staleTime: 5 * 60 * 1000, // slow data, cache 5 min
  });

  const activity = useQuery({
    queryKey: ['dashboard', 'activity'],
    queryFn: async () => (await internalApi.getDashboardActivity()).data,
    staleTime: 60 * 1000, // medium cadence, cache 1 min
  });

  const alerts = useQuery({
    queryKey: ['dashboard', 'alerts'],
    queryFn: async () => (await internalApi.getDashboardAlerts()).data,
    staleTime: 30 * 1000, // fast data, cache 30s
  });

  const isLoading = overview.isLoading || activity.isLoading || alerts.isLoading;

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // If any fetch failed, show error state
  if (overview.error || activity.error || alerts.error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <h2 className="text-lg font-semibold text-gray-900">Failed to load dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">Try refreshing the page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-500 mt-1">System-wide overview of MedOS operations</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab.key
                ? 'border-[#0A6253] text-[#0A6253]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && overview.data && (
        <OverviewTab overview={overview.data} />
      )}
      {activeTab === 'activity' && activity.data && (
        <ActivityTab activity={activity.data} />
      )}
      {activeTab === 'alerts' && alerts.data && (
        <AlertsTab alerts={alerts.data} />
      )}
    </div>
  );
}
