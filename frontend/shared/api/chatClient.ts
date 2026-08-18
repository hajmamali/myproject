/**
 * Chat API Client
 * 
 * Client for legal AI assistant chat endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  query: string;
  conversation_id?: string;
  top_k?: number;
}

export interface ChatResponse {
  conversation_id: string;
  query: string;
  answer: string;
  confidence: number;
  sources: Array<{
    id: string;
    text: string;
    score: number;
    metadata: {
      source: string;
      category: string;
    };
  }>;
  graph_context?: any;
  history_length: number;
}

export interface ConversationHistory {
  conversation_id: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
  total_messages: number;
}

export class ChatAPIError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = "ChatAPIError";
  }
}

/**
 * Send chat message to AI assistant
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ChatAPIError(
        error.detail || "Failed to send chat message",
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ChatAPIError) {
      throw error;
    }
    throw new ChatAPIError(
      error instanceof Error ? error.message : "Network error"
    );
  }
}

/**
 * Get conversation history
 */
export async function getConversationHistory(
  conversationId: string
): Promise<ConversationHistory> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new ChatAPIError(
        error.detail || "Failed to get conversation history",
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ChatAPIError) {
      throw error;
    }
    throw new ChatAPIError(
      error instanceof Error ? error.message : "Network error"
    );
  }
}

/**
 * Clear conversation history
 */
export async function clearConversation(
  conversationId: string
): Promise<{ message: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/clear`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new ChatAPIError(
        error.detail || "Failed to clear conversation",
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ChatAPIError) {
      throw error;
    }
    throw new ChatAPIError(
      error instanceof Error ? error.message : "Network error"
    );
  }
}
