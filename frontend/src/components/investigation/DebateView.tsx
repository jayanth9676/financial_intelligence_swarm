"use client";

import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
	Bot,
	User,
	Gavel,
	Search,
	ShieldAlert,
	Terminal,
	ChevronDown,
	ChevronRight,
	CheckCircle2,
	AlertCircle,
	Loader2
} from "lucide-react";
import { InvestigationMessage } from "@/hooks/useInvestigation";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";

interface DebateViewProps {
	messages: InvestigationMessage[];
	isStreaming: boolean;
}

const agentConfig = {
	prosecutor: {
		icon: ShieldAlert,
		name: "Prosecutor Agent",
		color: "text-red-600 dark:text-red-400",
		bgColor: "bg-red-50 dark:bg-red-900/20",
		borderColor: "border-red-200 dark:border-red-800",
	},
	skeptic: {
		icon: Search,
		name: "Skeptic Agent",
		color: "text-blue-600 dark:text-blue-400",
		bgColor: "bg-blue-50 dark:bg-blue-900/20",
		borderColor: "border-blue-200 dark:border-blue-800",
	},
	judge: {
		icon: Gavel,
		name: "Judge Agent",
		color: "text-purple-600 dark:text-purple-400",
		bgColor: "bg-purple-50 dark:bg-purple-900/20",
		borderColor: "border-purple-200 dark:border-purple-800",
	},
};

function ToolCall({ message }: { message: InvestigationMessage }) {
	const [isExpanded, setIsExpanded] = React.useState(false);

	if (message.type !== "tool_call") return null;

	const config = agentConfig[message.agent] || agentConfig.prosecutor;
	const isSuccess = !message.result?.toLowerCase().includes("error");

	return (
		<div className="mb-4 ml-8">
			<div
				className={`
          rounded-md border text-sm overflow-hidden
          ${isSuccess ? "border-gray-200 dark:border-gray-700" : "border-red-200 dark:border-red-800"}
          bg-white dark:bg-gray-900
        `}
			>
				<button
					onClick={() => setIsExpanded(!isExpanded)}
					className="w-full flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
				>
					<Terminal className="w-4 h-4 text-gray-500" />
					<span className="font-mono text-gray-700 dark:text-gray-300">
						{message.toolName}
					</span>
					<span className="text-xs text-gray-400 ml-auto">
						{new Date(message.timestamp).toLocaleTimeString()}
					</span>
					{isExpanded ? (
						<ChevronDown className="w-4 h-4 text-gray-400" />
					) : (
						<ChevronRight className="w-4 h-4 text-gray-400" />
					)}
				</button>

				<AnimatePresence>
					{isExpanded && (
						<motion.div
							initial={{ height: 0 }}
							animate={{ height: "auto" }}
							exit={{ height: 0 }}
							className="overflow-hidden"
						>
							<div className="p-3 bg-gray-50 dark:bg-gray-950 border-t border-gray-100 dark:border-gray-800 font-mono text-xs space-y-2">
								<div>
									<div className="text-gray-500 mb-1">Arguments:</div>
									<pre className="overflow-x-auto p-2 bg-gray-100 dark:bg-gray-900 rounded text-gray-700 dark:text-gray-300">
										{JSON.stringify(message.args, null, 2)}
									</pre>
								</div>
								<div>
									<div className="text-gray-500 mb-1">Result:</div>
									<pre className={`overflow-x-auto p-2 bg-gray-100 dark:bg-gray-900 rounded ${isSuccess ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
										{typeof message.result === 'string' ? message.result : JSON.stringify(message.result, null, 2)}
									</pre>
								</div>
							</div>
						</motion.div>
					)}
				</AnimatePresence>
			</div>
		</div>
	);
}

function MessageBubble({ message }: { message: InvestigationMessage }) {
	if (message.type === "tool_call") {
		return <ToolCall message={message} />;
	}

	const config = agentConfig[message.speaker] || agentConfig.prosecutor;
	const Icon = config.icon;

	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			className={`flex gap-4 mb-6 ${message.speaker === "judge" ? "justify-center" : ""}`}
		>
			<div className={`flex items-start gap-4 ${message.speaker === "judge" ? "justify-center w-full" : ""}`}>

				{/* Avatar - Hide for Judge in this layout as we center it */}
				{message.speaker !== "judge" && (
					<div className={`
					flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
					${config.bgColor} border ${config.borderColor} shadow-sm mt-1
				`}>
						<Icon className={`w-5 h-5 ${config.color}`} />
					</div>
				)}

				<div className={`
				flex-1 
				${message.speaker === "judge" ? "max-w-[800px] w-full mx-auto" : "max-w-[85%]"}
			`}>
					{message.speaker === "judge" ? (
						// Judge Special Layout
						<div className="flex flex-col items-center mb-6 mt-4">
							<div className="w-12 h-12 rounded-full bg-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/30 mb-3 animate-bounce-short">
								<Gavel className="w-6 h-6 text-white" />
							</div>
							<div className="bg-white dark:bg-gray-900 border-2 border-purple-500/30 dark:border-purple-500/50 rounded-2xl p-6 shadow-xl shadow-purple-900/5 w-full relative overflow-hidden">
								<div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-fuchsia-500 to-purple-500 opacity-50"></div>

								<div className="flex items-center justify-between mb-4 border-b border-purple-100 dark:border-purple-900/30 pb-3">
									<div className="flex items-center gap-2">
										<span className="text-lg font-bold text-gray-900 dark:text-white">
											Judge's Verdict
										</span>
										<span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded-full border border-purple-200 dark:border-purple-800">
											Final Decision
										</span>
									</div>
									<span className="text-xs text-gray-400 font-mono">
										{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
									</span>
								</div>

								<div className="text-gray-800 dark:text-gray-100 leading-relaxed prose dark:prose-invert max-w-none">
									<MarkdownRenderer content={message.content} />
								</div>
							</div>
						</div>
					) : (
						// Standard Layout for Prosecutor/Skeptic
						<>
							<div className="flex items-center gap-2 mb-1.5 ml-1">
								<span className={`text-sm font-bold tracking-tight ${config.color}`}>
									{config.name}
								</span>
								<span className="text-[11px] text-gray-400 font-mono opacity-80">
									{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
								</span>
							</div>

							<div className={`
							bg-white dark:bg-gray-900 
							border border-gray-200 dark:border-gray-700 
							rounded-2xl p-5 shadow-sm 
						`}>
								<div className="text-gray-800 dark:text-gray-200 leading-relaxed prose dark:prose-invert max-w-none">
									<MarkdownRenderer content={message.content} />
								</div>

								{message.evidenceIds && message.evidenceIds.length > 0 && (
									<div className="mt-4 flex flex-wrap gap-2 pt-3 border-t border-gray-100 dark:border-gray-800">
										{message.evidenceIds.map((id) => (
											<span
												key={id}
												className="text-[10px] px-2 py-1 bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded border border-gray-100 dark:border-gray-700 font-mono flex items-center gap-1 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
											>
												<Search className="w-3 h-3 opacity-70" />
												{id}
											</span>
										))}
									</div>
								)}
							</div>
						</>
					)}
				</div>
			</div>
		</motion.div>
	);
}

export function DebateView({ messages, isStreaming }: DebateViewProps) {
	const bottomRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (bottomRef.current) {
			bottomRef.current.scrollIntoView({ behavior: "smooth" });
		}
	}, [messages, isStreaming]);

	return (
		<div className="h-full overflow-y-auto p-6 bg-gray-50/50 dark:bg-gray-950/50">
			<div className="max-w-4xl mx-auto">
				{messages.map((msg, index) => (
					<MessageBubble key={`${msg.timestamp}-${index}`} message={msg} />
				))}

				{isStreaming && (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						className="flex gap-4 mb-6"
					>
						<div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-gray-100 dark:bg-gray-800">
							<Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
						</div>
						<div className="flex items-center">
							<span className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">
								Thinking...
							</span>
						</div>
					</motion.div>
				)}

				<div ref={bottomRef} />
			</div>
		</div>
	);
}
