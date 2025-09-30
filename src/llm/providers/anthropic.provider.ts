/**
 * Anthropic Claude Provider Implementation
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

export class AnthropicProvider extends BaseLLMProvider {
  private apiEndpoint: string;

  constructor(config: ProviderConfig) {
    super(config);
    this.apiEndpoint = config.baseUrl || 'https://api.anthropic.com/v1';
  }

  async initialize(): Promise<void> {
    await this.checkHealth();
    this.capabilities = await this.getCapabilities();
  }

  async getCapabilities(): Promise<ModelCapabilities> {
    const modelCaps: Record<string, Partial<ModelCapabilities>> = {
      'claude-3-5-sonnet-20241022': {
        contextWindow: 200000,
        maxOutputTokens: 8192,
        costPer1kInput: 0.003,
        costPer1kOutput: 0.015,
      },
      'claude-3-5-haiku-20241022': {
        contextWindow: 200000,
        maxOutputTokens: 8192,
        costPer1kInput: 0.001,
        costPer1kOutput: 0.005,
      },
      'claude-3-opus-20240229': {
        contextWindow: 200000,
        maxOutputTokens: 4096,
        costPer1kInput: 0.015,
        costPer1kOutput: 0.075,
      },
    };

    const modelConfig = modelCaps[this.config.model] || {};

    return {
      contextWindow: modelConfig.contextWindow || 200000,
      maxOutputTokens: modelConfig.maxOutputTokens || 4096,
      supportsFunctions: false, // Claude uses tools, not functions
      supportsTools: true,
      supportsStreaming: true,
      supportsSystemMessages: true,
      supportsVision: true,
      costPer1kInput: modelConfig.costPer1kInput,
      costPer1kOutput: modelConfig.costPer1kOutput,
      tokenizerType: 'claude',
    };
  }

  async createCompletion(options: CompletionOptions): Promise<CompletionResponse> {
    return this.withRetry(async () => {
      const anthropicMessages = this.convertMessages(options.messages);

      const response = await fetch(`${this.apiEndpoint}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.config.apiKey!,
          'anthropic-version': '2023-06-01',
          ...this.config.headers,
        },
        body: JSON.stringify({
          model: this.config.model,
          messages: anthropicMessages.messages,
          system: anthropicMessages.system,
          tools: options.tools ? this.formatTools(options.tools) : undefined,
          tool_choice: this.convertToolChoice(options.tool_choice),
          max_tokens: options.max_tokens || 4096,
          temperature: options.temperature ?? 0.7,
          top_p: options.top_p,
          stop_sequences: options.stop,
          stream: false,
        }),
        signal: AbortSignal.timeout(this.config.timeout || 60000),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`Anthropic API error: ${response.status} - ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return this.parseResponse(data);
    });
  }

  async *createStreamingCompletion(
    options: CompletionOptions
  ): AsyncIterator<StreamChunk> {
    const anthropicMessages = this.convertMessages(options.messages);

    const response = await fetch(`${this.apiEndpoint}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey!,
        'anthropic-version': '2023-06-01',
        ...this.config.headers,
      },
      body: JSON.stringify({
        model: this.config.model,
        messages: anthropicMessages.messages,
        system: anthropicMessages.system,
        tools: options.tools ? this.formatTools(options.tools) : undefined,
        tool_choice: this.convertToolChoice(options.tool_choice),
        max_tokens: options.max_tokens || 4096,
        temperature: options.temperature ?? 0.7,
        top_p: options.top_p,
        stop_sequences: options.stop,
        stream: true,
      }),
      signal: AbortSignal.timeout(this.config.timeout || 60000),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(`Anthropic API error: ${response.status} - ${error.error?.message || response.statusText}`);
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
          try {
            const event = JSON.parse(data);
            if (event.type === 'content_block_delta') {
              yield this.convertToStreamChunk(event);
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
  }

  async countTokens(messages: LLMMessage[]): Promise<number> {
    // Anthropic tokenization is different from OpenAI
    // Rough approximation for now
    const text = messages.map(m => m.content).join(' ');
    return Math.ceil(text.length / 3.5);
  }

  protected formatTools(tools: ToolDefinition[]): any {
    // Convert OpenAI format to Anthropic format
    return tools.map(tool => ({
      name: tool.function.name,
      description: tool.function.description,
      input_schema: {
        type: 'object',
        properties: tool.function.parameters.properties || {},
        required: tool.function.parameters.required || [],
      },
    }));
  }

  protected parseResponse(response: any): CompletionResponse {
    // Convert Anthropic response to unified format
    const message: LLMMessage = {
      role: 'assistant',
      content: response.content?.[0]?.text || '',
    };

    // Handle tool use
    if (response.content?.some((c: any) => c.type === 'tool_use')) {
      message.tool_calls = response.content
        .filter((c: any) => c.type === 'tool_use')
        .map((tool: any) => ({
          id: tool.id,
          type: 'function',
          function: {
            name: tool.name,
            arguments: JSON.stringify(tool.input),
          },
        }));
    }

    return {
      id: response.id,
      model: response.model,
      choices: [{
        message,
        finish_reason: response.stop_reason === 'tool_use' ? 'tool_calls' : 'stop',
      }],
      usage: {
        prompt_tokens: response.usage?.input_tokens || 0,
        completion_tokens: response.usage?.output_tokens || 0,
        total_tokens: (response.usage?.input_tokens || 0) + (response.usage?.output_tokens || 0),
      },
      created: Date.now() / 1000,
    };
  }

  private convertMessages(messages: LLMMessage[]): {
    messages: any[];
    system?: string;
  } {
    const system = messages.find(m => m.role === 'system')?.content;
    const nonSystemMessages = messages.filter(m => m.role !== 'system');

    return {
      messages: nonSystemMessages.map(msg => {
        if (msg.role === 'tool') {
          return {
            role: 'user',
            content: [{
              type: 'tool_result',
              tool_use_id: msg.tool_call_id,
              content: msg.content,
            }],
          };
        }
        return {
          role: msg.role,
          content: msg.content,
        };
      }),
      system,
    };
  }

  private convertToolChoice(choice: any): any {
    if (!choice) return undefined;
    if (choice === 'auto') return { type: 'auto' };
    if (choice === 'none') return { type: 'none' };
    if (choice === 'required') return { type: 'any' };
    if (choice.type === 'function') {
      return { type: 'tool', name: choice.function.name };
    }
    return undefined;
  }

  private convertToStreamChunk(event: any): StreamChunk {
    return {
      id: event.id || '',
      choices: [{
        delta: {
          content: event.delta?.text,
        },
        finish_reason: null,
      }],
    };
  }

  protected async performHealthCheck(): Promise<void> {
    // Simple health check - just verify API key works
    const response = await fetch(`${this.apiEndpoint}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey!,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: this.config.model || 'claude-3-5-haiku-20241022',
        messages: [{ role: 'user', content: 'Hi' }],
        max_tokens: 1,
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok && response.status !== 401) {
      throw new Error(`Health check failed: ${response.status}`);
    }
  }
}