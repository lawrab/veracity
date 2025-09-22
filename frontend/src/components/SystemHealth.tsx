'use client';

import { useEffect, useState } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';

export default function SystemHealth() {
  const { apiHealthy, checkingHealth, checkApiHealth } = useDashboardStore();
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  useEffect(() => {
    checkApiHealth();
    setLastChecked(new Date());
  }, []);

  const services = [
    {
      name: 'Backend API',
      status: apiHealthy ? 'healthy' : 'unhealthy',
      description: 'FastAPI server',
      checking: checkingHealth,
    },
    {
      name: 'PostgreSQL',
      status: 'healthy', // Would check actual DB status in real implementation
      description: 'Primary database',
      checking: false,
    },
    {
      name: 'MongoDB',
      status: 'healthy', // Would check actual DB status in real implementation
      description: 'Document storage',
      checking: false,
    },
    {
      name: 'Redis',
      status: 'healthy', // Would check actual cache status in real implementation
      description: 'Cache & sessions',
      checking: false,
    },
    {
      name: 'Elasticsearch',
      status: 'warning', // Would check actual search status in real implementation
      description: 'Search engine',
      checking: false,
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-800 bg-green-100';
      case 'warning':
        return 'text-yellow-800 bg-yellow-100';
      case 'unhealthy':
        return 'text-red-800 bg-red-100';
      default:
        return 'text-gray-800 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return '✓';
      case 'warning':
        return '⚠';
      case 'unhealthy':
        return '✕';
      default:
        return '?';
    }
  };

  const healthyCount = services.filter(s => s.status === 'healthy').length;
  const overallHealth = healthyCount === services.length ? 'healthy' : 
                       healthyCount >= services.length * 0.7 ? 'warning' : 'unhealthy';

  return (
    <div className="bg-white dark:bg-gray-800 shadow dark:shadow-gray-700/20 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">System Health</h2>
        <button
          onClick={() => {
            checkApiHealth();
            setLastChecked(new Date());
          }}
          disabled={checkingHealth}
          className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
        >
          {checkingHealth ? 'Checking...' : 'Refresh'}
        </button>
      </div>

      {/* Overall Status */}
      <div className={`rounded-lg p-4 mb-4 ${getStatusColor(overallHealth)}`}>
        <div className="flex items-center">
          <span className="text-lg mr-2">{getStatusIcon(overallHealth)}</span>
          <div>
            <p className="font-medium">
              System Status: {overallHealth.charAt(0).toUpperCase() + overallHealth.slice(1)}
            </p>
            <p className="text-sm opacity-75">
              {healthyCount} of {services.length} services operational
            </p>
          </div>
        </div>
      </div>

      {/* Service Details */}
      <div className="space-y-3">
        {services.map((service) => (
          <div key={service.name} className="flex items-center justify-between p-3 border dark:border-gray-600 rounded-lg">
            <div className="flex items-center">
              <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
                <span className="text-xs">🔧</span>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">{service.name}</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">{service.description}</p>
              </div>
            </div>
            <div className="flex items-center">
              {service.checking ? (
                <span className="text-xs text-gray-500 mr-2">Checking...</span>
              ) : null}
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(service.status)}`}>
                <span className="mr-1">{getStatusIcon(service.status)}</span>
                {service.status}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-xs text-gray-500 text-center">
        Last checked: {lastChecked ? lastChecked.toLocaleTimeString() : '--'}
      </div>
    </div>
  );
}