/**
 * Shared TypeScript interfaces for the Financial Intelligence Swarm frontend.
 * These types mirror the backend Pydantic models and LangGraph state schemas.
 */

// ============================================================================
// Risk & Verdict Types
// ============================================================================

export type RiskLevel = "low" | "medium" | "high" | "critical" | "unknown";

export type VerdictDecision = "APPROVE" | "BLOCK" | "ESCALATE" | "REVIEW";

export type Speaker = "prosecutor" | "skeptic" | "judge";

export type OverrideDecision = "approve" | "block" | "escalate";

export type InvestigationPhase = "investigation" | "rebuttal" | "verdict";

export type TransactionStatus =
  | "pending"
  | "investigating"
  | "completed"
  | "error"
  | "overridden_approve"
  | "overridden_block"
  | "overridden_escalate";

export type MessageType = "pacs.008" | "pain.001" | "camt.053";

// ============================================================================
// Debate & Investigation Types
// ============================================================================

export interface DebateMessage {
  speaker: Speaker;
  content: string;
  evidenceIds: string[];
  timestamp: string;
}

export interface EuAiActCompliance {
  article13Satisfied: boolean;
  transparencyStatement: string;
  humanOversightRequired: boolean;
}

export interface Verdict {
  verdict: VerdictDecision;
  riskLevel: RiskLevel;
  confidenceScore: number;
  reasoning: string;
  recommendedActions: string[];
  euAiActCompliance: EuAiActCompliance;
}

export interface HumanOverride {
  decision: OverrideDecision;
  reason: string;
  timestamp: string;
}

// ============================================================================
// Graph Visualization Types
// ============================================================================

export type GraphNodeType = "entity" | "account" | "transaction" | "sanctioned";

export interface GraphNode {
  id: string;
  name?: string;
  label?: string;
  type?: GraphNodeType;
  risk?: "high" | "normal";
  riskScore?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  highlightPath?: string[];
}

export interface HiddenLink {
  path_nodes: string[];
  risk_entity?: string;
  relationship_type?: string;
  confidence?: number;
}

// ============================================================================
// Transaction Types
// ============================================================================

export interface Amount {
  value: number;
  currency: string;
}

export interface Party {
  name: string;
  account?: string;
  bic?: string;
  address?: string;
}

export interface ParsedIsoMessage {
  parsed_successfully: boolean;
  message_type?: string;
  message_id?: string;
  uetr?: string;
  creation_date?: string;
  debtor?: Party;
  creditor?: Party;
  amount?: Amount;
  remittance_info?: string;
  error?: string;
}

export interface Transaction {
  uetr: string;
  debtor: string;
  creditor: string;
  amount: number;
  currency: string;
  status: TransactionStatus;
  riskLevel: RiskLevel | null;
  createdAt: string;
}

export interface TransactionDetail {
  parsed_message: ParsedIsoMessage;
  status: TransactionStatus;
  created_at: string;
  risk_level: RiskLevel | null;
  verdict: Verdict | null;
  human_override?: HumanOverride;
  investigation_result?: InvestigationResult;
}

// ============================================================================
// Investigation State Types
// ============================================================================

export interface InvestigationResult {
  uetr: string;
  iso_message: ParsedIsoMessage;
  graph_risk_score: number;
  semantic_risk_score: number;
  historical_drift: number;
  prosecutor_findings: string[];
  skeptic_findings: string[];
  tool_calls: ToolCall[];
  messages: DebateMessage[];
  graph_context: string;
  hidden_links: HiddenLink[];
  doc_context: string;
  alibi_evidence: string[];
  drift_context: string;
  behavioral_baseline: Record<string, unknown>;
  verdict: Verdict | null;
  risk_level: RiskLevel;
  confidence_score: number;
  human_override: boolean | null;
  current_phase: InvestigationPhase;
  round_count: number;
  needs_more_evidence: boolean;
}

export interface ToolCall {
  agent: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  result: string;
  timestamp: string;
}

export interface InvestigationState {
  isStreaming: boolean;
  messages: DebateMessage[];
  verdict: Verdict | null;
  graphData: GraphData;
  prosecutorFindings: string[];
  skepticFindings: string[];
  alibiEvidence: string[];
  graphRiskScore: number;
  semanticRiskScore: number;
  roundCount: number;
  error: string | null;
}

// ============================================================================
// API Request Types
// ============================================================================

export interface IngestRequest {
  xml_content: string;
  message_type?: MessageType;
}

export interface InvestigateRequest {
  uetr: string;
  restart?: boolean;
}

export interface OverrideRequest {
  action: OverrideDecision;
  reason?: string;
}

export interface ListTransactionsParams {
  status?: TransactionStatus;
  limit?: number;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiError {
  detail: string;
  status?: number;
  code?: string;
}

export interface IngestResponse {
  success: boolean;
  uetr: string;
  message_type: MessageType;
  parsed: ParsedIsoMessage;
}

export interface ListTransactionsResponse {
  transactions: Transaction[];
  total: number;
}

export interface OverrideResponse {
  success: boolean;
  uetr: string;
  override: HumanOverride;
}

export interface SARReport {
  report_id: string;
  generated_at: string;
  status: string;
  transaction_details: {
    uetr: string;
    date: string;
    amount: string;
    originator: {
      name: string;
      account: string;
      address: string;
    };
    beneficiary: {
      name: string;
      account: string;
      address: string;
    };
    purpose: string;
  };
  risk_assessment: {
    risk_level: RiskLevel;
    verdict: VerdictDecision;
    confidence_score: number;
  };
  investigation_summary: {
    prosecutor_findings: string[];
    skeptic_findings: string[];
    hidden_links_detected: boolean;
    graph_risk_score: number;
    semantic_risk_score: number;
  };
  reasoning: string;
  recommended_actions: string[];
  human_override?: HumanOverride;
  compliance: {
    eu_ai_act: {
      article_13_satisfied: boolean;
      transparency_statement: string;
      human_oversight_required: boolean;
    };
  };
}

export interface HealthResponse {
  message: string;
  status: string;
}

// ============================================================================
// Stream Data Types (Vercel AI SDK Data Stream Protocol)
// ============================================================================

export type StreamDataType =
  | "status"
  | "prosecutor_findings"
  | "skeptic_findings"
  | "verdict"
  | "data-graph"
  | "data-gauge"
  | "complete"
  | "error"
  | "message";

export interface BaseStreamData {
  type: StreamDataType;
}

export interface StatusStreamData extends BaseStreamData {
  type: "status";
  status: TransactionStatus;
  uetr: string;
}

export interface ProsecutorFindingsStreamData extends BaseStreamData {
  type: "prosecutor_findings";
  findings: string[];
  hidden_links: HiddenLink[];
  graph_risk_score: number;
}

export interface SkepticFindingsStreamData extends BaseStreamData {
  type: "skeptic_findings";
  findings: string[];
  alibi_evidence: string[];
  semantic_risk_score: number;
}

export interface VerdictStreamData extends BaseStreamData {
  type: "verdict";
  verdict: Record<string, unknown>;
  risk_level: RiskLevel;
  confidence_score: number;
  round: number;
}

export interface GraphStreamData extends BaseStreamData {
  type: "data-graph";
  data: {
    nodes: GraphNode[];
    links: GraphLink[];
  };
}

export interface GaugeStreamData extends BaseStreamData {
  type: "data-gauge";
  data: {
    risk_level: RiskLevel;
    confidence: number;
    verdict: VerdictDecision;
  };
}

export interface CompleteStreamData extends BaseStreamData {
  type: "complete";
  uetr: string;
  risk_level: RiskLevel;
  verdict: Record<string, unknown>;
}

export interface ErrorStreamData extends BaseStreamData {
  type: "error";
  message: string;
}

export interface MessageStreamData extends BaseStreamData {
  type: "message";
  speaker: Speaker;
  content: string;
  evidence_ids?: string[];
  timestamp?: string;
}

export type StreamData =
  | StatusStreamData
  | ProsecutorFindingsStreamData
  | SkepticFindingsStreamData
  | VerdictStreamData
  | GraphStreamData
  | GaugeStreamData
  | CompleteStreamData
  | ErrorStreamData
  | MessageStreamData;
