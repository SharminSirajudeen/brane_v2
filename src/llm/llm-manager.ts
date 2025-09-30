/**
 * LLM Manager - Central orchestrator for all LLM operations
 * Handles provider selection, fallbacks, context management, and tool orchestration
 */

import { EventEmitter } from 'events';
import {
  BaseLLMProvider,
  CompletionOptions,
  CompletionResponse,
  StreamChunk,
  LLMMessage,
  ToolDefinition,
  ProviderConfig,
  ModelCapabilities,
} from './providers/base.provider';
import { OpenAIProvider } from './providers/openai.provider';
import { AnthropicProvider } from './providers/anthropic.provider';
import { OllamaProvider } from './providers/ollama.provider';
import { OpenRouterProvider } from './providers/openrouter.provider';
import { ContextManager } from './context-manager';
import { ToolOrchestrator } from './tool-orchestrator';

export interface LLMManagerConfig {
  providers: ProviderConfig[];
  defaultProvider?: string;
  fallbackProviders?: string[];
  contextStrategy?: 'sliding' | 'summarize' | 'smart';
  maxRetries?: number;
  enableCaching?: boolean;
  cacheDir?: string;
}

export interface ConversationOptions extends Omit<CompletionOptions, 'messages'> {
  conversationId?: string;
  systemPrompt?: string;
  userMessage: string;
  includeHistory?: boolean;
  ragContext?: string[];
}

export class LLMManager extends EventEmitter {
  private providers: Map<string, BaseLLMProvider> = new Map();
  private activeProvider: BaseLLMProvider | null = null;
  private config: LLMManagerConfig;
  private contextManager: ContextManager;
  private toolOrchestrator: ToolOrchestrator;
  private conversations: Map<string, LLMMessage[]> = new Map();

  constructor(config: LLMManagerConfig) {
    super();
    this.config = config;
    this.contextManager = new ContextManager();
    this.toolOrchestrator = new ToolOrchestrator();
  }

  async initialize(): Promise<void> {
    // Initialize all configured providers
    for (const providerConfig of this.config.providers) {
      const provider = this.createProvider(providerConfig);
      await provider.initialize();
      this.providers.set(providerConfig.provider, provider);

      // Set default provider
      if (this.config.defaultProvider === providerConfig.provider || !this.activeProvider) {
        this.activeProvider = provider;
      }
    }

    if (!this.activeProvider) {
      throw new Error('No LLM providers configured');
    }

    this.emit('initialized', {
      providers: Array.from(this.providers.keys()),
      defaultProvider: this.config.defaultProvider,
    });
  }

  private createProvider(config: ProviderConfig): BaseLLMProvider {
    switch (config.provider) {
      case 'openai':
        return new OpenAIProvider(config);
      case 'anthropic':
        return new AnthropicProvider(config);
      case 'ollama':
        return new OllamaProvider(config);
      case 'openrouter':
        return new OpenRouterProvider(config);
      default:
        throw new Error(`Unknown provider: ${config.provider}`);
    }
  }

  /**
   * Main conversation interface with automatic context management
   */
  async chat(options: ConversationOptions): Promise<CompletionResponse> {
    const conversationId = options.conversationId || 'default';
    const history = this.conversations.get(conversationId) || [];
    const capabilities = await this.activeProvider!.getCapabilities();

    // Build messages with context management
    let messages: LLMMessage[] = [];

    // Add system prompt
    if (options.systemPrompt) {
      messages.push({
        role: 'system',
        content: options.systemPrompt,
      });
    }

    // Add RAG context if provided
    if (options.ragContext && options.ragContext.length > 0) {
      const ragPrompt = this.formatRAGContext(options.ragContext);
      messages.push({
        role: 'system',
        content: `Relevant context:\n${ragPrompt}`,
      });
    }

    // Add conversation history
    if (options.includeHistory !== false) {
      messages.push(...history);
    }

    // Add user message
    messages.push({
      role: 'user',
      content: options.userMessage,
    });

    // Apply context management strategy
    messages = await this.contextManager.optimizeMessages(
      messages,
      capabilities.contextWindow,
      this.config.contextStrategy || 'sliding'
    );

    // Create completion options
    const completionOptions: CompletionOptions = {
      ...options,
      messages,
    };

    // Execute with retries and fallbacks
    const response = await this.executeWithFallbacks(
      () => this.activeProvider!.createCompletion(completionOptions)
    );

    // Update conversation history
    history.push(
      { role: 'user', content: options.userMessage },
      response.choices[0].message
    );
    this.conversations.set(conversationId, history);

    // Emit event for monitoring
    this.emit('completion', {
      conversationId,
      provider: this.activeProvider!.getConfig().provider,
      usage: response.usage,
    });

    return response;
  }

  /**
   * Streaming chat interface
   */
  async *streamChat(options: ConversationOptions): AsyncIterator<StreamChunk> {
    const conversationId = options.conversationId || 'default';
    const history = this.conversations.get(conversationId) || [];
    const capabilities = await this.activeProvider!.getCapabilities();

    // Build messages (same as chat method)
    let messages: LLMMessage[] = [];

    if (options.systemPrompt) {
      messages.push({
        role: 'system',
        content: options.systemPrompt,
      });
    }

    if (options.ragContext && options.ragContext.length > 0) {
      const ragPrompt = this.formatRAGContext(options.ragContext);
      messages.push({
        role: 'system',
        content: `Relevant context:\n${ragPrompt}`,
      });
    }

    if (options.includeHistory !== false) {
      messages.push(...history);
    }

    messages.push({
      role: 'user',
      content: options.userMessage,
    });

    messages = await this.contextManager.optimizeMessages(
      messages,
      capabilities.contextWindow,
      this.config.contextStrategy || 'sliding'
    );

    const completionOptions: CompletionOptions = {
      ...options,
      messages,
      stream: true,
    };

    // Stream with current provider
    let fullResponse = '';
    let toolCalls: any[] = [];

    for await (const chunk of this.activeProvider!.createStreamingCompletion(completionOptions)) {
      // Accumulate response
      if (chunk.choices[0]?.delta?.content) {
        fullResponse += chunk.choices[0].delta.content;
      }

      if (chunk.choices[0]?.delta?.tool_calls) {
        // Accumulate tool calls
        for (const toolCall of chunk.choices[0].delta.tool_calls) {
          if (!toolCalls[toolCall.index]) {
            toolCalls[toolCall.index] = {
              id: toolCall.id || '',
              type: 'function',
              function: { name: '', arguments: '' },
            };
          }

          if (toolCall.function?.name) {
            toolCalls[toolCall.index].function.name += toolCall.function.name;
          }
          if (toolCall.function?.arguments) {
            toolCalls[toolCall.index].function.arguments += toolCall.function.arguments;
          }
        }
      }

      yield chunk;
    }

    // Update conversation history
    const assistantMessage: LLMMessage = {
      role: 'assistant',
      content: fullResponse,
    };

    if (toolCalls.length > 0) {
      assistantMessage.tool_calls = toolCalls;
    }

    history.push(
      { role: 'user', content: options.userMessage },
      assistantMessage
    );
    this.conversations.set(conversationId, history);
  }

  /**
   * Execute tool calls and continue conversation
   */
  async executeToolCalls(
    conversationId: string,
    toolCalls: any[],
    availableTools: Map<string, Function>
  ): Promise<CompletionResponse> {
    const history = this.conversations.get(conversationId) || [];

    // Execute each tool call
    for (const toolCall of toolCalls) {
      const tool = availableTools.get(toolCall.function.name);
      if (!tool) {
        throw new Error(`Tool not found: ${toolCall.function.name}`);
      }

      try {
        const args = JSON.parse(toolCall.function.arguments);
        const result = await tool(args);

        // Add tool response to history
        history.push({
          role: 'tool',
          content: JSON.stringify(result),
          tool_call_id: toolCall.id,
          name: toolCall.function.name,
        });
      } catch (error) {
        // Add error to history
        history.push({
          role: 'tool',
          content: `Error: ${error.message}`,
          tool_call_id: toolCall.id,
          name: toolCall.function.name,
        });
      }
    }

    this.conversations.set(conversationId, history);

    // Continue conversation with tool results
    const capabilities = await this.activeProvider!.getCapabilities();
    let messages = await this.contextManager.optimizeMessages(
      history,
      capabilities.contextWindow,
      this.config.contextStrategy || 'sliding'
    );

    return this.activeProvider!.createCompletion({ messages });
  }

  /**
   * Switch active provider
   */
  async switchProvider(providerName: string): Promise<void> {
    const provider = this.providers.get(providerName);
    if (!provider) {
      throw new Error(`Provider not found: ${providerName}`);
    }

    const status = await provider.checkHealth();
    if (!status.isAvailable) {
      throw new Error(`Provider not available: ${status.error}`);
    }

    this.activeProvider = provider;
    this.emit('providerSwitched', providerName);
  }

  /**
   * Execute with fallback providers
   */
  private async executeWithFallbacks<T>(
    fn: () => Promise<T>,
    triedProviders: Set<string> = new Set()
  ): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      console.error(`Provider failed:`, error);

      // Try fallback providers
      if (this.config.fallbackProviders) {
        for (const fallbackName of this.config.fallbackProviders) {
          if (triedProviders.has(fallbackName)) continue;

          const fallbackProvider = this.providers.get(fallbackName);
          if (!fallbackProvider) continue;

          const status = await fallbackProvider.checkHealth();
          if (!status.isAvailable) continue;

          // Switch to fallback
          const originalProvider = this.activeProvider;
          this.activeProvider = fallbackProvider;
          triedProviders.add(fallbackName);

          try {
            this.emit('fallbackActivated', fallbackName);
            const result = await this.executeWithFallbacks(fn, triedProviders);

            // Restore original provider for next request
            this.activeProvider = originalProvider;
            return result;
          } catch (fallbackError) {
            this.activeProvider = originalProvider;
            // Continue to next fallback
          }
        }
      }

      throw error;
    }
  }

  /**
   * Format RAG context for injection
   */
  private formatRAGContext(documents: string[]): string {
    return documents.map((doc, i) => `[Document ${i + 1}]\n${doc}`).join('\n\n');
  }

  /**
   * Get conversation history
   */
  getConversation(conversationId: string): LLMMessage[] {
    return this.conversations.get(conversationId) || [];
  }

  /**
   * Clear conversation history
   */
  clearConversation(conversationId: string): void {
    this.conversations.delete(conversationId);
  }

  /**
   * Get provider status
   */
  async getProviderStatus(): Promise<Map<string, any>> {
    const status = new Map();
    for (const [name, provider] of this.providers) {
      status.set(name, {
        ...await provider.checkHealth(),
        capabilities: await provider.getCapabilities(),
        isActive: provider === this.activeProvider,
      });
    }
    return status;
  }

  /**
   * Count tokens for current provider
   */
  async countTokens(messages: LLMMessage[]): Promise<number> {
    if (!this.activeProvider) {
      throw new Error('No active provider');
    }
    return this.activeProvider.countTokens(messages);
  }
}