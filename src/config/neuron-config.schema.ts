/**
 * Neuron Configuration Schema
 * Comprehensive configuration for AI agents with LLM provider flexibility
 */

import { z } from 'zod';

/**
 * LLM Provider Configuration
 */
export const LLMProviderSchema = z.object({
  provider: z.enum(['openai', 'anthropic', 'ollama', 'openrouter', 'custom']),
  apiKey: z.string().optional(),
  baseUrl: z.string().url().optional(),
  model: z.string(),
  headers: z.record(z.string()).optional(),
  timeout: z.number().min(1000).max(300000).optional(),
  retryConfig: z.object({
    maxRetries: z.number().min(0).max(10).default(3),
    retryDelay: z.number().min(100).max(10000).default(1000),
    backoffMultiplier: z.number().min(1).max(5).default(2),
  }).optional(),
  defaultOptions: z.object({
    temperature: z.number().min(0).max(2).optional(),
    maxTokens: z.number().min(1).optional(),
    topP: z.number().min(0).max(1).optional(),
    frequencyPenalty: z.number().min(-2).max(2).optional(),
    presencePenalty: z.number().min(-2).max(2).optional(),
    stop: z.array(z.string()).optional(),
  }).optional(),
});

/**
 * Embedding Provider Configuration
 */
export const EmbeddingProviderSchema = z.object({
  provider: z.enum(['openai', 'cohere', 'sentence-transformers', 'ollama']),
  model: z.string().optional(),
  apiKey: z.string().optional(),
  baseUrl: z.string().url().optional(),
  dimensions: z.number().min(64).max(4096).optional(),
  batchSize: z.number().min(1).max(1000).default(100),
});

/**
 * RAG Configuration (Axon)
 */
export const AxonConfigSchema = z.object({
  enabled: z.boolean().default(true),
  vectorStore: z.enum(['faiss', 'chroma', 'pinecone', 'weaviate', 'qdrant']).default('faiss'),
  embeddingProvider: EmbeddingProviderSchema,
  storage: z.object({
    type: z.enum(['local', 'cloud']).default('local'),
    path: z.string().optional(),
    syncEnabled: z.boolean().default(false),
    syncProvider: z.enum(['gdrive', 'dropbox', 's3']).optional(),
  }),
  indexing: z.object({
    chunkSize: z.number().min(100).max(4000).default(1000),
    chunkOverlap: z.number().min(0).max(500).default(200),
    maxDocuments: z.number().min(1).max(100000).default(1000),
    autoIndex: z.boolean().default(true),
  }),
  retrieval: z.object({
    topK: z.number().min(1).max(100).default(5),
    minScore: z.number().min(0).max(1).default(0.7),
    reranking: z.boolean().default(false),
    hybridSearch: z.boolean().default(false),
  }),
});

/**
 * Synapse (Plugin) Configuration
 */
export const SynapseConfigSchema = z.object({
  id: z.string(),
  enabled: z.boolean().default(true),
  config: z.record(z.any()).optional(),
  permissions: z.array(z.enum(['read', 'write', 'execute', 'network'])).optional(),
});

/**
 * MCP (Inter-Neuron Communication) Configuration
 */
export const MCPConfigSchema = z.object({
  enabled: z.boolean().default(false),
  servers: z.array(z.object({
    url: z.string().url(),
    name: z.string(),
    apiKey: z.string().optional(),
  })).optional(),
  discovery: z.object({
    enabled: z.boolean().default(false),
    broadcast: z.boolean().default(false),
    port: z.number().min(1024).max(65535).optional(),
  }).optional(),
});

/**
 * Complete Neuron Configuration Schema
 */
export const NeuronConfigSchema = z.object({
  // Identity
  neuronId: z.string().regex(/^[a-z0-9_-]+$/),
  displayName: z.string(),
  description: z.string().optional(),
  version: z.string().default('1.0.0'),
  author: z.string().optional(),

  // LLM Configuration
  llm: z.object({
    providers: z.array(LLMProviderSchema).min(1),
    defaultProvider: z.string().optional(),
    fallbackProviders: z.array(z.string()).optional(),
    contextStrategy: z.enum(['sliding', 'summarize', 'smart']).default('smart'),
    maxConversationLength: z.number().min(1).max(1000).default(100),
  }),

  // System Prompt
  systemPrompt: z.string().optional(),

  // RAG Configuration (Axon)
  axon: AxonConfigSchema.optional(),

  // Plugins (Synapses)
  synapses: z.array(SynapseConfigSchema).optional(),

  // Tools
  tools: z.array(z.object({
    name: z.string(),
    enabled: z.boolean().default(true),
    requiresConfirmation: z.boolean().default(false),
  })).optional(),

  // MCP Configuration
  mcp: MCPConfigSchema.optional(),

  // Runtime Configuration
  runtime: z.object({
    autoStart: z.boolean().default(false),
    restartOnFailure: z.boolean().default(true),
    maxMemoryMB: z.number().min(128).max(16384).default(2048),
    logging: z.object({
      level: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
      logToFile: z.boolean().default(true),
      logPath: z.string().optional(),
    }),
  }),

  // UI Configuration
  ui: z.object({
    theme: z.enum(['light', 'dark', 'auto']).default('auto'),
    showSystemMessages: z.boolean().default(false),
    showTokenUsage: z.boolean().default(true),
    showCosts: z.boolean().default(false),
    streamingEnabled: z.boolean().default(true),
  }).optional(),

  // Metadata
  metadata: z.record(z.any()).optional(),
});

export type NeuronConfig = z.infer<typeof NeuronConfigSchema>;
export type LLMProviderConfig = z.infer<typeof LLMProviderSchema>;
export type AxonConfig = z.infer<typeof AxonConfigSchema>;
export type SynapseConfig = z.infer<typeof SynapseConfigSchema>;