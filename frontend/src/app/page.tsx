"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Shield, RefreshCw, Menu, X, Wifi, WifiOff } from "lucide-react";
import { TransactionSidebar } from "@/components/dashboard/TransactionSidebar";
import { DebateView } from "@/components/investigation/DebateView";
import { VerdictCard } from "@/components/investigation/VerdictCard";
import { GraphExplorer } from "@/components/graph/GraphExplorer";
import { StatsDashboard } from "@/components/dashboard/StatsDashboard";
import { MonitoringWidgets } from "@/components/dashboard/MonitoringWidgets";
import { ModuleTabs, ModuleType } from "@/components/navigation/ModuleNavigation";
import { AlertDashboard } from "@/components/monitoring/AlertDashboard";
import { ComplianceDashboard } from "@/components/compliance/ComplianceDashboard";
import { AffiliateNetwork } from "@/components/partner/AffiliateNetwork";
import { ApprovalQueue } from "@/components/approval/ApprovalQueue";
import { ReconciliationDashboard } from "@/components/reconciliation/ReconciliationDashboard";
import { useInvestigation } from "@/hooks/useInvestigation";
import { useDashboardSync } from "@/hooks/useWebSocket";
import { toast } from "sonner";
import { getTransaction, api, getAnnexIV, getAnnexIvPdfUrl, AnnexIVResponse } from "@/lib/api";
import { Transaction as ApiTransaction, RiskLevel } from "@/lib/types";
import { useRouter, usePathname } from "next/navigation";

// Extend Transaction for UI display needs (add derived statuses)
type UIStatus = "pending" | "investigating" | "completed" | "approved" | "blocked" | "escalated";

interface Transaction {
  uetr: string;
  debtor: string;
  creditor: string;
  amount: string | number;
  currency: string;
  riskLevel: RiskLevel | null;
  status: UIStatus;
}

// Helper to map API transaction to UI transaction
function toUITransaction(tx: ApiTransaction): Transaction {
  let uiStatus: UIStatus = "pending";
  if (tx.status === "completed") uiStatus = "completed";
  else if (tx.status === "investigating") uiStatus = "investigating";
  else if (tx.status === "overridden_approve") uiStatus = "approved";
  else if (tx.status === "overridden_block") uiStatus = "blocked";
  else if (tx.status === "overridden_escalate") uiStatus = "escalated";
  else if (tx.status === "error") uiStatus = "pending";

  return {
    uetr: tx.uetr,
    debtor: tx.debtor,
    creditor: tx.creditor,
    amount: tx.amount,
    currency: tx.currency,
    riskLevel: tx.riskLevel,
    status: uiStatus,
  };
}

export default function Home() {
  const router = useRouter();
  const pathname = usePathname();
  // useSearchParams can cause prerendering errors in Next's app router during
  // static export. Use a client-only window-based URLSearchParams synced via
  // effect to avoid needing suspense boundaries.
  const [searchParams, setSearchParams] = useState<URLSearchParams>(
    typeof window !== "undefined" ? new URLSearchParams(window.location.search) : new URLSearchParams("")
  );

  useEffect(() => {
    const update = () => setSearchParams(new URLSearchParams(window.location.search));
    // initialize and listen for history navigation
    update();
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedUetr, setSelectedUetr] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"debate" | "graph">("debate");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeModule, setActiveModule] = useState<ModuleType>("overview");
  const [annexIVData, setAnnexIVData] = useState<AnnexIVResponse | null>(null);
  const [annexIVOpen, setAnnexIVOpen] = useState(false);

  const {
    isStreaming,
    messages,
    verdict,
    graphData,
    sarReport,
    investigate,
    loadResult,
    submitOverride,
    submitSAR,
    reset,
  } = useInvestigation();

  // Define fetchTransactionsList first (before it's used in hooks)
  const fetchTransactionsList = useCallback(async () => {
    try {
      const { transactions } = await api.listTransactions({ limit: 100 });
      const uiTransactions = transactions.map(toUITransaction);
      setTransactions(uiTransactions);
      return uiTransactions;
    } catch (err) {
      console.error("Failed to fetch transactions:", err);
      toast.error("Failed to load transactions");
      return [];
    }
  }, []);

  // Use ref to avoid stale closure in callbacks
  const fetchTransactionsRef = useRef(fetchTransactionsList);
  useEffect(() => {
    fetchTransactionsRef.current = fetchTransactionsList;
  }, [fetchTransactionsList]);

  // WebSocket for real-time sync (uses ref to get latest function)
  const { isConnected } = useDashboardSync(() => {
    fetchTransactionsRef.current();
  });

  // Define handleSelectTransaction before it's used in useEffect
  const handleSelectTransaction = useCallback(async (uetr: string, updateUrl: boolean = true) => {
    setSelectedUetr(uetr);
    setActiveModule("investigation");

    if (updateUrl) {
      const params = new URLSearchParams(searchParams);
      params.set("uetr", uetr);
      router.push(`${pathname}?${params.toString()}`);
    }

    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }

    reset();

    try {
      const detail = await getTransaction(uetr);

      setTransactions((prev) =>
        prev.map((t) => {
          if (t.uetr !== uetr) return t;

          let status: Transaction["status"] = "pending";
          if (detail.status === "pending" || detail.status === "investigating" || detail.status === "completed") {
            status = detail.status;
          } else if (detail.status === "overridden_approve") {
            status = "approved";
          } else if (detail.status === "overridden_block") {
            status = "blocked";
          } else if (detail.status === "overridden_escalate") {
            status = "escalated";
          }

          return {
            ...t,
            status: status,
            riskLevel: detail.risk_level || t.riskLevel
          };
        })
      );

      if (detail.status === "completed" || detail.status.startsWith("overridden")) {
        loadResult(detail);
      }
    } catch (err) {
      toast.error("Failed to load transaction details");
      console.error(err);
    }
  }, [pathname, router, reset, loadResult]);

  // URL helper for params
  const updateUrlParam = (key: string, value: string | null) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const handleModuleChange = (mod: ModuleType) => {
    setActiveModule(mod);
    const params = new URLSearchParams(searchParams);
    params.set("module", mod);
    
    if (mod === "investigation" && !selectedUetr) {
      // Stay on investigation
    } else if (mod !== "investigation") {
      setSelectedUetr(null);
      reset();
      params.delete("uetr"); // Clear transaction from URL when switching modules
      params.delete("tab");
    }
    
    router.push(`${pathname}?${params.toString()}`);
  };

  const handleTabChange = (tab: "debate" | "graph") => {
    setActiveTab(tab);
    const params = new URLSearchParams(searchParams);
    params.set("tab", tab);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  // Initial load
  useEffect(() => {
    fetchTransactionsList();
  }, [fetchTransactionsList]);

  // Sync state with URL param (now handleSelectTransaction is defined)
  useEffect(() => {
    const uetrParam = searchParams.get("uetr");
    const tabParam = searchParams.get("tab");
    const moduleParam = searchParams.get("module") as ModuleType | null;

    if (uetrParam && uetrParam !== selectedUetr) {
      handleSelectTransaction(uetrParam, false);
    } else if (!uetrParam && selectedUetr) {
      setSelectedUetr(null);
      reset();
    }

    if (tabParam === "graph" || tabParam === "debate") {
      setActiveTab(tabParam);
    }

    if (moduleParam && ["overview", "investigation", "monitoring", "compliance", "partners", "approvals", "reconciliation"].includes(moduleParam)) {
      setActiveModule(moduleParam);
    }
  }, [searchParams, selectedUetr, handleSelectTransaction, reset]);

  const handleGenerateData = async () => {
    try {
      const result = await api.generateSyntheticData();
      toast.success(`Generated ${result.generated} new transactions`);
      await fetchTransactionsList();
    } catch (err) {
      console.error("Failed to generate data:", err);
      toast.error("Failed to generate synthetic data");
    }
  };

  const handleClearData = async () => {
    try {
      await api.clearData();
      toast.success("All data cleared");
      setTransactions([]);
      setSelectedUetr(null);
    } catch (err) {
      console.error("Failed to clear data:", err);
      toast.error("Failed to clear data");
    }
  };

  const handleAction = async (action: "approve" | "block" | "escalate") => {
    if (!selectedUetr) return;

    try {
      const promise = submitOverride(selectedUetr, action);

      toast.promise(promise, {
        loading: 'Processing decision...',
        success: () => `Transaction ${action}d successfully`,
        error: 'Failed to submit decision',
      });

      await promise;

      setTransactions((prev) =>
        prev.map((tx) => {
          if (tx.uetr !== selectedUetr) return tx;
          return {
            ...tx,
            riskLevel: action === "approve" ? "low" : action === "block" ? "critical" : "high",
            status: action === "approve" ? "approved" : action === "block" ? "blocked" : "escalated"
          };
        })
      );
    } catch (err) {
      console.error("Override failed:", err);
    }
  };

  const handleViewReport = async () => {
    if (!selectedUetr) {
      toast.error("No transaction selected");
      return;
    }

    updateUrlParam("report", "annex-iv");

    try {
      toast.loading("Loading Annex IV documentation...");
      const data = await getAnnexIV(selectedUetr);
      setAnnexIVData(data);
      setAnnexIVOpen(true);
      toast.dismiss();
    } catch (err) {
      toast.dismiss();
      toast.error("Failed to load Annex IV documentation");
      console.error(err);
      updateUrlParam("report", null);
    }
  };

  const handleDownloadAnnexIVPdf = () => {
    if (selectedUetr) {
      window.open(getAnnexIvPdfUrl(selectedUetr), '_blank');
    }
  };

  const selectedTransaction = transactions.find((tx) => tx.uetr === selectedUetr);

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-950 overflow-hidden relative">
      {/* Sidebar */}
      <TransactionSidebar
        transactions={transactions}
        selectedUetr={selectedUetr}
        onSelect={handleSelectTransaction}
        isOpen={sidebarOpen}
        onGenerate={handleGenerateData}
        onClear={handleClearData}
      />

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-10 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden transition-all duration-200">
        {/* Header */}
        <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-4 flex-shrink-0">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
              >
                {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>

              <Shield className="w-8 h-8 text-blue-600 flex-shrink-0" />
              <div className="min-w-0 hidden md:block">
                <h1 className="text-xl font-bold text-gray-900 dark:text-white truncate">
                  Financial Intelligence Swarm
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  AI-Powered FraudOps Platform
                </p>
              </div>
            </div>

            {/* Module Tabs */}
            <div className="flex-1 max-w-3xl mx-4 hidden lg:block">
              <ModuleTabs
                activeModule={activeModule}
                onModuleChange={handleModuleChange}
              />
            </div>

            {/* Right side controls */}
            <div className="flex items-center gap-2">
              {isConnected ? (
                <div className="flex items-center gap-1 text-green-600 text-sm" title="Real-time sync active">
                  <Wifi className="w-4 h-4" />
                  <span className="hidden md:inline">Live</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-gray-400 text-sm" title="Offline - using cached data">
                  <WifiOff className="w-4 h-4" />
                  <span className="hidden md:inline">Offline</span>
                </div>
              )}
              <button
                onClick={fetchTransactionsList}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                title="Refresh Data"
              >
                <RefreshCw className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Mobile Module Tabs */}
          <div className="mt-3 lg:hidden overflow-x-auto">
            <ModuleTabs
              activeModule={activeModule}
              onModuleChange={handleModuleChange}
            />
          </div>
        </header>

        {/* Content Area - switches based on active module */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Overview Module */}
          {activeModule === "overview" && (
            <div className="flex-1 overflow-auto p-6 space-y-6">
              <MonitoringWidgets />
              <StatsDashboard transactions={transactions} />
            </div>
          )}

          {/* Investigation Module */}
          {activeModule === "investigation" && (
            <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
              {selectedTransaction ? (
                <>
                  {/* Investigation Tabs */}
                  <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                    <div className="flex gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
                      <button
                        onClick={() => handleTabChange("debate")}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === "debate"
                          ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                          : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                          }`}
                      >
                        Debate Trail
                      </button>
                      <button
                        onClick={() => handleTabChange("graph")}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === "graph"
                          ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                          : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                          }`}
                      >
                        Entity Graph
                      </button>
                      <div className="flex-1" />
                      <button
                        onClick={() => selectedUetr && investigate(selectedUetr)}
                        disabled={isStreaming}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                      >
                        {isStreaming ? "Investigating..." : "Start Investigation"}
                      </button>
                    </div>
                    <div className="flex-1 overflow-hidden">
                      {activeTab === "debate" ? (
                        messages.length === 0 && !isStreaming && selectedTransaction?.status === 'pending' ? (
                          <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-gray-50 dark:bg-gray-900/50">
                            <Shield className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
                            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                              Ready to Investigate
                            </h3>
                            <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md">
                              Start the AI swarm to analyze this transaction.
                            </p>
                            <button
                              onClick={() => {
                                setTransactions(prev => prev.map(t =>
                                  t.uetr === selectedTransaction.uetr ? { ...t, status: 'investigating' } : t
                                ));
                                investigate(selectedTransaction.uetr);
                              }}
                              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
                            >
                              Start Investigation
                            </button>
                          </div>
                        ) : (
                          <DebateView messages={messages} isStreaming={isStreaming} />
                        )
                      ) : (
                        <GraphExplorer
                          nodes={graphData.nodes}
                          links={graphData.links}
                          highlightPath={graphData.highlightPath}
                        />
                      )}
                    </div>
                  </div>
                    {/* Verdict Panel */}
                    {verdict && (
                      <div className="w-full lg:w-96 flex-shrink-0 border-l border-gray-200 dark:border-gray-700 overflow-auto">
                        <VerdictCard
                          verdict={verdict}
                          status={selectedTransaction?.status || "pending"}
                          uetr={selectedUetr || undefined}
                          onAction={(action) => handleAction(action)}
                          onViewReport={handleViewReport}
                          onGenerateSAR={async () => {
                            if (selectedUetr) {
                              try {
                                const result = await api.generateSAR(selectedUetr);
                                toast.success("SAR report generated successfully");
                              } catch (err) {
                                toast.error("Failed to generate SAR report");
                              }
                            }
                          }}
                          sarReport={sarReport}
                        />
                      </div>
                    )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full p-8 text-gray-500">
                  <Shield className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
                  <h3 className="text-xl font-medium mb-2">Select a Transaction</h3>
                  <p className="text-sm">Choose a transaction from the sidebar to investigate</p>
                </div>
              )}
            </div>
          )}

          {/* Monitoring Module */}
          {activeModule === "monitoring" && (
            <div className="flex-1 overflow-auto p-6">
              <AlertDashboard />
            </div>
          )}

          {/* Compliance Module */}
          {activeModule === "compliance" && (
            <div className="flex-1 overflow-auto p-6">
              <ComplianceDashboard />
            </div>
          )}

          {/* Partners Module */}
          {activeModule === "partners" && (
            <div className="flex-1 overflow-auto p-6">
              <AffiliateNetwork />
            </div>
          )}

          {/* Approvals Module */}
          {activeModule === "approvals" && (
            <div className="flex-1 overflow-auto p-6">
              <ApprovalQueue />
            </div>
          )}

          {/* Reconciliation Module */}
          {activeModule === "reconciliation" && (
            <div className="flex-1 overflow-auto p-6">
              <ReconciliationDashboard />
            </div>
          )}
        </div>
      </main>

      {/* Annex IV Modal */}
      {annexIVOpen && annexIVData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center sticky top-0 bg-white dark:bg-gray-800">
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  EU AI Act - Annex IV
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Technical Documentation for High-Risk AI System
                </p>
              </div>
              <button
                onClick={() => {
                  setAnnexIVOpen(false);
                  updateUrlParam("report", null);
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  1. General Description
                </h3>
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <strong>Name:</strong> {annexIVData.system_description.name}
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                    <strong>Type:</strong> {annexIVData.system_description.type}
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                    <strong>Version:</strong> {annexIVData.system_description.version}
                  </p>
                </div>
              </section>

              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  2. Intended Purpose
                </h3>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {annexIVData.intended_purpose}
                </p>
              </section>

              <div className="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleDownloadAnnexIVPdf}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  Download PDF
                </button>
                <button
                  onClick={() => {
                    setAnnexIVOpen(false);
                    updateUrlParam("report", null);
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
