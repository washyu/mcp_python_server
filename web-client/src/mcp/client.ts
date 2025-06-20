export class MCPClient {
  private baseUrl: string = '';  // Use relative URL through nginx proxy
  private sessionId: string | null = null;
  private currentServer: string | null = null;
  private tools: any[] = [];
  private connected: boolean = false;

  async connect(server: string): Promise<void> {
    try {
      console.log(`Connecting to MCP server via HTTP: ${server}`);
      
      // Start without session ID - server will provide one
      this.sessionId = null;
      this.currentServer = server;
      
      // Initialize the session first
      await this.initialize();
      
      // Then fetch tools
      await this.fetchTools();
      
      this.connected = true;
      console.log(`Connected to MCP server: ${server}`);
    } catch (error) {
      console.error('HTTP connection error:', error);
      throw new Error(`Failed to connect to ${server}: ${error}`);
    }
  }
  
  private async initialize(): Promise<void> {
    // Call initialize without session ID to get one from server
    const response = await this.makeRequestWithoutSessionCheck('initialize', {
      protocolVersion: '2025-03-26',
      capabilities: {
        experimental: {},
        tools: { listChanged: false }
      },
      clientInfo: {
        name: 'ollama-web-client',
        version: '1.0.0'
      }
    });
    
    if (response.result) {
      console.log('MCP session initialized:', response.result.serverInfo);
    }
  }
  
  private async makeRequestWithoutSessionCheck(method: string, params: any): Promise<any> {
    const requestBody = {
      jsonrpc: '2.0',
      method: method,
      params: params,
      id: Date.now()
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream'
    };

    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    // Check for session ID in response headers
    const sessionId = response.headers.get('mcp-session-id') || response.headers.get('x-session-id');
    if (sessionId) {
      this.sessionId = sessionId;
      console.log('Received session ID from server:', sessionId);
    }

    // Handle Server-Sent Events response format
    const text = await response.text();
    
    // Try to parse as SSE
    if (text.startsWith('event:')) {
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.substring(6);
          try {
            const result = JSON.parse(jsonStr);
            if (result.error) {
              throw new Error(`MCP Error: ${result.error.message}`);
            }
            return result;
          } catch (e) {
            // Continue to next line
          }
        }
      }
    }
    
    // Try to parse as regular JSON
    try {
      const result = JSON.parse(text);
      if (result.error) {
        throw new Error(`MCP Error: ${result.error.message}`);
      }
      return result;
    } catch (e) {
      throw new Error(`Failed to parse response: ${text}`);
    }
  }

  disconnect() {
    this.sessionId = null;
    this.currentServer = null;
    this.tools = [];
    this.connected = false;
    console.log('Disconnected from MCP server');
  }

  private async fetchTools(): Promise<void> {
    const response = await this.makeRequest('tools/list', {});
    if (response.result && response.result.tools) {
      this.tools = response.result.tools;
      console.log(`Received ${this.tools.length} tools from MCP server`);
    }
  }

  async callTool(toolName: string, args: any): Promise<any> {
    if (!this.isConnected()) {
      throw new Error('Not connected to MCP server');
    }

    return await this.makeRequest('tools/call', {
      name: toolName,
      arguments: args
    });
  }

  private async makeRequest(method: string, params: any): Promise<any> {
    const requestBody = {
      jsonrpc: '2.0',
      method: method,
      params: params,
      id: Date.now()
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream'
    };

    // Always send session ID using correct MCP header name
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }

    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    // Handle Server-Sent Events response format
    const text = await response.text();
    
    // Try to parse as SSE
    if (text.startsWith('event:')) {
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.substring(6);
          try {
            const result = JSON.parse(jsonStr);
            if (result.error) {
              throw new Error(`MCP Error: ${result.error.message}`);
            }
            return result;
          } catch (e) {
            // Continue to next line
          }
        }
      }
    }
    
    // Try to parse as regular JSON
    try {
      const result = JSON.parse(text);
      if (result.error) {
        throw new Error(`MCP Error: ${result.error.message}`);
      }
      return result;
    } catch (e) {
      throw new Error(`Failed to parse response: ${text}`);
    }
  }

  getTools() {
    return this.tools;
  }

  getCurrentServer() {
    return this.currentServer;
  }

  isConnected() {
    return this.connected && this.sessionId !== null;
  }

  // New method for streaming tool execution
  async executeToolWithStream(toolName: string, args: any, onChunk?: (chunk: string) => void): Promise<string> {
    if (!this.isConnected()) {
      throw new Error('Not connected to MCP server');
    }

    const requestBody = {
      jsonrpc: '2.0',
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args
      },
      id: Date.now()
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream'
    };

    // Always send session ID using correct MCP header name
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }

    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    // Handle streaming response
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullResponse += chunk;
        
        if (onChunk) {
          onChunk(chunk);
        }
      }
    } else {
      // Fallback for non-streaming
      fullResponse = await response.text();
    }

    try {
      const result = JSON.parse(fullResponse);
      if (result.error) {
        throw new Error(`MCP Error: ${result.error.message}`);
      }
      return result.result?.content?.[0]?.text || fullResponse;
    } catch (e) {
      // If not JSON, return raw response
      return fullResponse;
    }
  }
}