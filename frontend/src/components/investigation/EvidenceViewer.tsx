"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Scale,
  CreditCard,
  Building2,
  Newspaper,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  BarChart3,
  Search,
} from "lucide-react";

interface Evidence {
  content: string;
  source: string;
  relevanceScore: number;
  documentType: "contract" | "regulation" | "payment_grid" | "annual_report" | "adverse_media";
}

interface EvidenceViewerProps {
  evidence: Evidence[];
  title?: string;
}

const documentTypeConfig = {
  contract: {
    icon: FileText,
    label: "Contract",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    iconColor: "text-blue-500",
    badgeColor: "bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300",
  },
  regulation: {
    icon: Scale,
    label: "Regulation",
    bgColor: "bg-purple-50 dark:bg-purple-900/20",
    borderColor: "border-purple-200 dark:border-purple-800",
    iconColor: "text-purple-500",
    badgeColor: "bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300",
  },
  payment_grid: {
    icon: CreditCard,
    label: "Payment Grid",
    bgColor: "bg-green-50 dark:bg-green-900/20",
    borderColor: "border-green-200 dark:border-green-800",
    iconColor: "text-green-500",
    badgeColor: "bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300",
  },
  annual_report: {
    icon: Building2,
    label: "Annual Report",
    bgColor: "bg-amber-50 dark:bg-amber-900/20",
    borderColor: "border-amber-200 dark:border-amber-800",
    iconColor: "text-amber-500",
    badgeColor: "bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300",
  },
  adverse_media: {
    icon: Newspaper,
    label: "Adverse Media",
    bgColor: "bg-red-50 dark:bg-red-900/20",
    borderColor: "border-red-200 dark:border-red-800",
    iconColor: "text-red-500",
    badgeColor: "bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300",
  },
};

function RelevanceBar({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  const getColor = () => {
    if (score >= 0.8) return "bg-green-500";
    if (score >= 0.6) return "bg-yellow-500";
    if (score >= 0.4) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div className="flex items-center gap-2">
      <BarChart3 className="w-4 h-4 text-gray-400" />
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className={`h-full ${getColor()} rounded-full`}
        />
      </div>
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 min-w-[3rem] text-right">
        {percentage}%
      </span>
    </div>
  );
}

function SyntaxHighlighter({ code, language }: { code: string; language?: string }) {
  const highlightedCode = useMemo(() => {
    let highlighted = code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    if (language === "json" || (!language && code.trim().startsWith("{"))) {
      // JSON syntax highlighting
      highlighted = highlighted
        // Strings (keys and values)
        .replace(
          /"([^"\\]|\\.)*"/g,
          (match) => {
            if (match.endsWith('":') || code.includes(`${match}:`)) {
              return `<span class="text-purple-600 dark:text-purple-400">${match}</span>`;
            }
            return `<span class="text-green-600 dark:text-green-400">${match}</span>`;
          }
        )
        // Numbers
        .replace(
          /\b(\d+\.?\d*)\b/g,
          '<span class="text-blue-600 dark:text-blue-400">$1</span>'
        )
        // Booleans and null
        .replace(
          /\b(true|false|null)\b/g,
          '<span class="text-orange-600 dark:text-orange-400">$1</span>'
        );
    } else if (language === "cypher") {
      // Cypher query highlighting
      highlighted = highlighted
        // Keywords
        .replace(
          /\b(MATCH|WHERE|RETURN|CREATE|MERGE|SET|DELETE|WITH|ORDER BY|LIMIT|OPTIONAL|CALL|YIELD|AS|AND|OR|NOT|IN|IS|NULL)\b/gi,
          '<span class="text-blue-600 dark:text-blue-400 font-semibold">$1</span>'
        )
        // Node labels
        .replace(
          /\(:(\w+)\)/g,
          '(:<span class="text-yellow-600 dark:text-yellow-400">$1</span>)'
        )
        // Relationship types
        .replace(
          /\[:(\w+)\]/g,
          '[:<span class="text-pink-600 dark:text-pink-400">$1</span>]'
        )
        // Properties
        .replace(
          /\{([^}]+)\}/g,
          '{<span class="text-green-600 dark:text-green-400">$1</span>}'
        )
        // Strings
        .replace(
          /'([^'\\]|\\.)*'/g,
          '<span class="text-green-600 dark:text-green-400">$&</span>'
        );
    } else if (language === "xml") {
      // XML/ISO 20022 highlighting
      highlighted = highlighted
        // Tags
        .replace(
          /&lt;(\/?[\w:]+)/g,
          '&lt;<span class="text-blue-600 dark:text-blue-400">$1</span>'
        )
        // Attributes
        .replace(
          /(\w+)=(&quot;|")/g,
          '<span class="text-purple-600 dark:text-purple-400">$1</span>=$2'
        )
        // Attribute values
        .replace(
          /=(&quot;|")([^"&]*)(&quot;|")/g,
          '=$1<span class="text-green-600 dark:text-green-400">$2</span>$3'
        );
    }

    return highlighted;
  }, [code, language]);

  return (
    <pre className="bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono">
      <code dangerouslySetInnerHTML={{ __html: highlightedCode }} />
    </pre>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const renderedContent = useMemo(() => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockContent = "";
    let codeBlockLanguage = "";
    let listItems: string[] = [];
    let listType: "ul" | "ol" | null = null;

    const flushList = () => {
      if (listItems.length > 0 && listType) {
        const ListTag = listType;
        elements.push(
          <ListTag
            key={elements.length}
            className={`${listType === "ol" ? "list-decimal" : "list-disc"} list-inside my-2 space-y-1 text-gray-700 dark:text-gray-300`}
          >
            {listItems.map((item, i) => (
              <li key={i}>{renderInlineMarkdown(item)}</li>
            ))}
          </ListTag>
        );
        listItems = [];
        listType = null;
      }
    };

    const renderInlineMarkdown = (text: string): React.ReactNode => {
      // Process inline markdown: bold, italic, code, links
      const parts: React.ReactNode[] = [];
      let remaining = text;
      let keyCounter = 0;

      while (remaining.length > 0) {
        // Bold **text**
        const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
        // Italic *text* or _text_
        const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|_(.+?)_/);
        // Inline code `text`
        const codeMatch = remaining.match(/`([^`]+)`/);
        // Links [text](url)
        const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);

        const matches = [
          boldMatch ? { match: boldMatch, type: "bold", index: boldMatch.index! } : null,
          italicMatch ? { match: italicMatch, type: "italic", index: italicMatch.index! } : null,
          codeMatch ? { match: codeMatch, type: "code", index: codeMatch.index! } : null,
          linkMatch ? { match: linkMatch, type: "link", index: linkMatch.index! } : null,
        ].filter(Boolean).sort((a, b) => a!.index - b!.index);

        if (matches.length === 0) {
          parts.push(remaining);
          break;
        }

        const firstMatch = matches[0]!;
        const beforeMatch = remaining.slice(0, firstMatch.index);
        if (beforeMatch) {
          parts.push(beforeMatch);
        }

        switch (firstMatch.type) {
          case "bold":
            parts.push(
              <strong key={keyCounter++} className="font-semibold">
                {firstMatch.match[1]}
              </strong>
            );
            remaining = remaining.slice(firstMatch.index + firstMatch.match[0].length);
            break;
          case "italic":
            parts.push(
              <em key={keyCounter++} className="italic">
                {firstMatch.match[1] || firstMatch.match[2]}
              </em>
            );
            remaining = remaining.slice(firstMatch.index + firstMatch.match[0].length);
            break;
          case "code":
            parts.push(
              <code
                key={keyCounter++}
                className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-pink-600 dark:text-pink-400 rounded text-sm font-mono"
              >
                {firstMatch.match[1]}
              </code>
            );
            remaining = remaining.slice(firstMatch.index + firstMatch.match[0].length);
            break;
          case "link":
            parts.push(
              <a
                key={keyCounter++}
                href={firstMatch.match[2]}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
              >
                {firstMatch.match[1]}
                <ExternalLink className="w-3 h-3" />
              </a>
            );
            remaining = remaining.slice(firstMatch.index + firstMatch.match[0].length);
            break;
        }
      }

      return parts.length === 1 && typeof parts[0] === "string" ? parts[0] : <>{parts}</>;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code block handling
      if (line.startsWith("```")) {
        if (inCodeBlock) {
          flushList();
          elements.push(
            <SyntaxHighlighter
              key={elements.length}
              code={codeBlockContent.trim()}
              language={codeBlockLanguage}
            />
          );
          inCodeBlock = false;
          codeBlockContent = "";
          codeBlockLanguage = "";
        } else {
          flushList();
          inCodeBlock = true;
          codeBlockLanguage = line.slice(3).trim();
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent += line + "\n";
        continue;
      }

      // Headers
      if (line.startsWith("### ")) {
        flushList();
        elements.push(
          <h3 key={elements.length} className="text-lg font-semibold text-gray-900 dark:text-white mt-4 mb-2">
            {renderInlineMarkdown(line.slice(4))}
          </h3>
        );
        continue;
      }

      if (line.startsWith("## ")) {
        flushList();
        elements.push(
          <h2 key={elements.length} className="text-xl font-bold text-gray-900 dark:text-white mt-4 mb-2">
            {renderInlineMarkdown(line.slice(3))}
          </h2>
        );
        continue;
      }

      if (line.startsWith("# ")) {
        flushList();
        elements.push(
          <h1 key={elements.length} className="text-2xl font-bold text-gray-900 dark:text-white mt-4 mb-2">
            {renderInlineMarkdown(line.slice(2))}
          </h1>
        );
        continue;
      }

      // Blockquote
      if (line.startsWith("> ")) {
        flushList();
        elements.push(
          <blockquote
            key={elements.length}
            className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 py-1 my-2 text-gray-600 dark:text-gray-400 italic"
          >
            {renderInlineMarkdown(line.slice(2))}
          </blockquote>
        );
        continue;
      }

      // Horizontal rule
      if (line.match(/^(-{3,}|\*{3,}|_{3,})$/)) {
        flushList();
        elements.push(
          <hr key={elements.length} className="my-4 border-gray-200 dark:border-gray-700" />
        );
        continue;
      }

      // Unordered list
      if (line.match(/^[-*+]\s/)) {
        if (listType !== "ul") {
          flushList();
          listType = "ul";
        }
        listItems.push(line.slice(2));
        continue;
      }

      // Ordered list
      if (line.match(/^\d+\.\s/)) {
        if (listType !== "ol") {
          flushList();
          listType = "ol";
        }
        listItems.push(line.replace(/^\d+\.\s/, ""));
        continue;
      }

      // Empty line
      if (line.trim() === "") {
        flushList();
        continue;
      }

      // Regular paragraph
      flushList();
      elements.push(
        <p key={elements.length} className="text-gray-700 dark:text-gray-300 my-2 leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>
      );
    }

    flushList();
    return elements;
  }, [content]);

  return <div className="prose-sm max-w-none">{renderedContent}</div>;
}

function EvidenceCard({
  evidence,
  index,
  isExpanded,
  onToggle,
}: {
  evidence: Evidence;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const config = documentTypeConfig[evidence.documentType];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`rounded-lg border ${config.bgColor} ${config.borderColor} overflow-hidden`}
    >
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronRight className="w-4 h-4 text-gray-500" />
        </motion.div>

        <Icon className={`w-5 h-5 ${config.iconColor} flex-shrink-0`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded ${config.badgeColor}`}>
              {config.label}
            </span>
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {evidence.source}
            </span>
          </div>
        </div>

        <div className="w-32 flex-shrink-0">
          <RelevanceBar score={evidence.relevanceScore} />
        </div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-3 text-sm text-gray-500 dark:text-gray-400">
                <ExternalLink className="w-4 h-4" />
                <span>Source: {evidence.source}</span>
              </div>
              <MarkdownRenderer content={evidence.content} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export function EvidenceViewer({ evidence, title = "Evidence Review" }: EvidenceViewerProps) {
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"relevance" | "type">("relevance");

  const toggleExpanded = useCallback((index: number) => {
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedIndices(new Set(evidence.map((_, i) => i)));
  }, [evidence]);

  const collapseAll = useCallback(() => {
    setExpandedIndices(new Set());
  }, []);

  const filteredAndSortedEvidence = useMemo(() => {
    let result = evidence;

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (e) =>
          e.content.toLowerCase().includes(query) ||
          e.source.toLowerCase().includes(query) ||
          e.documentType.toLowerCase().includes(query)
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      if (sortBy === "relevance") {
        return b.relevanceScore - a.relevanceScore;
      }
      return a.documentType.localeCompare(b.documentType);
    });

    return result;
  }, [evidence, searchQuery, sortBy]);

  const averageRelevance = useMemo(() => {
    if (evidence.length === 0) return 0;
    return evidence.reduce((sum, e) => sum + e.relevanceScore, 0) / evidence.length;
  }, [evidence]);

  if (evidence.length === 0) {
    return (
      <div className="p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
          <FileText className="w-12 h-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">No Evidence Found</p>
          <p className="text-sm mt-1">Evidence documents will appear here during investigation.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {title}
            </h2>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ({evidence.length} document{evidence.length !== 1 ? "s" : ""})
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Avg. Relevance:{" "}
              <span className="font-medium text-gray-900 dark:text-white">
                {Math.round(averageRelevance * 100)}%
              </span>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 mt-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "relevance" | "type")}
            className="px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="relevance">Sort by Relevance</option>
            <option value="type">Sort by Type</option>
          </select>

          <div className="flex gap-1">
            <button
              onClick={expandAll}
              className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
            <button
              onClick={collapseAll}
              className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Evidence List */}
      <div className="p-4 space-y-3 max-h-[600px] overflow-y-auto">
        {filteredAndSortedEvidence.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No evidence matches your search.</p>
          </div>
        ) : (
          filteredAndSortedEvidence.map((item, index) => (
            <EvidenceCard
              key={`${item.source}-${index}`}
              evidence={item}
              index={index}
              isExpanded={expandedIndices.has(evidence.indexOf(item))}
              onToggle={() => toggleExpanded(evidence.indexOf(item))}
            />
          ))
        )}
      </div>
    </div>
  );
}
