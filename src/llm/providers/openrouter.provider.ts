/**
 * OpenRouter Provider - Multi-model routing service
 * Supports automatic model selection and fallbacks
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

export class OpenRouterProvider extends BaseLLMProvider {
  private apiEndpoint = 'https://openrouter.ai/api/v1';
  private modelInfo: any = {};

  constructor(config: ProviderConfig) {
    super(config);
    // OpenRouter requires specific headers
    this.config.headers = {
      ...config.headers,
      'HTTP-Referer': 'https://brane-app.com',
      'X-Title': 'BRANE AI Agent Platform',
    };
  }

  async initialize(): Promise<void> {
    await this.checkHealth();
    await this.loadModelInfo();
    this.capabilities = await this.getCapabilities();
  }

  private async loadModelInfo(): Promise<void> {
    try {
      const response = await fetch(`${this.apiEndpoint}/models`, {
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const models = data.data || [];
        this.modelInfo = models.find((m: any) => m.id === this.config.model) || {};
      }
    } catch (error) {
      console.warn('Could not load OpenRouter model info:', error);
    }
  }

  async getCapabilities(): Promise<ModelCapabilities> {
    // Use model info if available
    if (this.modelInfo.context_length) {
      return {
        contextWindow: this.modelInfo.context_length || 4096,
        maxOutputTokens: this.modelInfo.max_completion_tokens || 2048,
        supportsFunctions: this.modelInfo.supports_functions || false,
        supportsTools: this.modelInfo.supports_tools || false,
        supportsStreaming: true,
        supportsSystemMessages: this.modelInfo.supports_system_messages !== false,
        supportsVision: this.modelInfo.architecture?.modality === 'multimodal',
        costPer1kInput: this.modelInfo.pricing?.prompt,
        costPer1kOutput: this.modelInfo.pricing?.completion,
        tokenizerType: this.detectTokenizerType(this.modelInfo.id),
      };
    }

    // Fallback to defaults
    return {
      contextWindow: 8192,
      maxOutputTokens: 2048,
      supportsFunctions: true,
      supportsTools: true,
      supportsStreaming: true,
      supportsSystemMessages: true,
      supportsVision: false,
      tokenizerType: 'cl100k_base',
    };
  }

  private detectTokenizerType(modelId: string): 'cl100k_base' | 'claude' | 'llama' | 'custom' {
    if (modelId.includes('gpt') || modelId.includes('openai')) return 'cl100k_base';
    if (modelId.includes('claude') || modelId.includes('anthropic')) return 'claude';
    if (modelId.includes('llama') || modelId.includes('meta')) return 'llama';
    return 'custom';
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
          // OpenRouter specific options
          transforms: ['middle-out'], // Optimize for best model routing
          route: 'fallback', // Enable automatic fallbacks
        }),
        signal: AbortSignal.timeout(this.config.timeout || 60000),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`OpenRouter API error: ${response.status} - ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();

      // Log which model was actually used
      if (data.model !== this.config.model) {
        console.log(`OpenRouter routed to: ${data.model}`);
      }

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
        transforms: ['middle-out'],
        route: 'fallback',
      }),
      signal: AbortSignal.timeout(this.config.timeout || 60000),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(`OpenRouter API error: ${response.status} - ${error.error?.message || response.statusText}`);
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
    // OpenRouter provides token counting endpoint
    try {
      const response = await fetch(`${this.apiEndpoint}/tokens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        },
        body: JSON.stringify({
          model: this.config.model,
          messages,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        return data.tokens || 0;
      }
    } catch (error) {
      // Fallback to estimation
    }

    // Fallback: rough estimation
    const text = messages.map(m => m.content).join(' ');
    return Math.ceil(text.length / 4);
  }

  protected formatTools(tools: ToolDefinition[]): any {
    // OpenRouter uses OpenAI format
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
    const response = await fetch(`${this.apiEndpoint}/models`, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error('OpenRouter API is not accessible');
    }
  }

  /**
   * Get available models with current pricing
   */
  async getAvailableModels(): Promise<any[]> {
    const response = await fetch(`${this.apiEndpoint}/models`, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      return data.data || [];
    }

    return [];
  }

  /**
   * Get current usage and limits
   */
  async getUsage(): Promise<any> {
    const response = await fetch(`${this.apiEndpoint}/auth/key`, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
    });

    if (response.ok) {
      return response.json();
    }

    return null;
  }
}