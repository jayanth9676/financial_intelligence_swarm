"use client";

import { useState, useEffect, useCallback } from "react";
import {
	Calendar,
	CheckCircle,
	AlertTriangle,
	Clock,
	FileText,
	Shield,
	RefreshCw,
	ChevronRight,
	AlertCircle
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ComplianceDeadline {
	id: string;
	title: string;
	regulation: string;
	due_date: string;
	status: string;
	priority: string;
	description: string;
}

interface FrameworkStatus {
	framework: string;
	status: string;
	last_review: string;
	controls: string[];
	gaps: string[];
}

interface ComplianceData {
	deadlines: ComplianceDeadline[];
	frameworks: Record<string, FrameworkStatus>;
	overall_status: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const statusColors = {
	compliant: {
		bg: "bg-green-100 dark:bg-green-900/30",
		text: "text-green-700 dark:text-green-300",
		icon: CheckCircle,
	},
	partially_compliant: {
		bg: "bg-yellow-100 dark:bg-yellow-900/30",
		text: "text-yellow-700 dark:text-yellow-300",
		icon: AlertCircle,
	},
	non_compliant: {
		bg: "bg-red-100 dark:bg-red-900/30",
		text: "text-red-700 dark:text-red-300",
		icon: AlertTriangle,
	},
};

const priorityColors = {
	high: "bg-red-500",
	medium: "bg-yellow-500",
	low: "bg-blue-500",
};

export function ComplianceDashboard() {
	const [data, setData] = useState<ComplianceData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [selectedFramework, setSelectedFramework] = useState<string | null>(null);

	const fetchComplianceData = useCallback(async () => {
		setLoading(true);
		try {
			const [deadlinesRes, statusRes] = await Promise.all([
				fetch(`${API_BASE_URL}/compliance/deadlines?days_ahead=90`),
				fetch(`${API_BASE_URL}/compliance/status`),
			]);

			if (!deadlinesRes.ok || !statusRes.ok) {
				throw new Error("Failed to fetch compliance data");
			}

			const deadlines = await deadlinesRes.json();
			const status = await statusRes.json();

			setData({
				deadlines: deadlines.deadlines || [],
				frameworks: status.frameworks || {},
				overall_status: status.overall_status || "unknown",
			});
		} catch (err) {
			setError(err instanceof Error ? err.message : "Unknown error");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchComplianceData();
	}, [fetchComplianceData]);

	const getStatusStyle = (status: string) => {
		return statusColors[status as keyof typeof statusColors] || statusColors.partially_compliant;
	};

	const getDaysUntilDue = (dueDate: string) => {
		const due = new Date(dueDate);
		const now = new Date();
		const diff = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
		return diff;
	};

	if (loading) {
		return (
			<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
				<RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-500" />
				<p className="text-gray-500">Loading compliance data...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
				<AlertTriangle className="w-8 h-8 mx-auto mb-2 text-red-500" />
				<p className="text-red-500">{error}</p>
				<button
					onClick={fetchComplianceData}
					className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
				>
					Retry
				</button>
			</div>
		);
	}

	const overallStyle = data ? getStatusStyle(data.overall_status) : statusColors.partially_compliant;
	const OverallIcon = overallStyle.icon;

	return (
		<div className="space-y-6">
			{/* Overall Status Card */}
			<div className={`rounded-xl border p-6 ${overallStyle.bg} border-gray-200 dark:border-gray-700`}>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-4">
						<div className="p-3 bg-white dark:bg-gray-800 rounded-full shadow-sm">
							<OverallIcon className={`w-8 h-8 ${overallStyle.text}`} />
						</div>
						<div>
							<h2 className="text-xl font-bold text-gray-900 dark:text-white">
								Compliance Status
							</h2>
							<p className={`text-lg font-medium capitalize ${overallStyle.text}`}>
								{data?.overall_status?.replace("_", " ")}
							</p>
						</div>
					</div>
					<button
						onClick={fetchComplianceData}
						className="p-2 hover:bg-white/50 dark:hover:bg-gray-800/50 rounded-lg transition-colors"
					>
						<RefreshCw className="w-5 h-5 text-gray-600 dark:text-gray-400" />
					</button>
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* Regulatory Frameworks */}
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
						<Shield className="w-5 h-5 text-blue-600" />
						<h3 className="font-semibold text-gray-900 dark:text-white">Regulatory Frameworks</h3>
					</div>
					<ul className="divide-y divide-gray-100 dark:divide-gray-800">
						{data && Object.entries(data.frameworks).map(([key, framework]) => {
							const style = getStatusStyle(framework.status);
							const Icon = style.icon;
							return (
								<li
									key={key}
									className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
									onClick={() => setSelectedFramework(selectedFramework === key ? null : key)}
								>
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-3">
											<Icon className={`w-5 h-5 ${style.text}`} />
											<div>
												<p className="font-medium text-gray-900 dark:text-white">
													{framework.framework}
												</p>
												<p className={`text-sm capitalize ${style.text}`}>
													{framework.status.replace("_", " ")}
												</p>
											</div>
										</div>
										<ChevronRight className={`w-5 h-5 text-gray-400 transition-transform ${selectedFramework === key ? "rotate-90" : ""}`} />
									</div>
									<AnimatePresence>
										{selectedFramework === key && (
											<motion.div
												initial={{ height: 0, opacity: 0 }}
												animate={{ height: "auto", opacity: 1 }}
												exit={{ height: 0, opacity: 0 }}
												className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800"
											>
												<div className="text-sm space-y-2">
													<div>
														<span className="text-gray-500">Controls:</span>
														<div className="flex flex-wrap gap-1 mt-1">
															{framework.controls.map((ctrl, i) => (
																<span key={i} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">
																	{ctrl}
																</span>
															))}
														</div>
													</div>
													{framework.gaps.length > 0 && (
														<div>
															<span className="text-orange-600">Gaps:</span>
															<ul className="mt-1 text-orange-600 text-xs">
																{framework.gaps.map((gap, i) => (
																	<li key={i}>• {gap}</li>
																))}
															</ul>
														</div>
													)}
												</div>
											</motion.div>
										)}
									</AnimatePresence>
								</li>
							);
						})}
					</ul>
				</div>

				{/* Upcoming Deadlines */}
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
						<Calendar className="w-5 h-5 text-purple-600" />
						<h3 className="font-semibold text-gray-900 dark:text-white">Upcoming Deadlines</h3>
					</div>
					<ul className="divide-y divide-gray-100 dark:divide-gray-800 max-h-80 overflow-y-auto">
						{data?.deadlines.map((deadline) => {
							const daysUntil = getDaysUntilDue(deadline.due_date);
							const isUrgent = daysUntil <= 7;
							const isOverdue = daysUntil < 0;

							return (
								<li key={deadline.id} className="p-4">
									<div className="flex items-start gap-3">
										<span className={`w-2 h-2 mt-2 rounded-full ${priorityColors[deadline.priority as keyof typeof priorityColors]}`} />
										<div className="flex-1">
											<div className="flex items-center justify-between">
												<p className="font-medium text-gray-900 dark:text-white">
													{deadline.title}
												</p>
												<span className={`text-xs font-medium ${isOverdue ? "text-red-600" : isUrgent ? "text-orange-600" : "text-gray-500"}`}>
													{isOverdue ? `${Math.abs(daysUntil)} days overdue` : `${daysUntil} days`}
												</span>
											</div>
											<p className="text-sm text-gray-500">{deadline.regulation}</p>
											<p className="text-xs text-gray-400 mt-1">{deadline.description}</p>
										</div>
									</div>
								</li>
							);
						})}
					</ul>
				</div>
			</div>
		</div>
	);
}
