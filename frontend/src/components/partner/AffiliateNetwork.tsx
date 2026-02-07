"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
	Network,
	AlertTriangle,
	Users,
	DollarSign,
	RefreshCw,
	Eye,
	Ban,
	CheckCircle
} from "lucide-react";
import { motion } from "framer-motion";

interface Partner {
	id: string;
	name: string;
	type: string;
	risk_score: number;
	status: string;
	total_volume: number;
	total_commission: number;
	referrals: number;
	conversion_rate: number;
	connections: string[];
	flags: string[];
}

interface NetworkNode {
	id: string;
	name: string;
	type: string;
	risk_score: number;
}

interface NetworkEdge {
	from: string;
	to: string;
}

interface AffiliateNetworkProps {
	onPartnerSelect?: (partnerId: string) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const statusColors = {
	active: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700" },
	under_review: { bg: "bg-yellow-100 dark:bg-yellow-900/30", text: "text-yellow-700" },
	suspended: { bg: "bg-red-100 dark:bg-red-900/30", text: "text-red-700" },
};

const riskColors = (score: number) => {
	if (score >= 70) return "text-red-600";
	if (score >= 40) return "text-yellow-600";
	return "text-green-600";
};

export function AffiliateNetwork({ onPartnerSelect }: AffiliateNetworkProps) {
	const [partners, setPartners] = useState<Record<string, Partner>>({});
	const [selectedPartner, setSelectedPartner] = useState<string | null>(null);
	const [networkData, setNetworkData] = useState<{ nodes: NetworkNode[]; edges: NetworkEdge[] } | null>(null);
	const [loading, setLoading] = useState(true);
	const [analyzing, setAnalyzing] = useState(false);
	const canvasRef = useRef<HTMLCanvasElement>(null);

	const fetchPartners = useCallback(async () => {
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/partners`);
			if (!response.ok) throw new Error("Failed to fetch partners");
			const data = await response.json();
			setPartners(data.partners || {});
		} catch (err) {
			console.error("Failed to fetch partners:", err);
		} finally {
			setLoading(false);
		}
	}, []);

	const fetchNetwork = useCallback(async (partnerId: string) => {
		try {
			const response = await fetch(`${API_BASE_URL}/partners/${partnerId}/network?depth=2`);
			if (!response.ok) throw new Error("Failed to fetch network");
			const data = await response.json();
			setNetworkData({ nodes: data.nodes || [], edges: data.edges || [] });
		} catch (err) {
			console.error("Failed to fetch network:", err);
		}
	}, []);

	const runFraudAnalysis = async () => {
		setAnalyzing(true);
		try {
			const response = await fetch(`${API_BASE_URL}/partners/analyze`, {
				method: "POST",
			});
			if (!response.ok) throw new Error("Analysis failed");
			await fetchPartners();
		} catch (err) {
			console.error("Analysis failed:", err);
		} finally {
			setAnalyzing(false);
		}
	};

	useEffect(() => {
		fetchPartners();
	}, [fetchPartners]);

	useEffect(() => {
		if (selectedPartner) {
			fetchNetwork(selectedPartner);
		}
	}, [selectedPartner, fetchNetwork]);

	// Simple network visualization
	useEffect(() => {
		if (!canvasRef.current || !networkData || networkData.nodes.length === 0) return;

		const canvas = canvasRef.current;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const width = canvas.width;
		const height = canvas.height;

		ctx.clearRect(0, 0, width, height);

		// Position nodes in a circle
		const nodePositions: Record<string, { x: number; y: number }> = {};
		const centerX = width / 2;
		const centerY = height / 2;
		const radius = Math.min(width, height) / 3;

		networkData.nodes.forEach((node, i) => {
			const angle = (2 * Math.PI * i) / networkData.nodes.length - Math.PI / 2;
			nodePositions[node.id] = {
				x: centerX + radius * Math.cos(angle),
				y: centerY + radius * Math.sin(angle),
			};
		});

		// Draw edges
		ctx.strokeStyle = "#94a3b8";
		ctx.lineWidth = 2;
		networkData.edges.forEach((edge) => {
			const from = nodePositions[edge.from];
			const to = nodePositions[edge.to];
			if (from && to) {
				ctx.beginPath();
				ctx.moveTo(from.x, from.y);
				ctx.lineTo(to.x, to.y);
				ctx.stroke();
			}
		});

		// Draw nodes
		networkData.nodes.forEach((node) => {
			const pos = nodePositions[node.id];
			const isSelected = node.id === selectedPartner;
			const nodeRadius = isSelected ? 28 : 22;

			// Node circle
			ctx.beginPath();
			ctx.arc(pos.x, pos.y, nodeRadius, 0, 2 * Math.PI);
			ctx.fillStyle = node.risk_score >= 70 ? "#ef4444" : node.risk_score >= 40 ? "#f59e0b" : "#22c55e";
			ctx.fill();

			if (isSelected) {
				ctx.strokeStyle = "#3b82f6";
				ctx.lineWidth = 4;
				ctx.stroke();
			}

			// Node label
			ctx.fillStyle = "#1f2937";
			ctx.font = "11px sans-serif";
			ctx.textAlign = "center";
			ctx.fillText(node.name.substring(0, 12), pos.x, pos.y + nodeRadius + 16);
		});
	}, [networkData, selectedPartner]);

	const handlePartnerClick = (partnerId: string) => {
		setSelectedPartner(partnerId);
		onPartnerSelect?.(partnerId);
	};

	const getStatusStyle = (status: string) => {
		return statusColors[status as keyof typeof statusColors] || statusColors.active;
	};

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-3">
					<div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
						<Network className="w-6 h-6 text-purple-600" />
					</div>
					<div>
						<h2 className="text-xl font-bold text-gray-900 dark:text-white">
							Affiliate Network
						</h2>
						<p className="text-sm text-gray-500">Partner fraud detection & monitoring</p>
					</div>
				</div>
				<button
					onClick={runFraudAnalysis}
					disabled={analyzing}
					className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-medium rounded-lg flex items-center gap-2 transition-colors"
				>
					<RefreshCw className={`w-4 h-4 ${analyzing ? "animate-spin" : ""}`} />
					Analyze Network
				</button>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* Partner List */}
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
						<Users className="w-5 h-5 text-blue-600" />
						<h3 className="font-semibold text-gray-900 dark:text-white">Partners</h3>
						<span className="ml-auto text-sm text-gray-500">
							{Object.keys(partners).length} total
						</span>
					</div>
					<ul className="divide-y divide-gray-100 dark:divide-gray-800 max-h-96 overflow-y-auto">
						{loading ? (
							<li className="p-8 text-center text-gray-500">
								<RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
								Loading partners...
							</li>
						) : (
							Object.entries(partners).map(([id, partner]) => {
								const statusStyle = getStatusStyle(partner.status);
								return (
									<motion.li
										key={id}
										whileHover={{ backgroundColor: "rgba(0,0,0,0.02)" }}
										className={`p-4 cursor-pointer ${selectedPartner === id ? "bg-blue-50 dark:bg-blue-900/20" : ""}`}
										onClick={() => handlePartnerClick(id)}
									>
										<div className="flex items-center justify-between mb-2">
											<span className="font-medium text-gray-900 dark:text-white">
												{partner.name}
											</span>
											<span className={`text-lg font-bold ${riskColors(partner.risk_score)}`}>
												{partner.risk_score}
											</span>
										</div>
										<div className="flex items-center gap-2 text-xs">
											<span className={`px-2 py-0.5 rounded-full ${statusStyle.bg} ${statusStyle.text}`}>
												{partner.status}
											</span>
											<span className="text-gray-500">{partner.type}</span>
										</div>
										{partner.flags.length > 0 && (
											<div className="flex flex-wrap gap-1 mt-2">
												{partner.flags.map((flag, i) => (
													<span key={i} className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs rounded">
														{flag.replace(/_/g, " ")}
													</span>
												))}
											</div>
										)}
									</motion.li>
								);
							})
						)}
					</ul>
				</div>

				{/* Network Visualization */}
				<div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
					<div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
						<Network className="w-5 h-5 text-purple-600" />
						<h3 className="font-semibold text-gray-900 dark:text-white">
							Connection Graph
						</h3>
					</div>
					<div className="p-4">
						{selectedPartner ? (
							<canvas
								ref={canvasRef}
								width={400}
								height={300}
								className="w-full h-[300px] bg-gray-50 dark:bg-gray-800 rounded-lg"
							/>
						) : (
							<div className="h-[300px] flex items-center justify-center text-gray-500">
								<p>Select a partner to view connections</p>
							</div>
						)}
					</div>

					{/* Legend */}
					<div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
						<div className="flex items-center gap-4 text-xs">
							<span className="flex items-center gap-1">
								<span className="w-3 h-3 rounded-full bg-green-500" />
								Low Risk
							</span>
							<span className="flex items-center gap-1">
								<span className="w-3 h-3 rounded-full bg-yellow-500" />
								Medium Risk
							</span>
							<span className="flex items-center gap-1">
								<span className="w-3 h-3 rounded-full bg-red-500" />
								High Risk
							</span>
						</div>
					</div>
				</div>
			</div>

			{/* Partner Details */}
			{selectedPartner && partners[selectedPartner] && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
				>
					<div className="flex items-center justify-between mb-4">
						<h3 className="text-lg font-semibold text-gray-900 dark:text-white">
							{partners[selectedPartner].name}
						</h3>
						<div className="flex items-center gap-2">
							<button className="px-3 py-1.5 text-sm bg-blue-100 text-blue-700 rounded-lg flex items-center gap-1">
								<Eye className="w-4 h-4" />
								Review
							</button>
							<button className="px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded-lg flex items-center gap-1">
								<Ban className="w-4 h-4" />
								Suspend
							</button>
						</div>
					</div>

					<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
						<div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
							<div className="text-2xl font-bold text-gray-900 dark:text-white">
								${(partners[selectedPartner].total_volume / 1000000).toFixed(2)}M
							</div>
							<div className="text-xs text-gray-500">Total Volume</div>
						</div>
						<div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
							<div className="text-2xl font-bold text-gray-900 dark:text-white">
								${(partners[selectedPartner].total_commission / 1000).toFixed(0)}K
							</div>
							<div className="text-xs text-gray-500">Commission</div>
						</div>
						<div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
							<div className="text-2xl font-bold text-gray-900 dark:text-white">
								{partners[selectedPartner].referrals}
							</div>
							<div className="text-xs text-gray-500">Referrals</div>
						</div>
						<div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
							<div className="text-2xl font-bold text-gray-900 dark:text-white">
								{(partners[selectedPartner].conversion_rate * 100).toFixed(0)}%
							</div>
							<div className="text-xs text-gray-500">Conversion</div>
						</div>
					</div>
				</motion.div>
			)}
		</div>
	);
}
