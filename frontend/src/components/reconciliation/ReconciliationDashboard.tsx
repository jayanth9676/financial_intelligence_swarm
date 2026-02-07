"use client";

import { useState, useEffect, useCallback } from "react";
import {
	FileSpreadsheet,
	CheckCircle,
	AlertTriangle,
	RefreshCw,
	ArrowRightLeft,
	DollarSign,
	FileWarning,
	TrendingUp
} from "lucide-react";
import { motion } from "framer-motion";

interface ReconciliationStatus {
	internal_records: number;
	statement_entries: number;
	matched: number;
	unmatched: number;
	discrepancies: number;
	match_rate: number;
	total_internal_value: number;
	total_statement_value: number;
	variance: number;
	variance_percentage: number;
	last_reconciled: string;
}

interface Discrepancy {
	type: string;
	record_id?: string;
	entry_id?: string;
	issues?: string[];
	amount?: number;
	reference?: string;
}

interface MatchingResult {
	matched_count: number;
	unmatched_internal_count: number;
	unmatched_statement_count: number;
	discrepancies: Discrepancy[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function ReconciliationDashboard() {
	const [status, setStatus] = useState<ReconciliationStatus | null>(null);
	const [matching, setMatching] = useState<MatchingResult | null>(null);
	const [loading, setLoading] = useState(true);
	const [reconciling, setReconciling] = useState(false);

	const fetchStatus = useCallback(async () => {
		setLoading(true);
		try {
			const [statusRes, matchingRes] = await Promise.all([
				fetch(`${API_BASE_URL}/reconciliation/status`),
				fetch(`${API_BASE_URL}/reconciliation/match`),
			]);

			if (statusRes.ok) {
				setStatus(await statusRes.json());
			}
			if (matchingRes.ok) {
				setMatching(await matchingRes.json());
			}
		} catch (err) {
			console.error("Failed to fetch reconciliation data:", err);
		} finally {
			setLoading(false);
		}
	}, []);

	const runReconciliation = async () => {
		setReconciling(true);
		try {
			const response = await fetch(`${API_BASE_URL}/reconciliation/run`, {
				method: "POST",
			});
			if (response.ok) {
				await fetchStatus();
			}
		} catch (err) {
			console.error("Reconciliation failed:", err);
		} finally {
			setReconciling(false);
		}
	};

	useEffect(() => {
		fetchStatus();
	}, [fetchStatus]);

	const formatCurrency = (amount: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "EUR",
		}).format(amount);
	};

	const getDiscrepancyTypeLabel = (type: string) => {
		const labels: Record<string, string> = {
			partial_match: "Partial Match",
			missing_internal_record: "Missing Internal Record",
			missing_statement_entry: "Missing Statement Entry",
			amount_mismatch: "Amount Mismatch",
		};
		return labels[type] || type;
	};

	if (loading) {
		return (
			<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
				<RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-500" />
				<p className="text-gray-500">Loading reconciliation data...</p>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-3">
					<div className="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg">
						<FileSpreadsheet className="w-6 h-6 text-teal-600" />
					</div>
					<div>
						<h2 className="text-xl font-bold text-gray-900 dark:text-white">
							Reconciliation
						</h2>
						<p className="text-sm text-gray-500">
							Statement matching & discrepancy resolution
						</p>
					</div>
				</div>
				<button
					onClick={runReconciliation}
					disabled={reconciling}
					className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium rounded-lg flex items-center gap-2 transition-colors"
				>
					<RefreshCw className={`w-4 h-4 ${reconciling ? "animate-spin" : ""}`} />
					Run Reconciliation
				</button>
			</div>

			{/* Status Cards */}
			<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
				>
					<div className="flex items-center justify-between mb-2">
						<span className="text-sm text-gray-500">Match Rate</span>
						<TrendingUp className="w-4 h-4 text-green-500" />
					</div>
					<div className="text-2xl font-bold text-gray-900 dark:text-white">
						{status?.match_rate.toFixed(1)}%
					</div>
					<div className="text-xs text-gray-500 mt-1">
						{status?.matched} of {status?.internal_records} records
					</div>
				</motion.div>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ delay: 0.1 }}
					className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
				>
					<div className="flex items-center justify-between mb-2">
						<span className="text-sm text-gray-500">Variance</span>
						<DollarSign className="w-4 h-4 text-yellow-500" />
					</div>
					<div className={`text-2xl font-bold ${status && status.variance !== 0 ? "text-yellow-600" : "text-green-600"}`}>
						{formatCurrency(status?.variance || 0)}
					</div>
					<div className="text-xs text-gray-500 mt-1">
						{status?.variance_percentage.toFixed(2)}% of total
					</div>
				</motion.div>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ delay: 0.2 }}
					className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
				>
					<div className="flex items-center justify-between mb-2">
						<span className="text-sm text-gray-500">Discrepancies</span>
						<FileWarning className={`w-4 h-4 ${matching && matching.discrepancies.length > 0 ? "text-red-500" : "text-green-500"}`} />
					</div>
					<div className={`text-2xl font-bold ${matching && matching.discrepancies.length > 0 ? "text-red-600" : "text-green-600"}`}>
						{matching?.discrepancies.length || 0}
					</div>
					<div className="text-xs text-gray-500 mt-1">
						Requires resolution
					</div>
				</motion.div>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ delay: 0.3 }}
					className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
				>
					<div className="flex items-center justify-between mb-2">
						<span className="text-sm text-gray-500">Unmatched</span>
						<ArrowRightLeft className="w-4 h-4 text-orange-500" />
					</div>
					<div className="text-2xl font-bold text-gray-900 dark:text-white">
						{(matching?.unmatched_internal_count || 0) + (matching?.unmatched_statement_count || 0)}
					</div>
					<div className="text-xs text-gray-500 mt-1">
						{matching?.unmatched_internal_count} internal, {matching?.unmatched_statement_count} statement
					</div>
				</motion.div>
			</div>

			{/* Comparison View */}
			<div className="grid grid-cols-2 gap-6">
				{/* Internal Records */}
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-blue-50 dark:bg-blue-900/20">
						<h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
							<FileSpreadsheet className="w-4 h-4 text-blue-600" />
							Internal Records
						</h3>
						<p className="text-xs text-gray-500 mt-1">
							{status?.internal_records} records • {formatCurrency(status?.total_internal_value || 0)}
						</p>
					</div>
					<div className="max-h-64 overflow-y-auto">
						<div className="p-4 text-center text-sm text-gray-500">
							<CheckCircle className="w-6 h-6 mx-auto mb-2 text-green-500" />
							Records loaded for matching
						</div>
					</div>
				</div>

				{/* Bank Statement */}
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-green-50 dark:bg-green-900/20">
						<h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
							<FileSpreadsheet className="w-4 h-4 text-green-600" />
							Bank Statement (camt.053)
						</h3>
						<p className="text-xs text-gray-500 mt-1">
							{status?.statement_entries} entries • {formatCurrency(status?.total_statement_value || 0)}
						</p>
					</div>
					<div className="max-h-64 overflow-y-auto">
						<div className="p-4 text-center text-sm text-gray-500">
							<CheckCircle className="w-6 h-6 mx-auto mb-2 text-green-500" />
							Statement entries loaded
						</div>
					</div>
				</div>
			</div>

			{/* Discrepancies List */}
			{matching && matching.discrepancies.length > 0 && (
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-red-50 dark:bg-red-900/20">
						<h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
							<AlertTriangle className="w-4 h-4 text-red-600" />
							Discrepancies Requiring Resolution
						</h3>
					</div>
					<ul className="divide-y divide-gray-100 dark:divide-gray-800">
						{matching.discrepancies.map((disc, idx) => (
							<li key={idx} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
								<div className="flex items-center justify-between">
									<div>
										<span className="text-sm font-medium text-gray-900 dark:text-white">
											{getDiscrepancyTypeLabel(disc.type)}
										</span>
										<p className="text-xs text-gray-500 mt-1">
											{disc.record_id && `Record: ${disc.record_id}`}
											{disc.entry_id && ` • Entry: ${disc.entry_id}`}
											{disc.reference && ` • Ref: ${disc.reference}`}
										</p>
										{disc.issues && (
											<p className="text-xs text-orange-600 mt-1">
												{disc.issues.join(", ")}
											</p>
										)}
									</div>
									<div className="flex items-center gap-2">
										{disc.amount && (
											<span className="text-sm font-medium text-gray-700">
												{formatCurrency(disc.amount)}
											</span>
										)}
										<button className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors">
											Resolve
										</button>
									</div>
								</div>
							</li>
						))}
					</ul>
				</div>
			)}

			{/* Last Reconciled */}
			<div className="text-center text-xs text-gray-500">
				Last reconciled: {status?.last_reconciled ? new Date(status.last_reconciled).toLocaleString() : "Never"}
			</div>
		</div>
	);
}
