"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
	Activity,
	Shield,
	Users,
	CheckSquare,
	FileSearch,
	Search,
	ChevronRight,
	LayoutDashboard,
} from "lucide-react";

export type ModuleType =
	| "overview"
	| "investigation"
	| "monitoring"
	| "compliance"
	| "partners"
	| "approvals"
	| "reconciliation";

interface Module {
	id: ModuleType;
	name: string;
	description: string;
	icon: React.ComponentType<{ className?: string }>;
	category: "overview" | "compliance" | "anti-fraud" | "finance";
	color: string;
}

const modules: Module[] = [
	{
		id: "overview",
		name: "Dashboard",
		description: "System overview & stats",
		icon: LayoutDashboard,
		category: "overview",
		color: "blue",
	},
	{
		id: "investigation",
		name: "Fraud Investigation",
		description: "AI-powered client fraud detection",
		icon: Search,
		category: "anti-fraud",
		color: "red",
	},
	{
		id: "monitoring",
		name: "Transaction Monitoring",
		description: "Real-time pattern detection",
		icon: Activity,
		category: "compliance",
		color: "yellow",
	},
	{
		id: "compliance",
		name: "Compliance Manager",
		description: "Regulatory calendar & status",
		icon: Shield,
		category: "compliance",
		color: "green",
	},
	{
		id: "partners",
		name: "Partner Fraud",
		description: "Affiliate network analysis",
		icon: Users,
		category: "anti-fraud",
		color: "purple",
	},
	{
		id: "approvals",
		name: "Payments Approval",
		description: "Multi-level authorization",
		icon: CheckSquare,
		category: "finance",
		color: "orange",
	},
	{
		id: "reconciliation",
		name: "Reconciliation",
		description: "Statement matching & variance",
		icon: FileSearch,
		category: "finance",
		color: "cyan",
	},
];

const categoryLabels = {
	overview: "Overview",
	compliance: "Compliance & Risk",
	"anti-fraud": "Anti-Fraud",
	finance: "Finance Operations",
};

const colorClasses: Record<string, { bg: string; text: string; border: string }> = {
	blue: {
		bg: "bg-blue-100 dark:bg-blue-900/30",
		text: "text-blue-600 dark:text-blue-400",
		border: "border-blue-500",
	},
	red: {
		bg: "bg-red-100 dark:bg-red-900/30",
		text: "text-red-600 dark:text-red-400",
		border: "border-red-500",
	},
	yellow: {
		bg: "bg-yellow-100 dark:bg-yellow-900/30",
		text: "text-yellow-600 dark:text-yellow-400",
		border: "border-yellow-500",
	},
	green: {
		bg: "bg-green-100 dark:bg-green-900/30",
		text: "text-green-600 dark:text-green-400",
		border: "border-green-500",
	},
	purple: {
		bg: "bg-purple-100 dark:bg-purple-900/30",
		text: "text-purple-600 dark:text-purple-400",
		border: "border-purple-500",
	},
	orange: {
		bg: "bg-orange-100 dark:bg-orange-900/30",
		text: "text-orange-600 dark:text-orange-400",
		border: "border-orange-500",
	},
	cyan: {
		bg: "bg-cyan-100 dark:bg-cyan-900/30",
		text: "text-cyan-600 dark:text-cyan-400",
		border: "border-cyan-500",
	},
};

interface ModuleNavigationProps {
	activeModule: ModuleType;
	onModuleChange: (module: ModuleType) => void;
	compact?: boolean;
}

export function ModuleNavigation({
	activeModule,
	onModuleChange,
	compact = false,
}: ModuleNavigationProps) {
	const [hoveredModule, setHoveredModule] = useState<ModuleType | null>(null);

	if (compact) {
		return (
			<div className="flex items-center gap-1 overflow-x-auto pb-2 scrollbar-hide">
				{modules.map((module) => {
					const Icon = module.icon;
					const colors = colorClasses[module.color];
					const isActive = activeModule === module.id;

					return (
						<button
							key={module.id}
							onClick={() => onModuleChange(module.id)}
							className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${isActive
									? `${colors.bg} ${colors.text} border-2 ${colors.border}`
									: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-2 border-transparent hover:bg-gray-200 dark:hover:bg-gray-700"
								}`}
						>
							<Icon className="w-4 h-4" />
							<span>{module.name}</span>
						</button>
					);
				})}
			</div>
		);
	}

	// Group by category
	const grouped = modules.reduce((acc, mod) => {
		if (!acc[mod.category]) acc[mod.category] = [];
		acc[mod.category].push(mod);
		return acc;
	}, {} as Record<string, Module[]>);

	return (
		<div className="space-y-6">
			{Object.entries(grouped).map(([category, mods]) => (
				<div key={category}>
					<h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
						{categoryLabels[category as keyof typeof categoryLabels]}
					</h3>
					<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
						{mods.map((module) => {
							const Icon = module.icon;
							const colors = colorClasses[module.color];
							const isActive = activeModule === module.id;
							const isHovered = hoveredModule === module.id;

							return (
								<motion.button
									key={module.id}
									onClick={() => onModuleChange(module.id)}
									onMouseEnter={() => setHoveredModule(module.id)}
									onMouseLeave={() => setHoveredModule(null)}
									className={`relative flex items-start gap-3 p-4 rounded-xl text-left transition-all ${isActive
											? `${colors.bg} border-2 ${colors.border} shadow-lg`
											: "bg-white dark:bg-gray-800 border-2 border-transparent hover:border-gray-200 dark:hover:border-gray-600 shadow-sm hover:shadow-md"
										}`}
									whileHover={{ scale: 1.02 }}
									whileTap={{ scale: 0.98 }}
								>
									<div className={`p-2 rounded-lg ${colors.bg}`}>
										<Icon className={`w-5 h-5 ${colors.text}`} />
									</div>
									<div className="flex-1 min-w-0">
										<div className="flex items-center gap-2">
											<span className={`font-semibold ${isActive ? colors.text : "text-gray-900 dark:text-white"}`}>
												{module.name}
											</span>
											<AnimatePresence>
												{(isActive || isHovered) && (
													<motion.span
														initial={{ opacity: 0, x: -5 }}
														animate={{ opacity: 1, x: 0 }}
														exit={{ opacity: 0, x: -5 }}
													>
														<ChevronRight className={`w-4 h-4 ${colors.text}`} />
													</motion.span>
												)}
											</AnimatePresence>
										</div>
										<p className="text-sm text-gray-500 dark:text-gray-400 truncate">
											{module.description}
										</p>
									</div>
								</motion.button>
							);
						})}
					</div>
				</div>
			))}
		</div>
	);
}

// Tab bar version for header
export function ModuleTabs({
	activeModule,
	onModuleChange,
}: ModuleNavigationProps) {
	return (
		<div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg overflow-x-auto">
			{modules.map((module) => {
				const Icon = module.icon;
				const isActive = activeModule === module.id;
				const colors = colorClasses[module.color];

				return (
					<button
						key={module.id}
						onClick={() => onModuleChange(module.id)}
						className={`relative flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all whitespace-nowrap ${isActive
								? "bg-white dark:bg-gray-900 shadow-sm text-gray-900 dark:text-white"
								: "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
							}`}
					>
						<Icon className={`w-4 h-4 ${isActive ? colors.text : ""}`} />
						<span className="hidden md:inline">{module.name}</span>
					</button>
				);
			})}
		</div>
	);
}
