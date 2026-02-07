"""WebSocket handler for real-time dashboard updates.

Provides real-time notifications for:
- Transaction status changes
- New alerts
- Investigation completions
- Approval queue updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "transactions": set(),
            "alerts": set(),
            "approvals": set(),
            "all": set(),
        }
    
    async def connect(self, websocket: WebSocket, channel: str = "all"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if channel not in self.active_connections:
            channel = "all"
        self.active_connections[channel].add(websocket)
        self.active_connections["all"].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")
    
    def disconnect(self, websocket: WebSocket, channel: str = "all"):
        """Remove a WebSocket connection."""
        self.active_connections.get(channel, set()).discard(websocket)
        self.active_connections["all"].discard(websocket)
    
    async def broadcast(self, message: Dict[str, Any], channel: str = "all"):
        """Broadcast a message to all connections in a channel."""
        connections = self.active_connections.get(channel, set())
        disconnected = []
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn, channel)
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")


# Global connection manager
manager = ConnectionManager()


# Event types
class EventType:
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_COMPLETED = "transaction.completed"
    ALERT_CREATED = "alert.created"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"
    APPROVAL_PENDING = "approval.pending"
    APPROVAL_COMPLETED = "approval.completed"
    INVESTIGATION_STARTED = "investigation.started"
    INVESTIGATION_COMPLETED = "investigation.completed"
    SYSTEM_STATUS = "system.status"


async def notify_transaction_update(uetr: str, status: str, data: Dict[str, Any] = None):
    """Notify clients of a transaction status change."""
    await manager.broadcast({
        "type": EventType.TRANSACTION_UPDATED,
        "timestamp": datetime.now().isoformat(),
        "data": {
            "uetr": uetr,
            "status": status,
            **(data or {}),
        },
    }, channel="transactions")


async def notify_alert_created(alert: Dict[str, Any]):
    """Notify clients of a new alert."""
    await manager.broadcast({
        "type": EventType.ALERT_CREATED,
        "timestamp": datetime.now().isoformat(),
        "data": alert,
    }, channel="alerts")


async def notify_investigation_complete(uetr: str, verdict: Dict[str, Any]):
    """Notify clients when an investigation completes."""
    await manager.broadcast({
        "type": EventType.INVESTIGATION_COMPLETED,
        "timestamp": datetime.now().isoformat(),
        "data": {
            "uetr": uetr,
            "verdict": verdict,
        },
    }, channel="all")


async def notify_approval_update(uetr: str, action: str, level: str):
    """Notify clients of approval queue updates."""
    await manager.broadcast({
        "type": EventType.APPROVAL_COMPLETED if action in ["approved", "rejected"] else EventType.APPROVAL_PENDING,
        "timestamp": datetime.now().isoformat(),
        "data": {
            "uetr": uetr,
            "action": action,
            "level": level,
        },
    }, channel="approvals")


def setup_websocket_routes(app):
    """Setup WebSocket routes on the FastAPI app."""
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Main WebSocket endpoint for all real-time updates."""
        await manager.connect(websocket, "all")
        try:
            # Send initial connection confirmation
            await manager.send_personal(websocket, {
                "type": "connection.established",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to FIS real-time updates",
            })
            
            while True:
                # Keep connection alive and handle incoming messages
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=60.0  # Heartbeat every 60 seconds
                    )
                    
                    # Handle subscription messages
                    try:
                        message = json.loads(data)
                        if message.get("type") == "subscribe":
                            channel = message.get("channel", "all")
                            manager.active_connections.get(channel, set()).add(websocket)
                            await manager.send_personal(websocket, {
                                "type": "subscription.confirmed",
                                "channel": channel,
                            })
                        elif message.get("type") == "ping":
                            await manager.send_personal(websocket, {
                                "type": "pong",
                                "timestamp": datetime.now().isoformat(),
                            })
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await manager.send_personal(websocket, {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                    })
                    
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.info("WebSocket disconnected")
    
    @app.websocket("/ws/{channel}")
    async def websocket_channel_endpoint(websocket: WebSocket, channel: str):
        """Channel-specific WebSocket endpoint."""
        if channel not in ["transactions", "alerts", "approvals"]:
            await websocket.close(code=4000, reason="Invalid channel")
            return
        
        await manager.connect(websocket, channel)
        try:
            await manager.send_personal(websocket, {
                "type": "connection.established",
                "channel": channel,
                "timestamp": datetime.now().isoformat(),
            })
            
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=60.0
                    )
                    if data == "ping":
                        await manager.send_personal(websocket, {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat(),
                        })
                except asyncio.TimeoutError:
                    await manager.send_personal(websocket, {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                    })
                    
        except WebSocketDisconnect:
            manager.disconnect(websocket, channel)
