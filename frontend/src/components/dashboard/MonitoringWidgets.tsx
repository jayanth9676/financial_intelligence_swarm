"use client";

import { useState, useEffect, useCallback } from "react";
import {
	Activity,
	AlertTriangle,
	Shield,
	TrendingUp,
	Users,
	Clock,
	CheckCircle,
	XCircle,
	RefreshCw
} from "lucide-react";
import { motion } from "framer-motion";

interface MonitoringStats {
	total_transactions: number;
	pending: number;
	investigating: number;
	completed: number;
	high_risk: number;
	alerts_open: number;
	approval_pending: number;
	compliance_issues: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function MonitoringWidgets() {
	const [stats, setStats] = useState<MonitoringStats | null>(null);
	const [loading, setLoading] = useState(true);
	const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

	const fetchStats = useCallback(async () => {
		try {
			const [transactionsRes, alertsRes, approvalRes, complianceRes] = await Promise.all([
				fetch(`${API_BASE_URL}/transactions`),
				fetch(`${API_BASE_URL}/monitor/alerts?status=open`),
				fetch(`${API_BASE_URL}/approval/queue?status=pending`),
				fetch(`${API_BASE_URL}/compliance/status`),
			]);

			const transactions = transactionsRes.ok ? await transactionsRes.json() : { transactions: [] };
			const alerts = alertsRes.ok ? await alertsRes.json() : { alerts: [] };
			const approval = approvalRes.ok ? await approvalRes.json() : { pending: 0 };
			const compliance = complianceRes.ok ? await complianceRes.json() : { overall_status: "unknown" };

			const txList = transactions.transactions || [];

			setStats({
				total_transactions: txList.length,
				pending: txList.filter((t: any) => t.status === "pending").length,
				investigating: txList.filter((t: any) => t.status === "investigating").length,
				completed: txList.filter((t: any) => t.status === "completed").length,
				high_risk: txList.filter((t: any) => t.riskLevel === "high" || t.riskLevel === "critical").length,
				alerts_open: Array.isArray(alerts.alerts) ? alerts.alerts.length : 0,
				approval_pending: approval.pending || 0,
				compliance_issues: compliance.overall_status === "partially_compliant" ? 1 :
					compliance.overall_status === "non_compliant" ? 2 : 0,
			});
			setLastUpdated(new Date());
		} catch (err) {
			console.error("Failed to fetch monitoring stats:", err);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchStats();
		const interval = setInterval(fetchStats, 30000); // Refresh every 30s
		return () => clearInterval(interval);
	}, [fetchStats]);

	const widgets = [
		{
			title: "Total Transactions",
			value: stats?.total_transactions || 0,
			icon: Activity,
			color: "blue",
			bgColor: "bg-blue-100 dark:bg-blue-900/30",
			iconColor: "text-blue-600",
		},
		{
			title: "Pending Review",
			value: stats?.pending || 0,
			icon: Clock,
			color: "yellow",
			bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
			iconColor: "text-yellow-600",
		},
		{
			title: "High Risk",
			value: stats?.high_risk || 0,
			icon: AlertTriangle,
			color: "red",
			bgColor: "bg-red-100 dark:bg-red-900/30",
			iconColor: "text-red-600",
			highlight: (stats?.high_risk || 0) > 0,
		},
		{
			title: "Open Alerts",
			value: stats?.alerts_open || 0,
			icon: Shield,
			color: "orange",
			bgColor: "bg-orange-100 dark:bg-orange-900/30",
			iconColor: "text-orange-600",
			highlight: (stats?.alerts_open || 0) > 0,
		},
		{
			title: "Approval Queue",
			value: stats?.approval_pending || 0,
			icon: Users,
			color: "purple",
			bgColor: "bg-purple-100 dark:bg-purple-900/30",
			iconColor: "text-purple-600",
		},
		{
			title: "Completed",
			value: stats?.completed || 0,
			icon: CheckCircle,
			color: "green",
			bgColor: "bg-green-100 dark:bg-green-900/30",
			iconColor: "text-green-600",
		},
	];

	if (loading) {
		return (
			<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
				{[...Array(6)].map((_, i) => (
					<div key={i} className="bg-gray-100 dark:bg-gray-800 rounded-xl p-4 animate-pulse h-24" />
				))}
			</div>
		);
	}

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
					Live Monitoring
				</h3>
				<div className="flex items-center gap-2 text-xs text-gray-400">
					{lastUpdated && (
						<span>Updated {lastUpdated.toLocaleTimeString()}</span>
					)}
					<button
						onClick={fetchStats}
						className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
					>
						<RefreshCw className="w-3 h-3" />
					</button>
				</div>
			</div>

			<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
				{widgets.map((widget, index) => {
					const Icon = widget.icon;
					return (
						<motion.div
							key={widget.title}
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ delay: index * 0.05 }}
							className={`${widget.bgColor} rounded-xl p-4 border border-transparent ${widget.highlight ? "ring-2 ring-red-400 ring-offset-2 dark:ring-offset-gray-900" : ""
								}`}
						>
							<div className="flex items-center justify-between mb-2">
								<Icon className={`w-5 h-5 ${widget.iconColor}`} />
								{widget.highlight && (
									<span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
								)}
							</div>
							<div className="text-2xl font-bold text-gray-900 dark:text-white">
								{widget.value}
							</div>
							<div className="text-xs text-gray-600 dark:text-gray-400 truncate">
								{widget.title}
							</div>
						</motion.div>
					);
				})}
			</div>
		</div>
	);
}
