/**
 * Tool Orchestrator - Unified tool/function calling across providers
 * Handles format conversion, validation, and execution
 */

import { ToolDefinition, ToolCall } from './providers/base.provider';
import { z, ZodSchema } from 'zod';

export interface Tool {
  name: string;
  description: string;
  parameters: ZodSchema;
  execute: (args: any) => Promise<any>;
  validate?: (args: any) => boolean;
  requiresConfirmation?: boolean;
}

export interface ToolExecutionResult {
  toolCallId: string;
  toolName: string;
  success: boolean;
  result?: any;
  error?: string;
  executionTime: number;
}

export class ToolOrchestrator {
  private tools: Map<string, Tool> = new Map();
  private executionHistory: ToolExecutionResult[] = [];
  private parallelExecutionEnabled = true;

  /**
   * Register a tool
   */
  registerTool(tool: Tool): void {
    this.tools.set(tool.name, tool);
  }

  /**
   * Register multiple tools
   */
  registerTools(tools: Tool[]): void {
    for (const tool of tools) {
      this.registerTool(tool);
    }
  }

  /**
   * Unregister a tool
   */
  unregisterTool(name: string): void {
    this.tools.delete(name);
  }

  /**
   * Get tool definitions in OpenAI format
   */
  getToolDefinitions(): ToolDefinition[] {
    const definitions: ToolDefinition[] = [];

    for (const [name, tool] of this.tools) {
      definitions.push({
        type: 'function',
        function: {
          name: tool.name,
          description: tool.description,
          parameters: this.zodToJsonSchema(tool.parameters),
        },
      });
    }

    return definitions;
  }

  /**
   * Execute tool calls
   */
  async executeToolCalls(
    toolCalls: ToolCall[],
    options: {
      parallel?: boolean;
      confirmationCallback?: (tool: string, args: any) => Promise<boolean>;
    } = {}
  ): Promise<ToolExecutionResult[]> {
    const parallel = options.parallel ?? this.parallelExecutionEnabled;

    if (parallel) {
      return this.executeParallel(toolCalls, options);
    } else {
      return this.executeSequential(toolCalls, options);
    }
  }

  /**
   * Execute tools in parallel
   */
  private async executeParallel(
    toolCalls: ToolCall[],
    options: any
  ): Promise<ToolExecutionResult[]> {
    const promises = toolCalls.map(call => this.executeSingleTool(call, options));
    return Promise.all(promises);
  }

  /**
   * Execute tools sequentially
   */
  private async executeSequential(
    toolCalls: ToolCall[],
    options: any
  ): Promise<ToolExecutionResult[]> {
    const results: ToolExecutionResult[] = [];

    for (const call of toolCalls) {
      const result = await this.executeSingleTool(call, options);
      results.push(result);
    }

    return results;
  }

  /**
   * Execute a single tool call
   */
  private async executeSingleTool(
    call: ToolCall,
    options: any
  ): Promise<ToolExecutionResult> {
    const startTime = Date.now();
    const tool = this.tools.get(call.function.name);

    if (!tool) {
      return {
        toolCallId: call.id,
        toolName: call.function.name,
        success: false,
        error: `Tool not found: ${call.function.name}`,
        executionTime: Date.now() - startTime,
      };
    }

    try {
      // Parse arguments
      const args = JSON.parse(call.function.arguments);

      // Validate arguments
      const validationResult = tool.parameters.safeParse(args);
      if (!validationResult.success) {
        return {
          toolCallId: call.id,
          toolName: tool.name,
          success: false,
          error: `Validation failed: ${validationResult.error.message}`,
          executionTime: Date.now() - startTime,
        };
      }

      // Check if confirmation is required
      if (tool.requiresConfirmation && options.confirmationCallback) {
        const confirmed = await options.confirmationCallback(tool.name, args);
        if (!confirmed) {
          return {
            toolCallId: call.id,
            toolName: tool.name,
            success: false,
            error: 'User declined tool execution',
            executionTime: Date.now() - startTime,
          };
        }
      }

      // Execute tool
      const result = await tool.execute(validationResult.data);

      const executionResult: ToolExecutionResult = {
        toolCallId: call.id,
        toolName: tool.name,
        success: true,
        result,
        executionTime: Date.now() - startTime,
      };

      this.executionHistory.push(executionResult);
      return executionResult;

    } catch (error) {
      const executionResult: ToolExecutionResult = {
        toolCallId: call.id,
        toolName: tool.name,
        success: false,
        error: error.message,
        executionTime: Date.now() - startTime,
      };

      this.executionHistory.push(executionResult);
      return executionResult;
    }
  }

  /**
   * Convert Zod schema to JSON Schema for tool definitions
   */
  private zodToJsonSchema(schema: ZodSchema): any {
    // This is a simplified conversion - in production, use a library like zod-to-json-schema
    const shape = (schema as any)._def?.shape?.() || {};
    const properties: any = {};
    const required: string[] = [];

    for (const [key, value] of Object.entries(shape)) {
      const zodType = (value as any)._def;

      // Determine if field is required
      if (!zodType.typeName?.includes('Optional')) {
        required.push(key);
      }

      // Convert type
      let jsonType = 'string';
      if (zodType.typeName === 'ZodString') jsonType = 'string';
      else if (zodType.typeName === 'ZodNumber') jsonType = 'number';
      else if (zodType.typeName === 'ZodBoolean') jsonType = 'boolean';
      else if (zodType.typeName === 'ZodArray') jsonType = 'array';
      else if (zodType.typeName === 'ZodObject') jsonType = 'object';

      properties[key] = {
        type: jsonType,
        description: zodType.description || '',
      };

      // Handle enums
      if (zodType.values) {
        properties[key].enum = zodType.values;
      }
    }

    return {
      type: 'object',
      properties,
      required,
    };
  }

  /**
   * Get execution history
   */
  getExecutionHistory(): ToolExecutionResult[] {
    return this.executionHistory;
  }

  /**
   * Clear execution history
   */
  clearHistory(): void {
    this.executionHistory = [];
  }

  /**
   * Get available tools
   */
  getAvailableTools(): string[] {
    return Array.from(this.tools.keys());
  }

  /**
   * Get tool by name
   */
  getTool(name: string): Tool | undefined {
    return this.tools.get(name);
  }
}

/**
 * Built-in tools for common operations
 */
export class BuiltinTools {
  /**
   * Web search tool
   */
  static createWebSearchTool(): Tool {
    return {
      name: 'web_search',
      description: 'Search the web for information',
      parameters: z.object({
        query: z.string().describe('Search query'),
        maxResults: z.number().optional().default(5).describe('Maximum number of results'),
      }),
      execute: async ({ query, maxResults }) => {
        // Implement actual web search
        // This is a placeholder
        return {
          results: [
            {
              title: 'Example Result',
              url: 'https://example.com',
              snippet: 'This is an example search result',
            },
          ],
        };
      },
    };
  }

  /**
   * Code execution tool
   */
  static createCodeExecutionTool(): Tool {
    return {
      name: 'execute_code',
      description: 'Execute code in a sandboxed environment',
      parameters: z.object({
        language: z.enum(['javascript', 'python', 'bash']).describe('Programming language'),
        code: z.string().describe('Code to execute'),
      }),
      requiresConfirmation: true,
      execute: async ({ language, code }) => {
        // Implement sandboxed code execution
        // This is a placeholder
        return {
          output: 'Code execution result',
          exitCode: 0,
        };
      },
    };
  }

  /**
   * File system tool
   */
  static createFileSystemTool(): Tool {
    return {
      name: 'file_system',
      description: 'Read or write files',
      parameters: z.object({
        operation: z.enum(['read', 'write', 'list']).describe('File operation'),
        path: z.string().describe('File path'),
        content: z.string().optional().describe('File content (for write operation)'),
      }),
      requiresConfirmation: true,
      execute: async ({ operation, path, content }) => {
        // Implement file system operations with sandboxing
        // This is a placeholder
        switch (operation) {
          case 'read':
            return { content: 'File content' };
          case 'write':
            return { success: true };
          case 'list':
            return { files: ['file1.txt', 'file2.txt'] };
          default:
            throw new Error('Unknown operation');
        }
      },
    };
  }

  /**
   * Calculator tool
   */
  static createCalculatorTool(): Tool {
    return {
      name: 'calculator',
      description: 'Perform mathematical calculations',
      parameters: z.object({
        expression: z.string().describe('Mathematical expression to evaluate'),
      }),
      execute: async ({ expression }) => {
        // Use a safe math expression evaluator
        // This is a simplified example - use mathjs or similar in production
        try {
          // WARNING: eval is dangerous - use a proper math library
          const result = Function(`"use strict"; return (${expression})`)();
          return { result };
        } catch (error) {
          throw new Error(`Failed to evaluate expression: ${error.message}`);
        }
      },
    };
  }
}