/**
 * OpenAI Provider Implementation
 * Supports OpenAI API and OpenAI-compatible endpoints
 */

import {
  BaseLLMProvider,
  CompletionOptions,
  CompletionResponse,
  StreamChunk,
  ModelCapabilities,
  LLMMessage,
  ToolDefinition,
  ProviderConfig,
} from './base.provider';

export class OpenAIProvider extends BaseLLMProvider {
  private apiEndpoint: string;

  constructor(config: ProviderConfig) {
    super(config);
    this.apiEndpoint = config.baseUrl || 'https://api.openai.com/v1';
  }

  async initialize(): Promise<void> {
    await this.checkHealth();
    this.capabilities = await this.getCapabilities();
  }

  async getCapabilities(): Promise<ModelCapabilities> {
    // Model-specific capabilities
    const modelCaps: Record<string, Partial<ModelCapabilities>> = {
      'gpt-4o': {
        contextWindow: 128000,
        maxOutputTokens: 16384,
        supportsVision: true,
        costPer1kInput: 0.0025,
        costPer1kOutput: 0.01,
      },
      'gpt-4o-mini': {
        contextWindow: 128000,
        maxOutputTokens: 16384,
        supportsVision: true,
        costPer1kInput: 0.00015,
        costPer1kOutput: 0.0006,
      },
      'gpt-4-turbo': {
        contextWindow: 128000,
        maxOutputTokens: 4096,
        supportsVision: true,
        costPer1kInput: 0.01,
        costPer1kOutput: 0.03,
      },
      'gpt-3.5-turbo': {
        contextWindow: 16385,
        maxOutputTokens: 4096,
        supportsVision: false,
        costPer1kInput: 0.0005,
        costPer1kOutput: 0.0015,
      },
    };

    const modelConfig = modelCaps[this.config.model] || {};

    return {
      contextWindow: modelConfig.contextWindow || 8192,
      maxOutputTokens: modelConfig.maxOutputTokens || 4096,
      supportsFunctions: true,
      supportsTools: true,
      supportsStreaming: true,
      supportsSystemMessages: true,
      supportsVision: modelConfig.supportsVision || false,
      costPer1kInput: modelConfig.costPer1kInput,
      costPer1kOutput: modelConfig.costPer1kOutput,
      tokenizerType: 'cl100k_base',
    };
  }

  async createCompletion(options: CompletionOptions): Promise<CompletionResponse> {
    return this.withRetry(async () => {
      const response = await fetch(`${this.apiEndpoint}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
          ...this.config.headers,
        },
        body: JSON.stringify({
          model: this.config.model,
          messages: options.messages,
          tools: options.tools ? this.formatTools(options.tools) : undefined,
          tool_choice: options.tool_choice,
          temperature: options.temperature ?? 0.7,
          max_tokens: options.max_tokens,
          top_p: options.top_p,
          frequency_penalty: options.frequency_penalty,
          presence_penalty: options.presence_penalty,
          stop: options.stop,
          stream: false,
          user: options.user,
        }),
        signal: AbortSignal.timeout(this.config.timeout || 60000),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`OpenAI API error: ${response.status} - ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return this.parseResponse(data);
    });
  }

  async *createStreamingCompletion(
    options: CompletionOptions
  ): AsyncIterator<StreamChunk> {
    const response = await fetch(`${this.apiEndpoint}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
        ...this.config.headers,
      },
      body: JSON.stringify({
        model: this.config.model,
        messages: options.messages,
        tools: options.tools ? this.formatTools(options.tools) : undefined,
        tool_choice: options.tool_choice,
        temperature: options.temperature ?? 0.7,
        max_tokens: options.max_tokens,
        top_p: options.top_p,
        frequency_penalty: options.frequency_penalty,
        presence_penalty: options.presence_penalty,
        stop: options.stop,
        stream: true,
        user: options.user,
      }),
      signal: AbortSignal.timeout(this.config.timeout || 60000),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(`OpenAI API error: ${response.status} - ${error.error?.message || response.statusText}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;

          try {
            const chunk = JSON.parse(data);
            yield chunk as StreamChunk;
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
  }

  async countTokens(messages: LLMMessage[]): Promise<number> {
    // Use tiktoken library or approximate
    // For now, rough approximation: 1 token ≈ 4 characters
    const text = messages.map(m => m.content).join(' ');
    return Math.ceil(text.length / 4);
  }

  protected formatTools(tools: ToolDefinition[]): any {
    // OpenAI format is already our base format
    return tools;
  }

  protected parseResponse(response: any): CompletionResponse {
    return {
      id: response.id,
      model: response.model,
      choices: response.choices.map((choice: any) => ({
        message: choice.message,
        finish_reason: choice.finish_reason,
      })),
      usage: response.usage,
      created: response.created,
    };
  }

  protected async performHealthCheck(): Promise<void> {
    // Test with a minimal completion
    await fetch(`${this.apiEndpoint}/models`, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      signal: AbortSignal.timeout(5000),
    });
  }
}