"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Shield, AlertTriangle, CheckCircle, XCircle, ArrowUpRight, FileText, RotateCcw, Download, FileWarning } from "lucide-react";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";

interface Verdict {
  verdict: "APPROVE" | "BLOCK" | "ESCALATE" | "REVIEW";
  riskLevel: "low" | "medium" | "high" | "critical";
  confidenceScore: number;
  reasoning: string;
  recommendedActions: string[];
  euAiActCompliance: {
    article13Satisfied: boolean;
    transparencyStatement: string;
    humanOversightRequired: boolean;
  };
}

interface VerdictCardProps {
  verdict: Verdict | null;
  status: string;
  uetr?: string;
  onAction: (action: "approve" | "block" | "escalate") => void;
  onViewReport: () => void;
  onGenerateSAR?: () => Promise<void>;
  sarReport?: {
    report_id: string;
    status: string;
  } | null;
}

/**
 * Parse reasoning text and extract clean content from JSON/markdown code blocks
 */
function parseReasoning(reasoning: string): string {
  if (!reasoning) return "";

  let cleaned = reasoning;

  // Try to find any code block that looks like JSON
  const codeBlockMatch = cleaned.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
  if (codeBlockMatch) {
    try {
      const parsed = JSON.parse(codeBlockMatch[1]);
      if (parsed.reasoning) {
        return parsed.reasoning;
      }
    } catch {
      // If parsing fails, remove the block
      cleaned = cleaned.replace(codeBlockMatch[0], "");
    }
  }

  // Remove remaining code blocks
  cleaned = cleaned.replace(/```[\s\S]*?```/g, "");

  // If the whole string looks like JSON
  if (cleaned.trim().startsWith("{")) {
    try {
      const parsed = JSON.parse(cleaned);
      if (parsed.reasoning) {
        return parsed.reasoning;
      }
    } catch {
      // Not valid JSON
    }
  }

  return cleaned.trim();
}

/**
 * Expandable reasoning section with Show more/less toggle
 */
function ReasoningSection({ reasoning }: { reasoning: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const parsedReasoning = parseReasoning(reasoning);
  const MAX_LENGTH = 300;
  const shouldTruncate = parsedReasoning.length > MAX_LENGTH;

  const displayText = !isExpanded && shouldTruncate
    ? parsedReasoning.slice(0, MAX_LENGTH) + "..."
    : parsedReasoning;

  return (
    <div className="mb-4">
      <div className="text-sm text-gray-700 dark:text-gray-300 break-words">
        {shouldTruncate && !isExpanded ? (
          <p className="whitespace-pre-wrap">{displayText}</p>
        ) : (
          <MarkdownRenderer content={parsedReasoning} />
        )}
      </div>
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-2 font-medium"
        >
          {isExpanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

const verdictConfig = {
  APPROVE: {
    color: "green",
    icon: CheckCircle,
    bgColor: "bg-green-50 dark:bg-green-900/20",
    borderColor: "border-green-500",
    textColor: "text-green-700 dark:text-green-400",
  },
  BLOCK: {
    color: "red",
    icon: XCircle,
    bgColor: "bg-red-50 dark:bg-red-900/20",
    borderColor: "border-red-500",
    textColor: "text-red-700 dark:text-red-400",
  },
  ESCALATE: {
    color: "orange",
    icon: ArrowUpRight,
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    borderColor: "border-orange-500",
    textColor: "text-orange-700 dark:text-orange-400",
  },
  REVIEW: {
    color: "yellow",
    icon: AlertTriangle,
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    borderColor: "border-yellow-500",
    textColor: "text-yellow-700 dark:text-yellow-400",
  },
};

export function VerdictCard({ verdict, status, uetr, onAction, onViewReport, onGenerateSAR, sarReport }: VerdictCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isGeneratingSAR, setIsGeneratingSAR] = useState(false);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const handleGenerateSAR = async () => {
    if (onGenerateSAR) {
      setIsGeneratingSAR(true);
      try {
        await onGenerateSAR();
      } finally {
        setIsGeneratingSAR(false);
      }
    }
  };

  const handleDownloadSARPdf = () => {
    if (uetr) {
      window.open(`${API_BASE_URL}/generate-sar-pdf/${encodeURIComponent(uetr)}`, '_blank');
    }
  };

  if (!verdict) {
    return (
      <div className="p-8 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 flex flex-col items-center justify-center text-center h-full min-h-[300px]">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4 animate-pulse">
          <Shield className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Awaiting Verdict</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
          The Judge is currently analyzing evidence from the Prosecutor and Skeptic agents.
        </p>
      </div>
    );
  }

  const config = verdictConfig[verdict.verdict] || verdictConfig["REVIEW"];
  const Icon = config.icon;

  const isFinalState = ["approved", "blocked", "escalated"].includes(status);

  const getStatusConfig = (s: string) => {
    switch (s) {
      case "approved": return verdictConfig.APPROVE;
      case "blocked": return verdictConfig.BLOCK;
      case "escalated": return verdictConfig.ESCALATE;
      default: return verdictConfig.REVIEW;
    }
  };

  const finalStatusConfig = isFinalState ? getStatusConfig(status) : null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`
        rounded-xl border shadow-sm overflow-hidden bg-white dark:bg-gray-900
        ${isFinalState && finalStatusConfig ? finalStatusConfig.borderColor : config.borderColor}
      `}
    >
      {/* Header Banner */}
      <div className={`
        p-4 border-b flex items-center justify-between
        ${isFinalState && finalStatusConfig ? finalStatusConfig.bgColor : config.bgColor}
        ${isFinalState && finalStatusConfig ? finalStatusConfig.borderColor : config.borderColor}
      `}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
            <Icon className={`w-6 h-6 ${isFinalState && finalStatusConfig ? finalStatusConfig.textColor : config.textColor}`} />
          </div>
          <div>
            <h3 className={`text-lg font-bold ${isFinalState && finalStatusConfig ? finalStatusConfig.textColor : config.textColor}`}>
              {isFinalState ? `Transaction ${status.charAt(0).toUpperCase() + status.slice(1)}` : (verdict.verdict || "REVIEW")}
            </h3>
            <p className="text-xs opacity-80 font-medium tracking-wide uppercase">
              {isFinalState ? "Final Decision Executed" : "Recommended Verdict"}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-end">
          <span className="text-xs uppercase font-bold text-gray-500 dark:text-gray-400 mb-1">Risk Level</span>
          <span className={`text-sm font-bold px-2 py-0.5 rounded ${config.bgColor} ${config.textColor} border ${config.borderColor} uppercase`}>
            {verdict.riskLevel || "UNKNOWN"}
          </span>
        </div>
      </div>

      <div className="p-6">
        {/* Confidence Score - Compact Banner */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12">
              <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="10"
                  className="text-gray-200 dark:text-gray-700"
                />
                <motion.circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="10"
                  strokeLinecap="round"
                  className={`
                    ${(verdict.confidenceScore || 0) >= 0.8 ? "text-green-500" : ""}
                    ${(verdict.confidenceScore || 0) >= 0.6 && (verdict.confidenceScore || 0) < 0.8 ? "text-yellow-500" : ""}
                    ${(verdict.confidenceScore || 0) < 0.6 ? "text-red-500" : ""}
                  `}
                  initial={{ strokeDashoffset: 2 * Math.PI * 38 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 38 * (1 - (verdict.confidenceScore || 0)) }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  style={{ strokeDasharray: 2 * Math.PI * 38 }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-sm font-bold text-gray-900 dark:text-white">
                  {((verdict.confidenceScore || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900 dark:text-white">AI Confidence</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {(verdict.confidenceScore || 0) >= 0.8 ? "High confidence" :
                  (verdict.confidenceScore || 0) >= 0.6 ? "Moderate confidence" : "Low confidence"}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Risk Level</div>
            <span className={`text-sm font-bold ${config.textColor}`}>
              {verdict.riskLevel?.toUpperCase() || "UNKNOWN"}
            </span>
          </div>
        </div>

        {/* Key Reasoning - Full Width */}
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-500" />
            Key Reasoning
          </h4>
          <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg border border-gray-100 dark:border-gray-700">
            <ReasoningSection reasoning={verdict.reasoning || ""} />
          </div>
        </div>

        {/* Recommended Actions */}
        {verdict.recommendedActions && verdict.recommendedActions.length > 0 && (
          <div className="mb-6">
            <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
              Recommended Actions
            </h4>
            <ul className="space-y-2">
              {verdict.recommendedActions.map((action, i) => (
                <li key={i} className="flex gap-3 text-sm text-gray-700 dark:text-gray-300 group">
                  <div className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-400 group-hover:bg-blue-600 transition-colors flex-shrink-0" />
                  <span className="leading-relaxed">{action}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Human Oversight Warning */}
        {verdict.euAiActCompliance && verdict.euAiActCompliance.humanOversightRequired && (
          <div className="p-4 bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-200 dark:border-amber-800 mb-6 flex gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-amber-800 dark:text-amber-400 mb-1">Human Oversight Mandated</h4>
              <p className="text-xs text-amber-700 dark:text-amber-500 leading-relaxed">
                {verdict.euAiActCompliance.transparencyStatement || "High-risk AI system requirement: This decision must be reviewed by a qualified human operator."}
              </p>
            </div>
          </div>
        )}

        {/* Compliance Report Button */}
        <div className="mb-4 pt-4 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={onViewReport}
            className="w-full py-2.5 px-4 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-slate-700 dark:text-slate-300 hover:text-blue-700 dark:hover:text-blue-300 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200 group"
          >
            <FileText className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
            View EU AI Act Compliance Report (Annex IV)
            <ArrowUpRight className="w-3.5 h-3.5 opacity-50 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>

        {/* SAR Report Section */}
        <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-2 mb-3">
            <FileWarning className="w-5 h-5 text-amber-600 dark:text-amber-500" />
            <h4 className="text-sm font-bold text-amber-800 dark:text-amber-400">Suspicious Activity Report (SAR)</h4>
          </div>
          
          {sarReport ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-amber-700 dark:text-amber-500">Report ID:</span>
                <span className="font-mono text-amber-800 dark:text-amber-400">{sarReport.report_id}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-amber-700 dark:text-amber-500">Status:</span>
                <span className={`font-medium ${sarReport.status === 'FILED' ? 'text-green-600' : 'text-yellow-600'}`}>
                  {sarReport.status}
                </span>
              </div>
              <button
                onClick={handleDownloadSARPdf}
                className="w-full py-2 px-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                Download SAR PDF
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-amber-700 dark:text-amber-500">
                {verdict?.verdict === "BLOCK" || status === "blocked" 
                  ? "Transaction blocked. Generate SAR for regulatory filing."
                  : "Generate a SAR if this transaction is suspicious."}
              </p>
              <button
                onClick={handleGenerateSAR}
                disabled={isGeneratingSAR || !uetr}
                className="w-full py-2 px-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
              >
                {isGeneratingSAR ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <FileWarning className="w-4 h-4" />
                    Generate SAR Report
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Action Buttons or Status Banner */}
        {isFinalState && !isEditing ? (
          <div className="text-center">
            <button
              onClick={() => setIsEditing(true)}
              className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex items-center justify-center gap-1 mx-auto transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Re-evaluate Decision
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            <button
              onClick={() => {
                setIsEditing(false);
                onAction("approve");
              }}
              className="px-3 py-2.5 bg-gradient-to-b from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-white rounded-lg text-sm font-medium shadow-md shadow-green-500/20 hover:shadow-lg hover:shadow-green-500/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-sm"
            >
              Approve
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                onAction("escalate");
              }}
              className="px-3 py-2.5 bg-gradient-to-b from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500 text-white rounded-lg text-sm font-medium shadow-md shadow-orange-500/20 hover:shadow-lg hover:shadow-orange-500/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-sm"
            >
              Escalate
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                onAction("block");
              }}
              className="px-3 py-2.5 bg-gradient-to-b from-red-500 to-red-600 hover:from-red-400 hover:to-red-500 text-white rounded-lg text-sm font-medium shadow-md shadow-red-500/20 hover:shadow-lg hover:shadow-red-500/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-sm"
            >
              Block
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
