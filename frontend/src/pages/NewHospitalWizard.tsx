import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Building2, ArrowLeft, Loader2 } from 'lucide-react';
import { internalApi } from '../api/internalApi';

const PLANS = [
  { value: 'basic', label: 'Basic', desc: 'Core EMR, basic billing' },
  { value: 'professional', label: 'Professional', desc: '+ TeleICU, lab module, analytics' },
  { value: 'enterprise', label: 'Enterprise', desc: '+ AI scribe, custom integrations' },
];

export default function NewHospitalWizard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    name: '',
    slug: '',
    plan: 'basic',
    address: '',
    phone: '',
    email: '',
    admin_name: '',
    admin_email: '',
    admin_password: '',
  });

  const mutation = useMutation({
    mutationFn: (data: typeof form) => internalApi.createHospital(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hospitals'] });
      navigate('/');
    },
    onError: (err: any) => {
      setError(err.response?.data?.error || err.response?.data?.slug?.[0] || 'Failed to create hospital');
    },
  });

  const update = (field: string, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    // Auto-generate slug from name
    if (field === 'name') {
      setForm((f) => ({ ...f, slug: value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') }));
    }
  };

  const handleSubmit = () => {
    setError('');
    mutation.mutate(form);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <button
        onClick={() => step === 1 ? navigate('/') : setStep(step - 1)}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        {step === 1 ? 'Back to hospitals' : 'Previous step'}
      </button>

      <div className="bg-white rounded-xl border border-gray-200 p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-lg bg-[#0A6253] flex items-center justify-center">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">New Hospital</h1>
            <p className="text-sm text-gray-500">Step {step} of 2</p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex gap-2 mb-8">
          {[1, 2].map((s) => (
            <div
              key={s}
              className={`h-2 flex-1 rounded-full ${s <= step ? 'bg-[#0A6253]' : 'bg-gray-200'}`}
            />
          ))}
        </div>

        {step === 1 && (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-gray-900">Hospital Details</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hospital Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => update('name', e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none"
                placeholder="e.g. City Care Hospital"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Slug *</label>
              <input
                type="text"
                value={form.slug}
                onChange={(e) => update('slug', e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none bg-gray-50"
                placeholder="city-care-hospital"
                required
              />
              <p className="text-xs text-gray-400 mt-1">Used in subdomain, e.g. citycare.medos.com</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Plan</label>
              <div className="grid grid-cols-3 gap-3">
                {PLANS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => update('plan', p.value)}
                    className={`p-3 rounded-lg border text-left text-sm transition-all ${
                      form.plan === p.value
                        ? 'border-[#0A6253] bg-[#E8F5F2] ring-1 ring-[#0A6253]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <p className="font-medium text-gray-900">{p.label}</p>
                    <p className="text-xs text-gray-500 mt-1">{p.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <input
                  type="text"
                  value={form.address}
                  onChange={(e) => update('address', e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none"
                  placeholder="123 Main St"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => update('phone', e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none"
                  placeholder="+1 555-0000"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={() => setStep(2)}
              disabled={!form.name || !form.slug}
              className="w-full bg-[#0A6253] hover:bg-[#08705E] text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50"
            >
              Next — Admin Account
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-gray-900">Admin Account</h2>
            <p className="text-sm text-gray-500">
              This will be the hospital's super admin. They can log in and manage their own staff.
            </p>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Admin Name *</label>
              <input
                type="text"
                value={form.admin_name}
                onChange={(e) => update('admin_name', e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none"
                placeholder="John Smith"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Admin Email *</label>
              <input
                type="email"
                value={form.admin_email}
                onChange={(e) => update('admin_email', e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none"
                placeholder="admin@citycare.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Temporary Password *</label>
              <input
                type="text"
                value={form.admin_password}
                onChange={(e) => update('admin_password', e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0A6253] focus:border-[#0A6253] outline-none"
                placeholder="At least 8 characters"
                minLength={8}
                required
              />
              <p className="text-xs text-gray-400 mt-1">User must change this on first login.</p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="button"
              onClick={handleSubmit}
              disabled={mutation.isPending || !form.admin_name || !form.admin_email || !form.admin_password}
              className="w-full bg-[#0A6253] hover:bg-[#08705E] text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {mutation.isPending ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</>
              ) : (
                'Create Hospital & Send Credentials'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
