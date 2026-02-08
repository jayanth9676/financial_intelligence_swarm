"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export type WebSocketEvent =
	| { type: "transaction.created"; data: { uetr: string } }
	| { type: "transaction.updated"; data: { uetr: string; status: string } }
	| { type: "transaction.completed"; data: { uetr: string; verdict: Record<string, unknown> } }
	| { type: "alert.created"; data: Record<string, unknown> }
	| { type: "alert.acknowledged"; data: { id: string } }
	| { type: "approval.pending"; data: { uetr: string } }
	| { type: "approval.completed"; data: { uetr: string; action: string } }
	| { type: "investigation.started"; data: { uetr: string } }
	| { type: "investigation.completed"; data: { uetr: string; verdict: Record<string, unknown> } }
	| { type: "heartbeat"; timestamp: string }
	| { type: "pong"; timestamp: string }
	| { type: "connection.established"; message: string };

interface UseWebSocketOptions {
	channel?: "all" | "transactions" | "alerts" | "approvals";
	onMessage?: (event: WebSocketEvent) => void;
	onConnect?: () => void;
	onDisconnect?: () => void;
	autoReconnect?: boolean;
	reconnectInterval?: number;
}

import { WS_BASE_URL } from "../lib/api";

export function useWebSocket(options: UseWebSocketOptions = {}) {
	const {
		channel = "all",
		onMessage,
		onConnect,
		onDisconnect,
		autoReconnect = true,
		reconnectInterval = 5000,
	} = options;

	const wsRef = useRef<WebSocket | null>(null);
	const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const connectRef = useRef<(() => void) | null>(null);
	const [isConnected, setIsConnected] = useState(false);
	const [lastMessage, setLastMessage] = useState<WebSocketEvent | null>(null);

	const connect = useCallback(() => {
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			return;
		}

		const wsUrl = channel === "all" ? `${WS_BASE_URL}/ws` : `${WS_BASE_URL}/ws/${channel}`;

		try {
			const ws = new WebSocket(wsUrl);
			wsRef.current = ws;

			ws.onopen = () => {
				setIsConnected(true);
				onConnect?.();

				// Clear any pending reconnect
				if (reconnectTimeoutRef.current) {
					clearTimeout(reconnectTimeoutRef.current);
					reconnectTimeoutRef.current = null;
				}
			};

			ws.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data) as WebSocketEvent;
					setLastMessage(data);
					onMessage?.(data);
				} catch (err) {
					console.warn("Failed to parse WebSocket message:", err);
				}
			};

			ws.onclose = () => {
				setIsConnected(false);
				onDisconnect?.();
				wsRef.current = null;

				// Auto-reconnect using ref to get latest connect function
				if (autoReconnect && !reconnectTimeoutRef.current) {
					reconnectTimeoutRef.current = setTimeout(() => {
						reconnectTimeoutRef.current = null;
						connectRef.current?.();
					}, reconnectInterval);
				}
			};

			ws.onerror = () => {
				// WebSocket errors don't expose useful info in the browser
				// The connection will close and trigger onclose handler for retry
				// Only log at debug level to avoid noisy console errors
				if (process.env.NODE_ENV === "development") {
					console.debug("WebSocket connection error - will retry on close");
				}
			};
		} catch (err) {
			console.error("Failed to create WebSocket:", err);
		}
	}, [channel, onMessage, onConnect, onDisconnect, autoReconnect, reconnectInterval]);

	// Keep ref updated with latest connect function (in effect, not during render)
	useEffect(() => {
		connectRef.current = connect;
	}, [connect]);

	const disconnect = useCallback(() => {
		if (reconnectTimeoutRef.current) {
			clearTimeout(reconnectTimeoutRef.current);
			reconnectTimeoutRef.current = null;
		}
		wsRef.current?.close();
		wsRef.current = null;
		setIsConnected(false);
	}, []);

	const sendMessage = useCallback((message: Record<string, unknown>) => {
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			wsRef.current.send(JSON.stringify(message));
		}
	}, []);

	const ping = useCallback(() => {
		sendMessage({ type: "ping" });
	}, [sendMessage]);

	useEffect(() => {
		connect();
		return () => {
			disconnect();
		};
	}, [connect, disconnect]);

	return {
		isConnected,
		lastMessage,
		sendMessage,
		ping,
		connect,
		disconnect,
	};
}

// Higher-level hook for dashboard sync
export function useDashboardSync(onUpdate: () => void) {
	const { isConnected, lastMessage } = useWebSocket({
		channel: "all",
		onMessage: (event) => {
			// Trigger refresh on relevant events
			if (
				event.type === "transaction.updated" ||
				event.type === "transaction.completed" ||
				event.type === "alert.created" ||
				event.type === "investigation.completed" ||
				event.type === "approval.completed"
			) {
				onUpdate();
			}
		},
	});

	return { isConnected };
}
