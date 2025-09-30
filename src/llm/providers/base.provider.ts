/**
 * Base LLM Provider Interface
 * Unified abstraction for all LLM providers (OpenAI, Anthropic, Ollama, etc.)
 */

import { EventEmitter } from 'events';

// Core types for LLM operations
export interface LLMMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  name?: string; // For tool messages
  tool_calls?: ToolCall[];
  tool_call_id?: string; // For tool responses
}

export interface ToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string; // JSON string
  };
}

export interface ToolDefinition {
  type: 'function';
  function: {
    name: string;
    description: string;
    parameters: Record<string, any>; // JSON Schema
    required?: string[];
  };
}

export interface CompletionOptions {
  messages: LLMMessage[];
  tools?: ToolDefinition[];
  tool_choice?: 'auto' | 'none' | 'required' | { type: 'function'; function: { name: string } };
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stop?: string[];
  stream?: boolean;
  user?: string;
  metadata?: Record<string, any>;
}

export interface StreamChunk {
  id: string;
  choices: Array<{
    delta: {
      content?: string;
      tool_calls?: Array<{
        index: number;
        id?: string;
        type?: 'function';
        function?: {
          name?: string;
          arguments?: string;
        };
      }>;
    };
    finish_reason?: 'stop' | 'length' | 'tool_calls' | 'content_filter' | null;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface CompletionResponse {
  id: string;
  model: string;
  choices: Array<{
    message: LLMMessage;
    finish_reason: 'stop' | 'length' | 'tool_calls' | 'content_filter';
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  created: number;
}

export interface ModelCapabilities {
  contextWindow: number;
  maxOutputTokens: number;
  supportsFunctions: boolean;
  supportsTools: boolean;
  supportsStreaming: boolean;
  supportsSystemMessages: boolean;
  supportsVision: boolean;
  costPer1kInput?: number;
  costPer1kOutput?: number;
  tokenizerType: 'cl100k_base' | 'claude' | 'llama' | 'custom';
}

export interface ProviderConfig {
  provider: 'openai' | 'anthropic' | 'ollama' | 'openrouter' | 'custom';
  apiKey?: string;
  baseUrl?: string;
  model: string;
  defaultOptions?: Partial<CompletionOptions>;
  headers?: Record<string, string>;
  timeout?: number;
  retryConfig?: {
    maxRetries: number;
    retryDelay: number;
    backoffMultiplier: number;
  };
}

export interface ProviderStatus {
  isAvailable: boolean;
  lastCheck: Date;
  error?: string;
  latency?: number;
  rateLimit?: {
    remaining: number;
    reset: Date;
  };
}

/**
 * Abstract base class for all LLM providers
 */
export abstract class BaseLLMProvider extends EventEmitter {
  protected config: ProviderConfig;
  protected capabilities: ModelCapabilities;
  protected status: ProviderStatus;

  constructor(config: ProviderConfig) {
    super();
    this.config = config;
    this.status = {
      isAvailable: false,
      lastCheck: new Date(),
    };
  }

  /**
   * Initialize the provider (check connectivity, load model info)
   */
  abstract initialize(): Promise<void>;

  /**
   * Get model capabilities
   */
  abstract getCapabilities(): Promise<ModelCapabilities>;

  /**
   * Create a completion (non-streaming)
   */
  abstract createCompletion(options: CompletionOptions): Promise<CompletionResponse>;

  /**
   * Create a streaming completion
   */
  abstract createStreamingCompletion(
    options: CompletionOptions
  ): AsyncIterator<StreamChunk>;

  /**
   * Count tokens in messages (provider-specific tokenization)
   */
  abstract countTokens(messages: LLMMessage[]): Promise<number>;

  /**
   * Convert tools to provider-specific format
   */
  protected abstract formatTools(tools: ToolDefinition[]): any;

  /**
   * Convert provider response to unified format
   */
  protected abstract parseResponse(response: any): CompletionResponse;

  /**
   * Health check
   */
  async checkHealth(): Promise<ProviderStatus> {
    try {
      const start = Date.now();
      // Provider-specific health check
      await this.performHealthCheck();
      this.status = {
        isAvailable: true,
        lastCheck: new Date(),
        latency: Date.now() - start,
      };
    } catch (error) {
      this.status = {
        isAvailable: false,
        lastCheck: new Date(),
        error: error.message,
      };
    }
    return this.status;
  }

  protected abstract performHealthCheck(): Promise<void>;

  /**
   * Handle rate limiting with exponential backoff
   */
  protected async withRetry<T>(
    fn: () => Promise<T>,
    retries = this.config.retryConfig?.maxRetries || 3
  ): Promise<T> {
    let lastError: Error;
    let delay = this.config.retryConfig?.retryDelay || 1000;

    for (let i = 0; i < retries; i++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;
        if (i < retries - 1) {
          await this.sleep(delay);
          delay *= this.config.retryConfig?.backoffMultiplier || 2;
        }
      }
    }
    throw lastError!;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get current status
   */
  getStatus(): ProviderStatus {
    return this.status;
  }

  /**
   * Get provider configuration (without sensitive data)
   */
  getConfig(): Omit<ProviderConfig, 'apiKey'> {
    const { apiKey, ...safeConfig } = this.config;
    return safeConfig;
  }
}