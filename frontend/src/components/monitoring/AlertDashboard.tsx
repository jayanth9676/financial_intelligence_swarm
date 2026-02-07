"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, Bell, CheckCircle, Clock, Filter, RefreshCw, Shield, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Alert {
	alert_id: string;
	transaction_uetr: string;
	alert_type: string;
	severity: string;
	details: string;
	status: string;
	created_at: string;
	acknowledged_at: string | null;
	resolved_at: string | null;
}

interface AlertQueueResponse {
	alerts: Alert[];
	total: number;
	by_severity: {
		critical: number;
		high: number;
		medium: number;
		low: number;
	};
}

interface AlertDashboardProps {
	onSelectTransaction?: (uetr: string) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const severityColors = {
	critical: {
		bg: "bg-red-100 dark:bg-red-900/30",
		border: "border-red-300 dark:border-red-700",
		text: "text-red-800 dark:text-red-200",
		badge: "bg-red-500",
		icon: AlertTriangle,
	},
	high: {
		bg: "bg-orange-100 dark:bg-orange-900/30",
		border: "border-orange-300 dark:border-orange-700",
		text: "text-orange-800 dark:text-orange-200",
		badge: "bg-orange-500",
		icon: AlertTriangle,
	},
	medium: {
		bg: "bg-yellow-100 dark:bg-yellow-900/30",
		border: "border-yellow-300 dark:border-yellow-700",
		text: "text-yellow-800 dark:text-yellow-200",
		badge: "bg-yellow-500",
		icon: Clock,
	},
	low: {
		bg: "bg-blue-100 dark:bg-blue-900/30",
		border: "border-blue-300 dark:border-blue-700",
		text: "text-blue-800 dark:text-blue-200",
		badge: "bg-blue-500",
		icon: Shield,
	},
};

const alertTypeLabels: Record<string, string> = {
	velocity: "High Velocity",
	structuring: "Structuring Pattern",
	jurisdiction: "High-Risk Jurisdiction",
	round_amount: "Suspicious Amount",
	cross_border: "Cross-Border Risk",
};

export function AlertDashboard({ onSelectTransaction }: AlertDashboardProps) {
	const [alertData, setAlertData] = useState<AlertQueueResponse | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [statusFilter, setStatusFilter] = useState<string>("open");
	const [isMonitoring, setIsMonitoring] = useState(false);

	const fetchAlerts = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const response = await fetch(`${API_BASE_URL}/monitor/alerts?status=${statusFilter}`);
			if (!response.ok) throw new Error("Failed to fetch alerts");
			const data = await response.json();
			setAlertData(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Unknown error");
		} finally {
			setLoading(false);
		}
	}, [statusFilter]);

	const runMonitoringOnAll = async () => {
		setIsMonitoring(true);
		try {
			const response = await fetch(`${API_BASE_URL}/monitor/all`, {
				method: "POST",
			});
			if (!response.ok) throw new Error("Monitoring failed");
			await fetchAlerts();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Monitoring failed");
		} finally {
			setIsMonitoring(false);
		}
	};

	useEffect(() => {
		fetchAlerts();
	}, [fetchAlerts]);

	// Auto-refresh every 30 seconds
	useEffect(() => {
		const interval = setInterval(fetchAlerts, 30000);
		return () => clearInterval(interval);
	}, [fetchAlerts]);

	const getSeverityStyle = (severity: string) => {
		return severityColors[severity as keyof typeof severityColors] || severityColors.low;
	};

	return (
		<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
			{/* Header */}
			<div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
				<div className="flex items-center gap-3">
					<div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
						<Bell className="w-5 h-5 text-red-600 dark:text-red-400" />
					</div>
					<div>
						<h3 className="font-semibold text-gray-900 dark:text-white">Monitoring Alerts</h3>
						<p className="text-xs text-gray-500 dark:text-gray-400">
							Real-time pattern detection
						</p>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<button
						onClick={runMonitoringOnAll}
						disabled={isMonitoring}
						className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg flex items-center gap-1 transition-colors"
					>
						<RefreshCw className={`w-4 h-4 ${isMonitoring ? "animate-spin" : ""}`} />
						Scan All
					</button>
					<select
						value={statusFilter}
						onChange={(e) => setStatusFilter(e.target.value)}
						className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm"
					>
						<option value="open">Open</option>
						<option value="acknowledged">Acknowledged</option>
						<option value="resolved">Resolved</option>
						<option value="all">All</option>
					</select>
				</div>
			</div>

			{/* Severity Summary */}
			{alertData && (
				<div className="grid grid-cols-4 gap-px bg-gray-200 dark:bg-gray-700">
					{[
						{ key: "critical", label: "Critical", count: alertData.by_severity.critical },
						{ key: "high", label: "High", count: alertData.by_severity.high },
						{ key: "medium", label: "Medium", count: alertData.by_severity.medium },
						{ key: "low", label: "Low", count: alertData.by_severity.low },
					].map((item) => {
						const style = getSeverityStyle(item.key);
						return (
							<div
								key={item.key}
								className={`p-3 bg-white dark:bg-gray-900 text-center ${item.count > 0 ? style.bg : ""}`}
							>
								<div className={`text-2xl font-bold ${item.count > 0 ? style.text : "text-gray-400"}`}>
									{item.count}
								</div>
								<div className="text-xs text-gray-500 dark:text-gray-400">{item.label}</div>
							</div>
						);
					})}
				</div>
			)}

			{/* Alert List */}
			<div className="max-h-96 overflow-y-auto">
				{loading && !alertData ? (
					<div className="p-8 text-center text-gray-500">
						<RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
						Loading alerts...
					</div>
				) : error ? (
					<div className="p-8 text-center text-red-500">
						<AlertTriangle className="w-8 h-8 mx-auto mb-2" />
						{error}
					</div>
				) : alertData?.alerts.length === 0 ? (
					<div className="p-8 text-center text-gray-500">
						<CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
						<p className="font-medium">No alerts</p>
						<p className="text-sm">All transactions are within normal parameters</p>
					</div>
				) : (
					<AnimatePresence>
						<ul className="divide-y divide-gray-100 dark:divide-gray-800">
							{alertData?.alerts.map((alert) => {
								const style = getSeverityStyle(alert.severity);
								const Icon = style.icon;
								return (
									<motion.li
										key={alert.alert_id}
										initial={{ opacity: 0, y: -10 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0, y: -10 }}
										className={`p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${style.bg}`}
										onClick={() => onSelectTransaction?.(alert.transaction_uetr)}
									>
										<div className="flex items-start gap-3">
											<div className={`p-1.5 rounded-full ${style.badge}`}>
												<Icon className="w-4 h-4 text-white" />
											</div>
											<div className="flex-1 min-w-0">
												<div className="flex items-center justify-between mb-1">
													<span className={`text-sm font-medium ${style.text}`}>
														{alertTypeLabels[alert.alert_type] || alert.alert_type}
													</span>
													<span className="text-xs text-gray-500">
														{new Date(alert.created_at).toLocaleTimeString()}
													</span>
												</div>
												<p className="text-sm text-gray-700 dark:text-gray-300 mb-1 truncate">
													{alert.details}
												</p>
												<p className="text-xs font-mono text-gray-500 truncate">
													{alert.transaction_uetr}
												</p>
											</div>
										</div>
									</motion.li>
								);
							})}
						</ul>
					</AnimatePresence>
				)}
			</div>

			{/* Footer */}
			<div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-center">
				<span className="text-xs text-gray-500">
					Last updated: {new Date().toLocaleTimeString()} • Auto-refreshes every 30s
				</span>
			</div>
		</div>
	);
}
