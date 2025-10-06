'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface Service {
  service: string;
  unlocked_at: string;
}

export default function Dashboard() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.konqer.app';

    fetch(`${apiUrl}/user/services`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    .then(r => {
      if (!r.ok) {
        throw new Error('Failed to fetch services');
      }
      return r.json();
    })
    .then(data => {
      setServices(data);
      setLoading(false);
    })
    .catch(err => {
      console.error(err);
      setError(err.message);
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your services...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Error: {error}</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            Back to Login
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-6 py-16">
      <div className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Your Services</h1>
          <p className="mt-2 text-gray-600">{services.length} services unlocked</p>
        </div>
        <button
          onClick={() => {
            localStorage.removeItem('auth_token');
            router.push('/');
          }}
          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
        >
          Logout
        </button>
      </div>

      {services.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No services unlocked yet</p>
          <a
            href="/pricing"
            className="mt-4 inline-block px-6 py-3 bg-blue-600 text-white rounded"
          >
            View Plans
          </a>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map(service => (
            <div
              key={service.service}
              className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <h3 className="font-semibold text-lg capitalize">
                {service.service.replace(/-/g, ' ')}
              </h3>
              <p className="text-sm text-gray-500 mt-2">
                Unlocked: {new Date(service.unlocked_at).toLocaleDateString()}
              </p>
              <a
                href={`https://${service.service}.konqer.app`}
                className="mt-4 inline-block w-full text-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Use Service →
              </a>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
