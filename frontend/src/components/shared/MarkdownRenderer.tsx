"use client";

import React from "react";

/**
 * Parse inline formatting: **bold**, *italic*, `code`
 */
function parseInlineFormatting(text: string): React.ReactNode[] {
	if (!text) return [];

	const elements: React.ReactNode[] = [];
	let remaining = text;
	let keyCounter = 0;

	// Process text character by character looking for patterns
	while (remaining.length > 0) {
		// Check for inline code first (backticks)
		const codeMatch = remaining.match(/^`([^`]+)`/);
		if (codeMatch) {
			elements.push(
				<code
					key={`code-${keyCounter++}`}
					className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-pink-600 dark:text-pink-400 rounded text-sm font-mono"
				>
					{codeMatch[1]}
				</code>
			);
			remaining = remaining.slice(codeMatch[0].length);
			continue;
		}

		// Check for bold (**text**)
		const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/);
		if (boldMatch) {
			elements.push(
				<strong key={`bold-${keyCounter++}`} className="font-semibold text-gray-900 dark:text-white">
					{boldMatch[1]}
				</strong>
			);
			remaining = remaining.slice(boldMatch[0].length);
			continue;
		}

		// Check for italic (*text*) - but not ** 
		const italicMatch = remaining.match(/^\*([^*]+)\*/);
		if (italicMatch && !remaining.startsWith('**')) {
			elements.push(
				<em key={`italic-${keyCounter++}`} className="italic">
					{italicMatch[1]}
				</em>
			);
			remaining = remaining.slice(italicMatch[0].length);
			continue;
		}

		// Find next special character
		const nextSpecial = remaining.search(/[`*]/);
		if (nextSpecial === -1) {
			elements.push(remaining);
			break;
		} else if (nextSpecial === 0) {
			// Special char but didn't match pattern, just output it
			elements.push(remaining[0]);
			remaining = remaining.slice(1);
		} else {
			elements.push(remaining.slice(0, nextSpecial));
			remaining = remaining.slice(nextSpecial);
		}
	}

	return elements;
}

function processInlineLists(text: string): string {
	// Detect patterns like "(1) ... (2) ..." in a single line
	const inlineNumberPattern = /(\(\d+\))/g;
	const matches = text.match(inlineNumberPattern);

	if (matches && matches.length >= 2) {
		return text.replace(/(\s)(\(\d+\))/g, '\n$2');
	}

	return text;
}

interface CodeBlockProps {
	language?: string;
	code: string;
}

function CodeBlock({ language, code }: CodeBlockProps) {
	return (
		<div className="my-3 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
			{language && (
				<div className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 text-xs font-mono text-gray-500 dark:text-gray-400">
					{language}
				</div>
			)}
			<pre className="p-3 bg-gray-50 dark:bg-gray-900 overflow-x-auto">
				<code className="text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
					{code.trim()}
				</code>
			</pre>
		</div>
	);
}

export function MarkdownRenderer({ content }: { content: string }) {
	if (!content) return null;

	// First, extract code blocks
	const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
	const segments: Array<{ type: 'text' | 'code'; content: string; language?: string }> = [];
	let lastIndex = 0;
	let match;

	while ((match = codeBlockRegex.exec(content)) !== null) {
		if (match.index > lastIndex) {
			segments.push({ type: 'text', content: content.slice(lastIndex, match.index) });
		}
		segments.push({ type: 'code', content: match[2], language: match[1] || undefined });
		lastIndex = match.index + match[0].length;
	}
	if (lastIndex < content.length) {
		segments.push({ type: 'text', content: content.slice(lastIndex) });
	}

	return (
		<div className="text-[15px] leading-relaxed">
			{segments.map((segment, segIdx) => {
				if (segment.type === 'code') {
					return <CodeBlock key={`seg-${segIdx}`} language={segment.language} code={segment.content} />;
				}

				// Process text segment
				const processedContent = segment.content.split('\n').map(processInlineLists).join('\n');
				const lines = processedContent.split('\n');
				const elements: React.ReactNode[] = [];
				let currentList: React.ReactNode[] = [];
				let listType: 'ul' | 'ol' = 'ul';

				const flushList = (keyPrefix: string) => {
					if (currentList.length > 0) {
						if (listType === 'ul') {
							elements.push(
								<ul key={`${keyPrefix}-list`} className="list-disc list-outside ml-5 mb-3 space-y-1.5">
									{currentList}
								</ul>
							);
						} else {
							elements.push(
								<ol key={`${keyPrefix}-list`} className="list-decimal list-outside ml-5 mb-3 space-y-1.5">
									{currentList}
								</ol>
							);
						}
						currentList = [];
					}
				};

				lines.forEach((line, i) => {
					const trimmed = line.trim();

					// Handle Unordered List Items
					if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
						if (currentList.length > 0 && listType === 'ol') flushList(`switch-${segIdx}-${i}`);
						listType = 'ul';
						const text = trimmed.substring(2);
						currentList.push(
							<li key={`li-${segIdx}-${i}`} className="text-gray-700 dark:text-gray-300">
								{parseInlineFormatting(text)}
							</li>
						);
						return;
					}

					// Handle Ordered List Items (1. or (1))
					const orderedMatch = trimmed.match(/^(\d+\.|[\(\[]\d+[\)\]])\s+(.*)/);
					if (orderedMatch) {
						if (currentList.length > 0 && listType === 'ul') flushList(`switch-${segIdx}-${i}`);
						listType = 'ol';
						const text = orderedMatch[2];
						currentList.push(
							<li key={`li-${segIdx}-${i}`} className="text-gray-700 dark:text-gray-300">
								{parseInlineFormatting(text)}
							</li>
						);
						return;
					}

					// Not a list item, flush any pending list
					flushList(`line-${segIdx}-${i}`);

					if (trimmed === "") {
						return;
					}

					// Handle Headers
					if (trimmed.startsWith('#### ')) {
						elements.push(
							<h4 key={`h4-${segIdx}-${i}`} className="text-base font-bold mt-4 mb-2 text-gray-900 dark:text-white">
								{parseInlineFormatting(trimmed.substring(5))}
							</h4>
						);
					} else if (trimmed.startsWith('### ')) {
						elements.push(
							<h3 key={`h3-${segIdx}-${i}`} className="text-lg font-bold mt-4 mb-2 text-gray-900 dark:text-white">
								{parseInlineFormatting(trimmed.substring(4))}
							</h3>
						);
					} else if (trimmed.startsWith('## ')) {
						elements.push(
							<h2 key={`h2-${segIdx}-${i}`} className="text-xl font-bold mt-5 mb-3 text-gray-900 dark:text-white">
								{parseInlineFormatting(trimmed.substring(3))}
							</h2>
						);
					}
					// Handle blockquotes
					else if (trimmed.startsWith('> ')) {
						elements.push(
							<blockquote key={`quote-${segIdx}-${i}`} className="border-l-4 border-blue-400 dark:border-blue-600 pl-4 py-1 my-3 italic text-gray-600 dark:text-gray-400 bg-blue-50/50 dark:bg-blue-900/10 rounded-r">
								{parseInlineFormatting(trimmed.substring(2))}
							</blockquote>
						);
					}
					// Handle "Key: Value" bold headers
					else if (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length < 80 && !trimmed.includes('\n')) {
						elements.push(
							<div key={`bold-header-${segIdx}-${i}`} className="font-bold mt-4 mb-2 text-gray-900 dark:text-white">
								{parseInlineFormatting(trimmed)}
							</div>
						);
					}
					// Horizontal rule
					else if (trimmed === '---' || trimmed === '***') {
						elements.push(
							<hr key={`hr-${segIdx}-${i}`} className="my-4 border-gray-200 dark:border-gray-700" />
						);
					}
					else {
						// Regular paragraph
						elements.push(
							<p key={`p-${segIdx}-${i}`} className="mb-2">
								{parseInlineFormatting(line)}
							</p>
						);
					}
				});

				flushList(`final-${segIdx}`);
				return <React.Fragment key={`text-${segIdx}`}>{elements}</React.Fragment>;
			})}
		</div>
	);
}
