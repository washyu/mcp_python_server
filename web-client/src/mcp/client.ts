export class MCPClient {
  private baseUrl: string = 'http://localhost:3000';
  private sessionId: string | null = null;
  private currentServer: string | null = null;
  private tools: any[] = [];
  private connected: boolean = false;

  async connect(server: string): Promise<void> {
    try {
      console.log(`Connecting to MCP server via HTTP: ${server}`);
      
      // Generate a unique session ID
      this.sessionId = crypto.randomUUID();
      this.currentServer = server;
      
      // Test connection and fetch tools
      await this.fetchTools();
      
      this.connected = true;
      console.log(`Connected to MCP server: ${server}`);
    } catch (error) {
      console.error('HTTP connection error:', error);
      throw new Error(`Failed to connect to ${server}: ${error}`);
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

  async callTool(toolName: string, arguments: any): Promise<any> {
    if (!this.isConnected()) {
      throw new Error('Not connected to MCP server');
    }

    return await this.makeRequest('tools/call', {
      name: toolName,
      arguments: arguments
    });
  }

  private async makeRequest(method: string, params: any): Promise<any> {
    if (!this.sessionId) {
      throw new Error('No session ID - not connected');
    }

    const requestBody = {
      jsonrpc: '2.0',
      method: method,
      params: params,
      id: Date.now()
    };

    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'X-Session-ID': this.sessionId
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    
    if (result.error) {
      throw new Error(`MCP Error: ${result.error.message}`);
    }

    return result;
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
  async executeToolWithStream(toolName: string, arguments: any, onChunk?: (chunk: string) => void): Promise<string> {
    if (!this.isConnected()) {
      throw new Error('Not connected to MCP server');
    }

    const requestBody = {
      jsonrpc: '2.0',
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: arguments
      },
      id: Date.now()
    };

    const response = await fetch(`${this.baseUrl}/mcp/v1/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'X-Session-ID': this.sessionId!
      },
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