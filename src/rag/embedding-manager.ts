/**
 * Embedding Manager - Handles multiple embedding providers
 * Supports local and cloud-based embedding generation
 */

import { EventEmitter } from 'events';

export interface EmbeddingProvider {
  name: string;
  type: 'local' | 'cloud';
  initialize(): Promise<void>;
  embed(texts: string[]): Promise<number[][]>;
  embedSingle(text: string): Promise<number[]>;
  getDimensions(): number;
  getMaxInputLength(): number;
}

export interface EmbeddingConfig {
  provider: 'openai' | 'cohere' | 'sentence-transformers' | 'ollama' | 'custom';
  model?: string;
  apiKey?: string;
  baseUrl?: string;
  dimensions?: number;
  batchSize?: number;
}

/**
 * OpenAI Embeddings Provider
 */
export class OpenAIEmbeddingProvider implements EmbeddingProvider {
  name = 'openai';
  type: 'local' | 'cloud' = 'cloud';
  private config: EmbeddingConfig;
  private dimensions: number;

  constructor(config: EmbeddingConfig) {
    this.config = config;
    this.dimensions = config.dimensions || 1536; // text-embedding-3-small default
  }

  async initialize(): Promise<void> {
    // Verify API key
    if (!this.config.apiKey) {
      throw new Error('OpenAI API key required');
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    const batchSize = this.config.batchSize || 100;
    const embeddings: number[][] = [];

    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      const response = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        },
        body: JSON.stringify({
          model: this.config.model || 'text-embedding-3-small',
          input: batch,
          dimensions: this.dimensions,
        }),
      });

      if (!response.ok) {
        throw new Error(`OpenAI Embeddings API error: ${response.statusText}`);
      }

      const data = await response.json();
      embeddings.push(...data.data.map((d: any) => d.embedding));
    }

    return embeddings;
  }

  async embedSingle(text: string): Promise<number[]> {
    const embeddings = await this.embed([text]);
    return embeddings[0];
  }

  getDimensions(): number {
    return this.dimensions;
  }

  getMaxInputLength(): number {
    return 8191; // OpenAI limit
  }
}

/**
 * Ollama Embeddings Provider (local)
 */
export class OllamaEmbeddingProvider implements EmbeddingProvider {
  name = 'ollama';
  type: 'local' | 'cloud' = 'local';
  private config: EmbeddingConfig;
  private baseUrl: string;
  private dimensions: number = 4096; // Default for most models

  constructor(config: EmbeddingConfig) {
    this.config = config;
    this.baseUrl = config.baseUrl || 'http://localhost:11434';
  }

  async initialize(): Promise<void> {
    // Check if Ollama is running and model is available
    const response = await fetch(`${this.baseUrl}/api/tags`);
    if (!response.ok) {
      throw new Error('Ollama server not available');
    }

    const data = await response.json();
    const models = data.models || [];
    const model = this.config.model || 'nomic-embed-text';

    if (!models.some((m: any) => m.name.includes(model))) {
      console.warn(`Embedding model ${model} not found, attempting to pull...`);
      await this.pullModel(model);
    }

    // Get model info to determine dimensions
    await this.getModelInfo();
  }

  private async pullModel(model: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: model }),
    });

    if (!response.ok) {
      throw new Error(`Failed to pull embedding model: ${model}`);
    }

    // Wait for pull to complete
    const reader = response.body!.getReader();
    while (true) {
      const { done } = await reader.read();
      if (done) break;
    }
  }

  private async getModelInfo(): Promise<void> {
    const model = this.config.model || 'nomic-embed-text';

    // Model-specific dimensions
    const dimensionMap: Record<string, number> = {
      'nomic-embed-text': 768,
      'mxbai-embed-large': 1024,
      'all-minilm': 384,
      'bge-m3': 1024,
    };

    for (const [key, dim] of Object.entries(dimensionMap)) {
      if (model.includes(key)) {
        this.dimensions = dim;
        return;
      }
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    const embeddings: number[][] = [];

    for (const text of texts) {
      const response = await fetch(`${this.baseUrl}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.config.model || 'nomic-embed-text',
          prompt: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama embeddings error: ${response.statusText}`);
      }

      const data = await response.json();
      embeddings.push(data.embedding);
    }

    return embeddings;
  }

  async embedSingle(text: string): Promise<number[]> {
    const embeddings = await this.embed([text]);
    return embeddings[0];
  }

  getDimensions(): number {
    return this.dimensions;
  }

  getMaxInputLength(): number {
    return 2048; // Conservative limit for local models
  }
}

/**
 * Cohere Embeddings Provider
 */
export class CohereEmbeddingProvider implements EmbeddingProvider {
  name = 'cohere';
  type: 'local' | 'cloud' = 'cloud';
  private config: EmbeddingConfig;
  private dimensions: number;

  constructor(config: EmbeddingConfig) {
    this.config = config;
    this.dimensions = config.dimensions || 1024; // embed-english-v3.0 default
  }

  async initialize(): Promise<void> {
    if (!this.config.apiKey) {
      throw new Error('Cohere API key required');
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    const response = await fetch('https://api.cohere.ai/v1/embed', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        model: this.config.model || 'embed-english-v3.0',
        texts,
        input_type: 'search_document',
        truncate: 'END',
      }),
    });

    if (!response.ok) {
      throw new Error(`Cohere Embeddings API error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.embeddings;
  }

  async embedSingle(text: string): Promise<number[]> {
    const embeddings = await this.embed([text]);
    return embeddings[0];
  }

  getDimensions(): number {
    return this.dimensions;
  }

  getMaxInputLength(): number {
    return 512; // Cohere limit for embed models
  }
}

/**
 * Main Embedding Manager
 */
export class EmbeddingManager extends EventEmitter {
  private provider: EmbeddingProvider | null = null;
  private fallbackProvider: EmbeddingProvider | null = null;
  private cache: Map<string, number[]> = new Map();
  private cacheEnabled: boolean;

  constructor(config: {
    primary: EmbeddingConfig;
    fallback?: EmbeddingConfig;
    cacheEnabled?: boolean;
  }) {
    super();
    this.cacheEnabled = config.cacheEnabled ?? true;
    this.initializeProviders(config);
  }

  private async initializeProviders(config: any): Promise<void> {
    // Initialize primary provider
    this.provider = this.createProvider(config.primary);
    await this.provider.initialize();

    // Initialize fallback if configured
    if (config.fallback) {
      this.fallbackProvider = this.createProvider(config.fallback);
      await this.fallbackProvider.initialize();
    }

    this.emit('initialized', {
      primary: this.provider.name,
      fallback: this.fallbackProvider?.name,
    });
  }

  private createProvider(config: EmbeddingConfig): EmbeddingProvider {
    switch (config.provider) {
      case 'openai':
        return new OpenAIEmbeddingProvider(config);
      case 'ollama':
        return new OllamaEmbeddingProvider(config);
      case 'cohere':
        return new CohereEmbeddingProvider(config);
      default:
        throw new Error(`Unknown embedding provider: ${config.provider}`);
    }
  }

  /**
   * Generate embeddings for texts
   */
  async embed(texts: string[]): Promise<number[][]> {
    // Check cache first
    if (this.cacheEnabled) {
      const cached: number[][] = [];
      const uncached: string[] = [];
      const uncachedIndices: number[] = [];

      texts.forEach((text, i) => {
        const cacheKey = this.getCacheKey(text);
        if (this.cache.has(cacheKey)) {
          cached[i] = this.cache.get(cacheKey)!;
        } else {
          uncached.push(text);
          uncachedIndices.push(i);
        }
      });

      if (uncached.length === 0) {
        return cached;
      }

      // Generate embeddings for uncached texts
      try {
        const newEmbeddings = await this.provider!.embed(uncached);

        // Cache and merge results
        newEmbeddings.forEach((embedding, i) => {
          const text = uncached[i];
          const index = uncachedIndices[i];
          const cacheKey = this.getCacheKey(text);

          this.cache.set(cacheKey, embedding);
          cached[index] = embedding;
        });

        return cached;
      } catch (error) {
        // Try fallback
        if (this.fallbackProvider) {
          return this.fallbackProvider.embed(texts);
        }
        throw error;
      }
    }

    // No cache - generate all
    try {
      return await this.provider!.embed(texts);
    } catch (error) {
      if (this.fallbackProvider) {
        return this.fallbackProvider.embed(texts);
      }
      throw error;
    }
  }

  /**
   * Generate embedding for single text
   */
  async embedSingle(text: string): Promise<number[]> {
    const embeddings = await this.embed([text]);
    return embeddings[0];
  }

  /**
   * Get embedding dimensions
   */
  getDimensions(): number {
    return this.provider!.getDimensions();
  }

  /**
   * Clear embedding cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  private getCacheKey(text: string): string {
    // Simple hash for cache key
    return `${this.provider!.name}:${text.substring(0, 100)}:${text.length}`;
  }
}