"use client";

import { useState, useCallback } from "react";
import { TransactionDetail } from "@/lib/types";

export interface DebateMessage {
  type: "message";
  speaker: "prosecutor" | "skeptic" | "judge";
  content: string;
  evidenceIds: string[];
  timestamp: string;
}

export interface ToolCallMessage {
  type: "tool_call";
  agent: "prosecutor" | "skeptic";
  toolName: string;
  args: Record<string, unknown>;
  result: string;
  timestamp: string;
}

export type InvestigationMessage = DebateMessage | ToolCallMessage;

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

interface GraphData {
  nodes: Array<{
    id: string;
    name: string;
    type: "entity" | "account" | "transaction" | "sanctioned";
    riskScore?: number;
  }>;
  links: Array<{
    source: string;
    target: string;
    type: string;
  }>;
  highlightPath: string[];
}

interface SARReport {
  report_id: string;
  generated_at: string;
  status: string;
  transaction_details: Record<string, unknown>;
  risk_assessment: Record<string, unknown>;
  investigation_summary: Record<string, unknown>;
  reasoning: string;
  recommended_actions: string[];
}

interface InvestigationState {
  isStreaming: boolean;
  messages: InvestigationMessage[];
  verdict: Verdict | null;
  graphData: GraphData;
  error: string | null;
  sarReport: SARReport | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useInvestigation() {
  const [state, setState] = useState<InvestigationState>({
    isStreaming: false,
    messages: [],
    verdict: null,
    graphData: { nodes: [], links: [], highlightPath: [] },
    error: null,
    sarReport: null,
  });

  const investigate = useCallback(async (uetr: string, restart: boolean = false) => {
    setState((prev) => ({
      ...prev,
      isStreaming: true,
      messages: [],
      verdict: null,
      error: null,
      sarReport: null,
      graphData: { nodes: [], links: [], highlightPath: [] } // Reset graph on restart
    }));

    try {
      const response = await fetch(`${API_BASE_URL}/investigate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ uetr, restart }),
      });

      if (!response.ok) {
        throw new Error(`Investigation failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;

          // Parse Vercel AI SDK Data Stream Protocol
          // Format: TYPE:DATA
          const colonIndex = line.indexOf(":");
          if (colonIndex === -1) continue;

          const type = line.substring(0, colonIndex);
          const data = line.substring(colonIndex + 1);

          try {
            switch (type) {
              case "0": // Text
                // Ignore text chunks for now
                break;

              case "d": // Data
                const parsed = JSON.parse(data);
                handleDataPart(parsed, setState);
                break;

              case "b": // Tool call
                const toolCall = JSON.parse(data);
                console.log("Tool call:", toolCall);
                break;

              case "e": // Error
                const error = JSON.parse(data);
                setState((prev) => ({ ...prev, error: error.message }));
                break;

              default:
                console.log("Unknown stream type:", type, data);
            }
          } catch (parseError) {
            console.error("Failed to parse stream data:", parseError);
          }
        }
      }
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Unknown error",
      }));
    } finally {
      setState((prev) => ({ ...prev, isStreaming: false }));
    }
  }, []);

  const loadResult = useCallback((detail: TransactionDetail) => {
    if (!detail.investigation_result) return;

    // Cast to any to handle potential mismatched types between frontend interface and backend dict
    const result = detail.investigation_result as any;

    // Get the last message from each speaker (for multi-round debates, show only final messages)
    const lastMessageBySpeaker: Record<string, any> = {};
    for (const msg of (result.messages || [])) {
      lastMessageBySpeaker[msg.speaker] = msg;
    }
    
    // Create final messages in debate order: prosecutor -> skeptic -> judge
    const debateOrder = ["prosecutor", "skeptic", "judge"];
    const finalMessages: InvestigationMessage[] = debateOrder
      .filter(speaker => lastMessageBySpeaker[speaker])
      .map(speaker => {
        const msg = lastMessageBySpeaker[speaker];
        return {
          type: "message" as const,
          speaker: msg.speaker,
          content: msg.content,
          evidenceIds: msg.evidenceIds || msg.evidence_ids || [],
          timestamp: msg.timestamp,
        };
      });

    const toolCalls: InvestigationMessage[] = (result.tool_calls || []).map((tc: any) => ({
      type: "tool_call" as const,
      agent: tc.agent,
      toolName: tc.tool_name,
      args: tc.tool_args || tc.args || {},
      result: tc.result,
      timestamp: tc.timestamp,
    }));

    // Sort tool calls by timestamp, then append final messages in debate order
    toolCalls.sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    
    // Tool calls first (chronological), then final debate messages (in debate order)
    const allMessages = [...toolCalls, ...finalMessages];

    // Construct full Verdict object from potentially scattered backend fields
    let constructedVerdict: Verdict | null = null;

    // Backend stores risk/confidence at top level of state, but verdict rationale in 'verdict' dict
    if (result.verdict) {
      constructedVerdict = {
        verdict: (result.verdict.verdict as "APPROVE" | "BLOCK" | "ESCALATE" | "REVIEW") || "REVIEW",
        riskLevel: (result.risk_level as "low" | "medium" | "high" | "critical") || "medium",
        confidenceScore: result.confidence_score || 0.0,
        reasoning: result.verdict.reasoning || "",
        recommendedActions: result.verdict.recommended_actions || [],
        euAiActCompliance: {
          article13Satisfied: result.verdict.eu_ai_act_compliance?.article_13_satisfied ?? true,
          transparencyStatement:
            result.verdict.eu_ai_act_compliance?.transparency_statement ||
            "Generated by FIS Swarm AI",
          humanOversightRequired:
            result.verdict.eu_ai_act_compliance?.human_oversight_required ?? true,
        },
      };
    } else if (detail.verdict) {
      // Fallback to transaction-level verdict if detailed result verdict is missing
      constructedVerdict = detail.verdict as unknown as Verdict;
    }

    // Extract graph data from hidden_links if available
    let graphData: GraphData = { nodes: [], links: [], highlightPath: [] };

    // Helper to generate basic graph from transaction details (fallback)
    const generateFallbackGraph = () => {
      const debtor = detail.parsed_message?.debtor?.name || "Unknown Debtor";
      const creditor = detail.parsed_message?.creditor?.name || "Unknown Creditor";
      const uetr = detail.parsed_message?.uetr || "Transaction";
      // Handle potentially missing amount object
      const amountObj = detail.parsed_message?.amount as any;
      const amountVal = amountObj?.value;
      const amountCur = amountObj?.currency;
      const formattedAmount = amountVal ? `${amountVal} ${amountCur || 'EUR'}` : "?";

      return {
        nodes: [
          { id: debtor, name: debtor, type: "entity" as const, riskScore: 0.1 },
          { id: uetr, name: formattedAmount, type: "transaction" as const, riskScore: 0.5 },
          { id: creditor, name: creditor, type: "entity" as const, riskScore: 0.1 }
        ],
        links: [
          { source: debtor, target: uetr, type: "SENT_FUNDS" },
          { source: uetr, target: creditor, type: "RECEIVED_FUNDS" }
        ],
        highlightPath: [debtor, uetr, creditor]
      };
    };

    if (result.hidden_links && result.hidden_links.length > 0) {
      // Reconstruct graph from hidden links (similar to backend _extract_graph_nodes logic)
      const nodesMap = new Map<string, any>();
      const links: any[] = [];
      const highlightPathSet = new Set<string>();

      result.hidden_links.forEach((link: any) => {
        const pathNodes = link.path_nodes || link.path || [];
        const riskEntity = link.risk_entity || link.end || "";

        // Extract nodes
        pathNodes.forEach((nodeName: string) => {
          highlightPathSet.add(nodeName);
          if (!nodesMap.has(nodeName)) {
            const isSanctioned = nodeName === riskEntity || nodeName.toLowerCase().includes("sanctioned");
            nodesMap.set(nodeName, {
              id: nodeName,
              name: nodeName,
              type: isSanctioned ? "sanctioned" : "entity",
              riskScore: isSanctioned ? 1.0 : 0.5
            });
          }
        });

        // Extract links
        for (let i = 0; i < pathNodes.length - 1; i++) {
          links.push({
            source: pathNodes[i],
            target: pathNodes[i + 1],
            type: "RELATED_TO" // Generic type as specific types might be complex to reconstruct without full edge data
          });
        }
      });

      graphData = {
        nodes: Array.from(nodesMap.values()),
        links: links,
        highlightPath: Array.from(highlightPathSet)
      };
    } else {
      // If no hidden links found (but investigation is done), show the basic transaction graph
      graphData = generateFallbackGraph();
    }

    setState({
      isStreaming: false,
      messages: allMessages,
      verdict: constructedVerdict,
      graphData: graphData,
      error: null,
      sarReport: null,
    });
  }, []);

  const submitOverride = useCallback(
    async (uetr: string, action: "approve" | "block" | "escalate") => {
      try {
        const response = await fetch(`${API_BASE_URL}/override/${encodeURIComponent(uetr)}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ action }),
        });

        if (!response.ok) {
          throw new Error(`Override failed: ${response.statusText}`);
        }

        const result = await response.json();

        // If action is block, automatically generate SAR
        if (action === "block") {
          try {
            const sarResponse = await fetch(`${API_BASE_URL}/generate-sar/${encodeURIComponent(uetr)}`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
            });

            if (sarResponse.ok) {
              const sarData = await sarResponse.json();
              setState((prev) => ({
                ...prev,
                sarReport: sarData,
              }));
            }
          } catch (sarError) {
            console.error("SAR generation failed:", sarError);
          }
        }

        return result;
      } catch (error) {
        setState((prev) => ({
          ...prev,
          error: error instanceof Error ? error.message : "Unknown error",
        }));
        throw error;
      }
    },
    []
  );

  const generateSAR = useCallback(async (uetr: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/generate-sar/${encodeURIComponent(uetr)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`SAR generation failed: ${response.statusText}`);
      }

      const sarData = await response.json();
      setState((prev) => ({
        ...prev,
        sarReport: sarData,
      }));

      return sarData;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Unknown error",
      }));
      throw error;
    }
  }, []);

  const submitSAR = useCallback(async (uetr: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/submit-sar/${encodeURIComponent(uetr)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`SAR submission failed: ${response.statusText}`);
      }

      const result = await response.json();
      setState((prev) => ({
        ...prev,
        sarReport: result.sar_report,
      }));

      return result;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Unknown error",
      }));
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({
      isStreaming: false,
      messages: [],
      verdict: null,
      graphData: { nodes: [], links: [], highlightPath: [] },
      error: null,
      sarReport: null,
    });
  }, []);

  return {
    ...state,
    investigate,
    loadResult,
    submitOverride,
    generateSAR,
    submitSAR,
    reset,
  };
}

interface StreamDataPart {
  type: string;
  speaker?: string;
  content?: string;
  evidence_ids?: string[];
  timestamp?: string;
  agent?: string;
  tool_name?: string;
  args?: Record<string, unknown>;
  result?: string;
  verdict?: string | Record<string, unknown>;  // Can be string or full verdict object
  risk_level?: string;
  confidence_score?: number;
  reasoning?: string;
  recommended_actions?: string[];
  eu_ai_act_compliance?: {
    article_13_satisfied?: boolean;
    transparency_statement?: string;
    human_oversight_required?: boolean;
  };
  nodes?: Array<{
    id: string;
    name: string;
    type: "entity" | "account" | "transaction" | "sanctioned";
    riskScore?: number;
  }>;
  links?: Array<{
    source: string;
    target: string;
    type: string;
  }>;
  highlight_path?: string[];
}

function handleDataPart(
  data: StreamDataPart,
  setState: React.Dispatch<React.SetStateAction<InvestigationState>>
) {
  if (data.type === "message") {
    setState((prev) => {
      // Deduplicate: check if last message is identical
      const lastMsg = prev.messages[prev.messages.length - 1];
      // Type guard: only compare if lastMsg is a message type (not tool_call)
      if (lastMsg && lastMsg.type === "message" &&
        lastMsg.speaker === data.speaker &&
        lastMsg.content === (data.content || "") &&
        // Check if the EXACT message exists in recent history
        prev.messages.slice(-3).some(m => m.type === "message" && m.speaker === data.speaker && m.content === data.content)
      ) {
        return prev;
      }

      return {
        ...prev,
        messages: [
          ...prev.messages,
          {
            type: "message", // Explicitly set as message
            speaker: data.speaker as "prosecutor" | "skeptic" | "judge",
            content: data.content || "",
            evidenceIds: data.evidence_ids || [],
            timestamp: data.timestamp || new Date().toISOString(),
          },
        ],
      };
    });
  } else if (data.type === "tool_call") {
    setState((prev) => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          type: "tool_call",
          agent: data.agent as "prosecutor" | "skeptic",
          toolName: data.tool_name || "unknown",
          args: data.args || {},
          result: data.result || "",
          timestamp: data.timestamp || new Date().toISOString(),
        },
      ],
    }));
  } else if (data.type === "verdict") {
    // Parse the verdict - it could be a string or already have the fields
    let verdictDecision = data.verdict;
    let reasoning = data.reasoning || "";
    let recommendedActions = data.recommended_actions || [];
    let euCompliance = data.eu_ai_act_compliance;

    // If verdict is an object (the full verdict dict), extract fields
    if (typeof data.verdict === "object" && data.verdict !== null) {
      const v = data.verdict as Record<string, unknown>;
      verdictDecision = (v.verdict as string) || "REVIEW";
      reasoning = (v.reasoning as string) || reasoning;
      recommendedActions = (v.recommended_actions as string[]) || recommendedActions;
      euCompliance = (v.eu_ai_act_compliance as StreamDataPart["eu_ai_act_compliance"]) || euCompliance;
    }

    setState((prev) => ({
      ...prev,
      verdict: {
        verdict: (verdictDecision as "APPROVE" | "BLOCK" | "ESCALATE" | "REVIEW") || "REVIEW",
        riskLevel: (data.risk_level as "low" | "medium" | "high" | "critical") || "medium",
        confidenceScore: data.confidence_score || 0.5,
        reasoning: reasoning,
        recommendedActions: recommendedActions,
        euAiActCompliance: {
          article13Satisfied: euCompliance?.article_13_satisfied ?? true,
          transparencyStatement:
            euCompliance?.transparency_statement ||
            "Generated by FIS Swarm AI",
          humanOversightRequired:
            euCompliance?.human_oversight_required ?? true,
        },
      },
    }));
  } else if (data.type === "graph") {
    setState((prev) => ({
      ...prev,
      graphData: {
        nodes: data.nodes || [],
        links: data.links || [],
        highlightPath: data.highlight_path || [],
      },
    }));
  }
}
