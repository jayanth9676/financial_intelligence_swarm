import { Shield, AlertTriangle, CheckCircle, Activity, Lock } from "lucide-react";

interface Transaction {
  uetr: string;
  amount: string | number;
  currency: string;
  riskLevel: "low" | "medium" | "high" | "critical" | "unknown" | null;
  status: "pending" | "investigating" | "completed" | "approved" | "blocked" | "escalated";
}

interface StatsDashboardProps {
  transactions: Transaction[];
}

export function StatsDashboard({ transactions }: StatsDashboardProps) {
  const total = transactions.length;
  const critical = transactions.filter((t) => t.riskLevel === "critical").length;
  const high = transactions.filter((t) => t.riskLevel === "high").length;
  const medium = transactions.filter((t) => t.riskLevel === "medium").length;
  const low = transactions.filter((t) => t.riskLevel === "low").length;

  const completed = transactions.filter((t) =>
    ["completed", "approved", "blocked", "escalated"].includes(t.status)
  ).length;
  const pending = transactions.filter((t) => t.status === "pending").length;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Activity className="w-6 h-6 text-blue-600" />
          FraudOps Dashboard
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Real-time oversight of financial intelligence swarm operations
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Volume</span>
            <Shield className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{total}</div>
          <div className="text-xs text-green-600 mt-1 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            Live Monitoring
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Critical Threats</span>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{critical}</div>
          <div className="text-xs text-red-600 mt-1">Requires immediate action</div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Cases Closed</span>
            <CheckCircle className="w-4 h-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{completed}</div>
          <div className="text-xs text-gray-500 mt-1">
            {pending} pending review
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">System Status</span>
            <Lock className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-xl font-bold text-green-600 dark:text-green-400">Operational</div>
          <div className="text-xs text-gray-500 mt-1">All agents active</div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">Risk Distribution</h3>
        </div>
        <div className="p-4">
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-red-600 dark:text-red-400">Critical Risk</span>
                <span className="text-gray-600 dark:text-gray-400">{critical} cases</span>
              </div>
              <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-red-500 h-2 rounded-full"
                  style={{ width: `${(critical / total) * 100}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-orange-600 dark:text-orange-400">High Risk</span>
                <span className="text-gray-600 dark:text-gray-400">{high} cases</span>
              </div>
              <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-orange-500 h-2 rounded-full"
                  style={{ width: `${(high / total) * 100}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-yellow-600 dark:text-yellow-400">Medium Risk</span>
                <span className="text-gray-600 dark:text-gray-400">{medium} cases</span>
              </div>
              <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-yellow-500 h-2 rounded-full"
                  style={{ width: `${(medium / total) * 100}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-green-600 dark:text-green-400">Low Risk</span>
                <span className="text-gray-600 dark:text-gray-400">{low} cases</span>
              </div>
              <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${(low / total) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}