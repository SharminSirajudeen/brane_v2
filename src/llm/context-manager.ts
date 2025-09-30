/**
 * Context Manager - Intelligent context window management
 * Handles sliding windows, summarization, and smart truncation
 */

import { LLMMessage } from './providers/base.provider';

export type ContextStrategy = 'sliding' | 'summarize' | 'smart';

export interface ContextOptions {
  preserveSystemMessages?: boolean;
  preserveToolCalls?: boolean;
  preserveRecentMessages?: number;
  summarizationThreshold?: number;
}

export class ContextManager {
  private tokenEstimator: TokenEstimator;

  constructor() {
    this.tokenEstimator = new TokenEstimator();
  }

  /**
   * Optimize messages to fit within context window
   */
  async optimizeMessages(
    messages: LLMMessage[],
    contextWindow: number,
    strategy: ContextStrategy,
    options: ContextOptions = {}
  ): Promise<LLMMessage[]> {
    const estimatedTokens = await this.tokenEstimator.estimateTokens(messages);

    // If within limits, return as-is
    if (estimatedTokens <= contextWindow * 0.9) {
      // Keep 10% buffer
      return messages;
    }

    // Apply strategy
    switch (strategy) {
      case 'sliding':
        return this.applySlidingWindow(messages, contextWindow, options);
      case 'summarize':
        return this.applySummarization(messages, contextWindow, options);
      case 'smart':
        return this.applySmartTruncation(messages, contextWindow, options);
      default:
        return this.applySlidingWindow(messages, contextWindow, options);
    }
  }

  /**
   * Sliding window - keep most recent messages
   */
  private async applySlidingWindow(
    messages: LLMMessage[],
    contextWindow: number,
    options: ContextOptions
  ): Promise<LLMMessage[]> {
    const result: LLMMessage[] = [];
    let tokenCount = 0;
    const targetTokens = Math.floor(contextWindow * 0.9);

    // Always preserve system messages
    const systemMessages = messages.filter(m => m.role === 'system');
    for (const msg of systemMessages) {
      const tokens = await this.tokenEstimator.estimateMessageTokens(msg);
      tokenCount += tokens;
      result.push(msg);
    }

    // Add messages from the end (most recent first)
    const nonSystemMessages = messages.filter(m => m.role !== 'system');
    for (let i = nonSystemMessages.length - 1; i >= 0; i--) {
      const msg = nonSystemMessages[i];
      const tokens = await this.tokenEstimator.estimateMessageTokens(msg);

      if (tokenCount + tokens <= targetTokens) {
        tokenCount += tokens;
        result.splice(systemMessages.length, 0, msg); // Insert after system messages
      } else {
        break;
      }
    }

    return result;
  }

  /**
   * Summarization - replace old messages with summaries
   */
  private async applySummarization(
    messages: LLMMessage[],
    contextWindow: number,
    options: ContextOptions
  ): Promise<LLMMessage[]> {
    const result: LLMMessage[] = [];
    const targetTokens = Math.floor(contextWindow * 0.9);
    const summarizationThreshold = options.summarizationThreshold || 10;

    // Separate messages into groups
    const systemMessages = messages.filter(m => m.role === 'system');
    const conversationMessages = messages.filter(m => m.role !== 'system');

    // Keep system messages
    result.push(...systemMessages);

    // Check if we need to summarize
    if (conversationMessages.length > summarizationThreshold) {
      // Split into messages to summarize and messages to keep
      const toSummarize = conversationMessages.slice(0, -summarizationThreshold);
      const toKeep = conversationMessages.slice(-summarizationThreshold);

      // Create summary of older messages
      const summary = this.createConversationSummary(toSummarize);
      result.push({
        role: 'system',
        content: `Previous conversation summary:\n${summary}`,
      });

      // Add recent messages
      result.push(...toKeep);
    } else {
      result.push(...conversationMessages);
    }

    // Apply sliding window if still too large
    const estimatedTokens = await this.tokenEstimator.estimateTokens(result);
    if (estimatedTokens > targetTokens) {
      return this.applySlidingWindow(result, contextWindow, options);
    }

    return result;
  }

  /**
   * Smart truncation - intelligent message selection
   */
  private async applySmartTruncation(
    messages: LLMMessage[],
    contextWindow: number,
    options: ContextOptions
  ): Promise<LLMMessage[]> {
    const result: LLMMessage[] = [];
    const targetTokens = Math.floor(contextWindow * 0.9);

    // Score messages by importance
    const scoredMessages = messages.map((msg, index) => ({
      message: msg,
      score: this.calculateMessageImportance(msg, index, messages.length),
      index,
    }));

    // Sort by score (higher is more important)
    scoredMessages.sort((a, b) => b.score - a.score);

    // Add messages by importance until context is full
    let tokenCount = 0;
    const selectedMessages: typeof scoredMessages = [];

    for (const item of scoredMessages) {
      const tokens = await this.tokenEstimator.estimateMessageTokens(item.message);
      if (tokenCount + tokens <= targetTokens) {
        tokenCount += tokens;
        selectedMessages.push(item);
      }
    }

    // Sort selected messages back to original order
    selectedMessages.sort((a, b) => a.index - b.index);

    return selectedMessages.map(item => item.message);
  }

  /**
   * Calculate importance score for a message
   */
  private calculateMessageImportance(
    message: LLMMessage,
    index: number,
    totalMessages: number
  ): number {
    let score = 0;

    // System messages are very important
    if (message.role === 'system') {
      score += 100;
    }

    // Recent messages are more important
    const recency = (index / totalMessages) * 50;
    score += recency;

    // Tool calls and responses are important
    if (message.tool_calls || message.tool_call_id) {
      score += 30;
    }

    // Longer messages might contain more context
    const lengthScore = Math.min(message.content.length / 100, 20);
    score += lengthScore;

    // Messages with code blocks are often important
    if (message.content.includes('```')) {
      score += 15;
    }

    // Messages with questions are important
    if (message.content.includes('?')) {
      score += 10;
    }

    return score;
  }

  /**
   * Create a summary of conversation messages
   */
  private createConversationSummary(messages: LLMMessage[]): string {
    const keyPoints: string[] = [];

    for (const msg of messages) {
      if (msg.role === 'user') {
        // Extract user intents
        if (msg.content.length > 50) {
          keyPoints.push(`User asked: ${msg.content.substring(0, 100)}...`);
        } else {
          keyPoints.push(`User: ${msg.content}`);
        }
      } else if (msg.role === 'assistant') {
        // Extract key responses
        if (msg.tool_calls) {
          keyPoints.push(`Assistant called tools: ${msg.tool_calls.map(t => t.function.name).join(', ')}`);
        } else if (msg.content.length > 100) {
          const firstLine = msg.content.split('\n')[0];
          keyPoints.push(`Assistant: ${firstLine.substring(0, 100)}...`);
        }
      }
    }

    return keyPoints.join('\n');
  }
}

/**
 * Token estimation utility
 */
class TokenEstimator {
  /**
   * Estimate tokens for multiple messages
   */
  async estimateTokens(messages: LLMMessage[]): Promise<number> {
    let total = 0;
    for (const msg of messages) {
      total += await this.estimateMessageTokens(msg);
    }
    return total;
  }

  /**
   * Estimate tokens for a single message
   */
  async estimateMessageTokens(message: LLMMessage): Promise<number> {
    // Rough estimation: 1 token ≈ 4 characters
    // Add overhead for message structure
    let tokens = Math.ceil(message.content.length / 4);

    // Add tokens for role
    tokens += 3;

    // Add tokens for tool calls
    if (message.tool_calls) {
      tokens += JSON.stringify(message.tool_calls).length / 4;
    }

    return tokens;
  }
}