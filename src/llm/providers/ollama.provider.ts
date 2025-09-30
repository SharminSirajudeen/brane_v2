/**
 * Ollama Local Model Provider Implementation
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

interface OllamaModel {
  name: string;
  modified_at: string;
  size: number;
  digest: string;
  details?: {
    format: string;
    family: string;
    families: string[];
    parameter_size: string;
    quantization_level: string;
  };
}

export class OllamaProvider extends BaseLLMProvider {
  private apiEndpoint: string;
  private modelInfo?: OllamaModel;

  constructor(config: ProviderConfig) {
    super(config);
    this.apiEndpoint = config.baseUrl || 'http://localhost:11434';
  }

  async initialize(): Promise<void> {
    await this.checkHealth();
    await this.loadModelInfo();
    this.capabilities = await this.getCapabilities();
  }

  private async loadModelInfo(): Promise<void> {
    try {
      const response = await fetch(`${this.apiEndpoint}/api/show`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: this.config.model }),
      });

      if (response.ok) {
        this.modelInfo = await response.json();
      }
    } catch (error) {
      console.warn('Could not load Ollama model info:', error);
    }
  }

  async getCapabilities(): Promise<ModelCapabilities> {
    // Detect model capabilities based on model name/family
    const modelName = this.config.model.toLowerCase();

    let contextWindow = 4096;
    let maxOutputTokens = 2048;
    let supportsTools = false;
    let supportsVision = false;

    // Common model patterns
    if (modelName.includes('llama')) {
      if (modelName.includes('3.2')) {
        contextWindow = 128000;
        maxOutputTokens = 8192;
        supportsTools = true;
      } else if (modelName.includes('3.1')) {
        contextWindow = 128000;
        maxOutputTokens = 4096;
        supportsTools = true;
      } else if (modelName.includes('2')) {
        contextWindow = 4096;
        maxOutputTokens = 2048;
      }
    } else if (modelName.includes('mistral')) {
      contextWindow = 32000;
      maxOutputTokens = 4096;
      supportsTools = true;
    } else if (modelName.includes('mixtral')) {
      contextWindow = 32000;
      maxOutputTokens = 4096;
      supportsTools = true;
    } else if (modelName.includes('qwen')) {
      if (modelName.includes('2.5')) {
        contextWindow = 128000;
        maxOutputTokens = 8192;
        supportsTools = true;
      } else {
        contextWindow = 32000;
        maxOutputTokens = 4096;
      }
    } else if (modelName.includes('llava') || modelName.includes('bakllava')) {
      supportsVision = true;
      contextWindow = 4096;
      maxOutputTokens = 2048;
    } else if (modelName.includes('deepseek')) {
      contextWindow = 128000;
      maxOutputTokens = 4096;
      supportsTools = true;
    }

    return {
      contextWindow,
      maxOutputTokens,
      supportsFunctions: supportsTools,
      supportsTools,
      supportsStreaming: true,
      supportsSystemMessages: true,
      supportsVision,
      tokenizerType: 'llama',
    };
  }

  async createCompletion(options: CompletionOptions): Promise<CompletionResponse> {
    return this.withRetry(async () => {
      const ollamaMessages = this.convertToOllamaFormat(options.messages);

      const response = await fetch(`${this.apiEndpoint}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.config.headers,
        },
        body: JSON.stringify({
          model: this.config.model,
          messages: ollamaMessages,
          tools: options.tools ? this.formatTools(options.tools) : undefined,
          options: {
            temperature: options.temperature ?? 0.7,
            top_p: options.top_p,
            num_predict: options.max_tokens,
            stop: options.stop,
          },
          stream: false,
        }),
        signal: AbortSignal.timeout(this.config.timeout || 120000), // Ollama can be slow
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Ollama API error: ${response.status} - ${error}`);
      }

      const data = await response.json();
      return this.parseResponse(data);
    });
  }

  async *createStreamingCompletion(
    options: CompletionOptions
  ): AsyncIterator<StreamChunk> {
    const ollamaMessages = this.convertToOllamaFormat(options.messages);

    const response = await fetch(`${this.apiEndpoint}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.config.headers,
      },
      body: JSON.stringify({
        model: this.config.model,
        messages: ollamaMessages,
        tools: options.tools ? this.formatTools(options.tools) : undefined,
        options: {
          temperature: options.temperature ?? 0.7,
          top_p: options.top_p,
          num_predict: options.max_tokens,
          stop: options.stop,
        },
        stream: true,
      }),
      signal: AbortSignal.timeout(this.config.timeout || 120000),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Ollama API error: ${response.status} - ${error}`);
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
        if (line.trim()) {
          try {
            const data = JSON.parse(line);
            yield this.convertToStreamChunk(data);

            if (data.done) {
              return;
            }
          } catch (e) {
            console.error('Failed to parse Ollama stream:', e);
          }
        }
      }
    }
  }

  async countTokens(messages: LLMMessage[]): Promise<number> {
    // Rough approximation for Llama-based tokenization
    const text = messages.map(m => m.content).join(' ');
    return Math.ceil(text.length / 3.8);
  }

  protected formatTools(tools: ToolDefinition[]): any {
    // Ollama uses a simplified tool format
    return tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.function.name,
        description: tool.function.description,
        parameters: tool.function.parameters,
      },
    }));
  }

  protected parseResponse(response: any): CompletionResponse {
    const message: LLMMessage = {
      role: 'assistant',
      content: response.message?.content || '',
    };

    // Handle tool calls if present
    if (response.message?.tool_calls) {
      message.tool_calls = response.message.tool_calls;
    }

    return {
      id: response.created_at || Date.now().toString(),
      model: this.config.model,
      choices: [{
        message,
        finish_reason: response.done_reason || 'stop',
      }],
      usage: {
        prompt_tokens: response.prompt_eval_count || 0,
        completion_tokens: response.eval_count || 0,
        total_tokens: (response.prompt_eval_count || 0) + (response.eval_count || 0),
      },
      created: Date.now() / 1000,
    };
  }

  private convertToOllamaFormat(messages: LLMMessage[]): any[] {
    return messages.map(msg => {
      if (msg.role === 'tool') {
        // Convert tool response to user message
        return {
          role: 'user',
          content: `Tool response for ${msg.name}: ${msg.content}`,
        };
      }
      return {
        role: msg.role,
        content: msg.content,
        tool_calls: msg.tool_calls,
      };
    });
  }

  private convertToStreamChunk(data: any): StreamChunk {
    const chunk: StreamChunk = {
      id: data.created_at || Date.now().toString(),
      choices: [{
        delta: {
          content: data.message?.content || '',
        },
        finish_reason: data.done ? 'stop' : null,
      }],
    };

    // Add usage data on final chunk
    if (data.done) {
      chunk.usage = {
        prompt_tokens: data.prompt_eval_count || 0,
        completion_tokens: data.eval_count || 0,
        total_tokens: (data.prompt_eval_count || 0) + (data.eval_count || 0),
      };
    }

    return chunk;
  }

  protected async performHealthCheck(): Promise<void> {
    // Check if Ollama is running and model is available
    const response = await fetch(`${this.apiEndpoint}/api/tags`, {
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error('Ollama server is not responding');
    }

    const data = await response.json();
    const models = data.models || [];

    if (!models.some((m: any) => m.name === this.config.model)) {
      throw new Error(`Model ${this.config.model} not found in Ollama`);
    }
  }

  /**
   * Pull a model if not already available
   */
  async pullModel(onProgress?: (progress: number) => void): Promise<void> {
    const response = await fetch(`${this.apiEndpoint}/api/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: this.config.model, stream: true }),
    });

    if (!response.ok) {
      throw new Error(`Failed to pull model: ${response.statusText}`);
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
        if (line.trim()) {
          try {
            const data = JSON.parse(line);
            if (data.total && data.completed && onProgress) {
              onProgress((data.completed / data.total) * 100);
            }
            if (data.status === 'success') {
              return;
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
  }
}