"use client";

import { useState, useEffect, useCallback } from "react";
import {
	CheckCircle,
	XCircle,
	ArrowUpCircle,
	Clock,
	AlertTriangle,
	DollarSign,
	Filter,
	RefreshCw,
	ChevronDown
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ApprovalItem {
	uetr: string;
	amount: number;
	currency: string;
	risk_level: string;
	debtor: string;
	creditor: string;
	required_level: string;
	status: string;
	created_at: string;
	approval_chain: Array<{
		level: string;
		approver: string;
		action: string;
		notes?: string;
		timestamp: string;
	}>;
}

interface ApprovalQueueData {
	items: ApprovalItem[];
	total: number;
	pending: number;
	by_level: Record<string, number>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const levelLabels: Record<string, string> = {
	auto: "Auto-Approved",
	level_1: "Analyst",
	level_2: "Senior Analyst",
	level_3: "Manager",
	level_4: "Director",
};

const riskBadgeColors = {
	low: "bg-green-100 text-green-700",
	medium: "bg-yellow-100 text-yellow-700",
	high: "bg-orange-100 text-orange-700",
	critical: "bg-red-100 text-red-700",
};

const statusIcons = {
	pending: Clock,
	approved: CheckCircle,
	rejected: XCircle,
	escalated: ArrowUpCircle,
};

export function ApprovalQueue() {
	const [data, setData] = useState<ApprovalQueueData | null>(null);
	const [loading, setLoading] = useState(true);
	const [statusFilter, setStatusFilter] = useState<string>("pending");
	const [expandedItem, setExpandedItem] = useState<string | null>(null);
	const [actionLoading, setActionLoading] = useState<string | null>(null);

	const fetchQueue = useCallback(async () => {
		setLoading(true);
		try {
			const response = await fetch(
				`${API_BASE_URL}/approval/queue?status=${statusFilter === "all" ? "" : statusFilter}`
			);
			if (!response.ok) throw new Error("Failed to fetch queue");
			const queueData = await response.json();
			setData(queueData);
		} catch (err) {
			console.error("Failed to fetch approval queue:", err);
		} finally {
			setLoading(false);
		}
	}, [statusFilter]);

	useEffect(() => {
		fetchQueue();
	}, [fetchQueue]);

	const handleAction = async (uetr: string, action: "approve" | "reject" | "escalate") => {
		setActionLoading(uetr);
		try {
			const endpoint = action === "escalate"
				? `${API_BASE_URL}/approval/escalate`
				: `${API_BASE_URL}/approval/${action}`;

			const body = action === "escalate"
				? { uetr, reason: "Requires senior review" }
				: { uetr, action, approver_id: "current_user" };

			const response = await fetch(endpoint, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
			});

			if (!response.ok) throw new Error(`Failed to ${action}`);
			await fetchQueue();
		} catch (err) {
			console.error(`Failed to ${action}:`, err);
		} finally {
			setActionLoading(null);
		}
	};

	const formatAmount = (amount: number, currency: string) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: currency,
		}).format(amount);
	};

	const getRiskBadgeColor = (risk: string) => {
		return riskBadgeColors[risk as keyof typeof riskBadgeColors] || riskBadgeColors.medium;
	};

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-3">
					<div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
						<DollarSign className="w-6 h-6 text-blue-600" />
					</div>
					<div>
						<h2 className="text-xl font-bold text-gray-900 dark:text-white">
							Approval Queue
						</h2>
						<p className="text-sm text-gray-500">
							{data?.pending || 0} pending approvals
						</p>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<select
						value={statusFilter}
						onChange={(e) => setStatusFilter(e.target.value)}
						className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm"
					>
						<option value="pending">Pending</option>
						<option value="approved">Approved</option>
						<option value="rejected">Rejected</option>
						<option value="all">All</option>
					</select>
					<button
						onClick={fetchQueue}
						className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
					>
						<RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
					</button>
				</div>
			</div>

			{/* Level Summary */}
			{data && (
				<div className="grid grid-cols-4 gap-4">
					{Object.entries(data.by_level).map(([level, count]) => (
						<div
							key={level}
							className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center"
						>
							<div className="text-2xl font-bold text-gray-900 dark:text-white">
								{count}
							</div>
							<div className="text-xs text-gray-500">{levelLabels[level] || level}</div>
						</div>
					))}
				</div>
			)}

			{/* Queue List */}
			<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
				<div className="divide-y divide-gray-100 dark:divide-gray-800">
					{loading ? (
						<div className="p-8 text-center text-gray-500">
							<RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
							Loading queue...
						</div>
					) : data?.items.length === 0 ? (
						<div className="p-8 text-center text-gray-500">
							<CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
							<p className="font-medium">No items in queue</p>
							<p className="text-sm">All transactions have been processed</p>
						</div>
					) : (
						data?.items.map((item) => {
							const StatusIcon = statusIcons[item.status as keyof typeof statusIcons] || Clock;
							const isExpanded = expandedItem === item.uetr;

							return (
								<motion.div key={item.uetr} layout>
									<div
										className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
										onClick={() => setExpandedItem(isExpanded ? null : item.uetr)}
									>
										<div className="flex items-center justify-between">
											<div className="flex items-center gap-4">
												<StatusIcon className={`w-5 h-5 ${item.status === "approved" ? "text-green-500" :
														item.status === "rejected" ? "text-red-500" :
															"text-yellow-500"
													}`} />
												<div>
													<p className="font-medium text-gray-900 dark:text-white">
														{formatAmount(item.amount, item.currency)}
													</p>
													<p className="text-xs text-gray-500 truncate max-w-[200px]">
														{item.debtor} → {item.creditor}
													</p>
												</div>
											</div>

											<div className="flex items-center gap-3">
												<span className={`px-2 py-0.5 rounded text-xs font-medium ${getRiskBadgeColor(item.risk_level)}`}>
													{item.risk_level}
												</span>
												<span className="text-xs text-gray-500">
													{levelLabels[item.required_level] || item.required_level}
												</span>
												<ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
											</div>
										</div>
									</div>

									<AnimatePresence>
										{isExpanded && (
											<motion.div
												initial={{ height: 0, opacity: 0 }}
												animate={{ height: "auto", opacity: 1 }}
												exit={{ height: 0, opacity: 0 }}
												className="border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50"
											>
												<div className="p-4 space-y-4">
													{/* Transaction Details */}
													<div className="grid grid-cols-2 gap-4 text-sm">
														<div>
															<span className="text-gray-500">UETR:</span>
															<p className="font-mono text-xs">{item.uetr}</p>
														</div>
														<div>
															<span className="text-gray-500">Created:</span>
															<p>{new Date(item.created_at).toLocaleString()}</p>
														</div>
													</div>

													{/* Approval Chain */}
													{item.approval_chain.length > 0 && (
														<div>
															<span className="text-xs text-gray-500 uppercase">Approval History</span>
															<ul className="mt-2 space-y-1">
																{item.approval_chain.map((entry, idx) => (
																	<li key={idx} className="text-xs flex items-center gap-2">
																		<span className="w-2 h-2 rounded-full bg-blue-500" />
																		<span className="font-medium">{entry.action}</span>
																		<span className="text-gray-500">by {entry.approver}</span>
																		<span className="text-gray-400">
																			{new Date(entry.timestamp).toLocaleTimeString()}
																		</span>
																	</li>
																))}
															</ul>
														</div>
													)}

													{/* Action Buttons */}
													{item.status === "pending" && (
														<div className="flex items-center gap-2 pt-2">
															<button
																onClick={(e) => {
																	e.stopPropagation();
																	handleAction(item.uetr, "approve");
																}}
																disabled={actionLoading === item.uetr}
																className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium rounded-lg flex items-center justify-center gap-2"
															>
																<CheckCircle className="w-4 h-4" />
																Approve
															</button>
															<button
																onClick={(e) => {
																	e.stopPropagation();
																	handleAction(item.uetr, "reject");
																}}
																disabled={actionLoading === item.uetr}
																className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium rounded-lg flex items-center justify-center gap-2"
															>
																<XCircle className="w-4 h-4" />
																Reject
															</button>
															<button
																onClick={(e) => {
																	e.stopPropagation();
																	handleAction(item.uetr, "escalate");
																}}
																disabled={actionLoading === item.uetr}
																className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 text-white font-medium rounded-lg flex items-center justify-center gap-2"
															>
																<ArrowUpCircle className="w-4 h-4" />
																Escalate
															</button>
														</div>
													)}
												</div>
											</motion.div>
										)}
									</AnimatePresence>
								</motion.div>
							);
						})
					)}
				</div>
			</div>
		</div>
	);
}
