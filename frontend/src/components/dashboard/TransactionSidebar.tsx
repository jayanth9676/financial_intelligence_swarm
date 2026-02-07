"use client";

import { AlertTriangle, CheckCircle, Clock, FileText, Plus, Trash2, HelpCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Transaction {
  uetr: string;
  debtor: string;
  creditor: string;
  amount: string | number;
  currency: string;
  riskLevel: "low" | "medium" | "high" | "critical" | "unknown" | null;
  status: "pending" | "investigating" | "completed" | "approved" | "blocked" | "escalated";
}

interface TransactionSidebarProps {
  transactions: Transaction[];
  selectedUetr: string | null;
  onSelect: (uetr: string) => void;
  isOpen: boolean;
  onGenerate?: () => void;
  onClear?: () => void;
}

const riskColors = {
  low: "bg-green-500",
  medium: "bg-yellow-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
  unknown: "bg-gray-400",
};

const riskIcons = {
  low: CheckCircle,
  medium: Clock,
  high: AlertTriangle,
  critical: AlertTriangle,
  unknown: HelpCircle,
};

export function TransactionSidebar({
  transactions,
  selectedUetr,
  onSelect,
  isOpen,
  onGenerate,
  onClear,
}: TransactionSidebarProps) {
  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-20 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700
        transition-all duration-300 ease-in-out
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
        lg:relative lg:translate-x-0
        ${isOpen ? "lg:w-80" : "lg:w-0 lg:border-r-0 lg:overflow-hidden"}
        w-80
      `}
    >
      <div className="h-full flex flex-col w-80">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Transactions
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {transactions.length} pending investigation
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          <AnimatePresence>
            <ul className="divide-y divide-gray-100 dark:divide-gray-800">
              {transactions.map((tx) => {
                const level = tx.riskLevel || "unknown";
                const RiskIcon = riskIcons[level] || HelpCircle;
                const isSelected = tx.uetr === selectedUetr;

                return (
                  <motion.li
                    key={tx.uetr}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className={`
                      cursor-pointer transition-colors
                      ${isSelected
                        ? "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500"
                        : "hover:bg-gray-50 dark:hover:bg-gray-800 border-l-4 border-transparent"
                      }
                    `}
                    onClick={() => onSelect(tx.uetr)}
                  >
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-gray-500 dark:text-gray-400 truncate max-w-[180px]">
                          {tx.uetr}
                        </span>
                        <span
                          className={`
                            w-2 h-2 rounded-full
                            ${riskColors[level] || riskColors.unknown}
                            ${level === "critical" ? "animate-pulse" : ""}
                          `}
                        />
                      </div>

                      <div className="flex items-center gap-2 mb-1">
                        <RiskIcon
                          className={`w-4 h-4 ${level === "critical"
                            ? "text-red-500"
                            : level === "high"
                              ? "text-orange-500"
                              : level === "medium"
                                ? "text-yellow-500"
                                : level === "low"
                                  ? "text-green-500"
                                  : "text-gray-400"
                            }`}
                        />
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {tx.amount} {tx.currency}
                        </span>
                      </div>

                      <div className="text-xs text-gray-600 dark:text-gray-300">
                        <div className="truncate">{tx.debtor}</div>
                        <div className="text-gray-400 dark:text-gray-500">→</div>
                        <div className="truncate">{tx.creditor}</div>
                      </div>

                      {tx.status === "investigating" && (
                        <div className="mt-2 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                            className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full"
                          />
                          Investigating...
                        </div>
                      )}
                    </div>
                  </motion.li>
                );
              })}
            </ul>
          </AnimatePresence>
        </div>

        {(onGenerate || onClear) && (
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex-shrink-0 flex gap-2">
            {onGenerate && (
              <button
                onClick={onGenerate}
                className="flex-1 py-2 px-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-center gap-2 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Generate
              </button>
            )}
            {onClear && (
              <button
                onClick={onClear}
                className="p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center justify-center transition-colors shadow-sm"
                title="Clear All Data"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
