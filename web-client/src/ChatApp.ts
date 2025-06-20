import { Message, LLMProvider, Server } from './types';
import { ClaudeAPI } from './api/claude';
import { MCPClient } from './mcp/client';
import { ChatMessage } from './ui/ChatMessage';
import { ChatInput } from './ui/ChatInput';
import { Storage } from './utils/storage';
import { marked } from 'marked';

export class ChatApp {
  private messages: Message[] = [];
  private mcpClient = new MCPClient();
  private claudeAPI?: ClaudeAPI;
  private chatInput!: ChatInput;
  
  // UI Elements
  private messagesContainer!: HTMLElement;
  private providerSelect!: HTMLSelectElement;
  private modelSelect!: HTMLSelectElement;
  private serverSelect!: HTMLSelectElement;
  private stopButton!: HTMLButtonElement;
  private clearButton!: HTMLButtonElement;
  private settingsButton!: HTMLButtonElement;
  private settingsModal!: HTMLElement;

  private providers: LLMProvider[] = [
    {
      name: 'Claude',
      apiKeyRequired: true,
      models: [
        'claude-3-5-sonnet-20241022',
        'claude-3-5-haiku-20241022',
        'claude-3-opus-20240229',
        'claude-3-sonnet-20240229',
        'claude-3-haiku-20240307'
      ]
    },
    {
      name: 'Ollama',
      apiKeyRequired: false,
      models: ['llama3.1:8b', 'deepseek-r1:8b']
    }
  ];

  constructor() {
    this.initializeUI();
    this.loadSettings();
    this.initializeProviders();
    this.autoConnectMCP();
    ChatMessage.setupMarkdown();
  }

  private initializeUI() {
    // Get UI elements
    this.messagesContainer = document.querySelector('#messages')!;
    this.providerSelect = document.querySelector('#provider-select')!;
    this.modelSelect = document.querySelector('#model-select')!;
    this.serverSelect = document.querySelector('#server-select')!;
    this.stopButton = document.querySelector('#stop-btn')!;
    this.clearButton = document.querySelector('#clear-btn')!;
    this.settingsButton = document.querySelector('#settings-btn')!;
    this.settingsModal = document.querySelector('#settings-modal')!;

    const messageInput = document.querySelector('#message-input') as HTMLTextAreaElement;
    const sendButton = document.querySelector('#send-btn') as HTMLButtonElement;

    // Initialize chat input
    this.chatInput = new ChatInput(
      messageInput,
      sendButton,
      (message) => this.handleSendMessage(message)
    );

    // Setup event listeners
    this.setupEventListeners();
    this.populateProviders();
    this.populateServers();
  }

  private setupEventListeners() {
    this.providerSelect.addEventListener('change', () => this.handleProviderChange());
    this.serverSelect.addEventListener('change', () => this.handleServerChange());
    this.stopButton.addEventListener('click', () => this.handleStop());
    this.clearButton.addEventListener('click', () => this.handleClear());
    this.settingsButton.addEventListener('click', () => this.showSettings());

    // Settings modal
    const closeButton = this.settingsModal.querySelector('.close-button');
    closeButton?.addEventListener('click', () => this.hideSettings());

    const saveButton = this.settingsModal.querySelector('#save-settings');
    saveButton?.addEventListener('click', () => this.saveSettings());
  }

  private populateProviders() {
    this.providerSelect.innerHTML = '';
    this.providers.forEach(provider => {
      const option = document.createElement('option');
      option.value = provider.name;
      option.textContent = provider.name;
      this.providerSelect.appendChild(option);
    });
  }

  private initializeProviders() {
    // Set default provider to Ollama
    this.providerSelect.value = 'Ollama';
    
    // Load models for default provider
    const defaultProvider = this.providers.find(p => p.name === 'Ollama');
    if (defaultProvider) {
      this.updateModelOptions(defaultProvider.models);
    }
  }

  private populateServers() {
    const servers: Server[] = [
      { hostname: 'none', description: 'No MCP server' },
      { hostname: 'localhost:3000', description: 'Universal Homelab MCP Server' }
    ];

    servers.forEach(server => {
      const option = document.createElement('option');
      option.value = server.hostname || '';
      option.textContent = server.hostname === 'none' ? 'No MCP server' : `${server.hostname} - ${server.description}`;
      this.serverSelect.appendChild(option);
    });

    // Set default to localhost:3000
    this.serverSelect.value = 'localhost:3000';
  }

  private async autoConnectMCP() {
    // Auto-connect to the MCP server after UI is initialized
    setTimeout(async () => {
      try {
        await this.mcpClient.connect('localhost:3000');
        this.addSystemMessage('🚀 Connected to Universal Homelab MCP Server with 52+ infrastructure automation tools');
      } catch (error) {
        console.warn('Failed to auto-connect to MCP server:', error);
        this.addSystemMessage('⚠️ Failed to connect to MCP server. Please check if the server is running.');
      }
    }, 1000); // Wait 1 second for UI to be ready
  }

  private convertMCPToolsToClaudeFormat(mcpTools: any[]): any[] {
    return mcpTools.map(tool => ({
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema || {
        type: "object",
        properties: {},
        required: []
      }
    }));
  }

  private handleProviderChange() {
    const provider = this.providers.find(p => p.name === this.providerSelect.value);
    if (provider) {
      this.updateModelOptions(provider.models);
      
      if (provider.name === 'Claude' && !Storage.get('claude_api_key')) {
        this.promptForApiKey();
      }
    }
  }

  private updateModelOptions(models: string[]) {
    this.modelSelect.innerHTML = '';
    models.forEach(model => {
      const option = document.createElement('option');
      option.value = model;
      option.textContent = model;
      this.modelSelect.appendChild(option);
    });
  }

  private async handleServerChange() {
    const server = this.serverSelect.value;
    if (server && server !== 'none') {
      try {
        await this.mcpClient.connect(server);
        this.addSystemMessage(`Connected to MCP server: ${server}`);
      } catch (error) {
        this.addSystemMessage(`Failed to connect to ${server}: ${error}`);
      }
    } else {
      this.mcpClient.disconnect();
    }
  }

  private async handleSendMessage(content: string) {
    if (!content.trim()) return;

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date()
    };
    this.messages.push(userMessage);
    this.renderMessage(userMessage);

    // Disable input during processing
    this.chatInput.setEnabled(false);
    this.stopButton.style.display = 'inline-block';

    try {
      if (this.providerSelect.value === 'Claude') {
        await this.sendClaudeMessage(content);
      } else if (this.providerSelect.value === 'Ollama') {
        await this.sendOllamaMessage(content);
      }
    } catch (error) {
      this.addSystemMessage(`Error: ${error}`);
    } finally {
      this.chatInput.setEnabled(true);
      this.stopButton.style.display = 'none';
    }
  }

  private async sendClaudeMessage(_userMessage: string) {
    const apiKey = Storage.get('claude_api_key');
    if (!apiKey) {
      this.promptForApiKey();
      return;
    }

    if (!this.claudeAPI) {
      this.claudeAPI = new ClaudeAPI(apiKey);
    }

    // Create assistant message
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      thinking: '',
      timestamp: new Date()
    };
    this.messages.push(assistantMessage);
    const messageElement = this.renderMessage(assistantMessage);

    // Let MCP tools be self-describing - minimal system message
    const systemMessage = this.mcpClient.isConnected() && this.mcpClient.getTools().length > 0
      ? `You have access to homelab infrastructure automation tools. When users ask about infrastructure tasks, check your available tools and use them as appropriate.`
      : '';
    
    const claudeTools = this.mcpClient.isConnected() 
      ? this.convertMCPToolsToClaudeFormat(this.mcpClient.getTools())
      : [];

    try {
      await this.claudeAPI.streamChat(
        this.messages.slice(0, -1),
        this.modelSelect.value,
        systemMessage,
        (chunk) => {
          assistantMessage.content += chunk;
          this.updateMessage(messageElement, assistantMessage);
        },
        (thinking) => {
          assistantMessage.thinking += thinking;
          this.updateMessage(messageElement, assistantMessage);
        },
        claudeTools
      );
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        assistantMessage.content += '\n\n*[Response stopped by user]*';
      } else {
        throw error;
      }
    }

    this.updateMessage(messageElement, assistantMessage);
  }

  private async sendOllamaMessage(_userMessage: string) {
    // Create assistant message
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date()
    };
    this.messages.push(assistantMessage);
    const messageElement = this.renderMessage(assistantMessage);

    try {
      // Let MCP tools be self-describing for Ollama too
      const systemMessage = this.mcpClient.isConnected() && this.mcpClient.getTools().length > 0
        ? `You have access to homelab infrastructure automation tools. When users ask about infrastructure tasks, check your available tools and use them as appropriate.`
        : '';

      // Prepare messages for Ollama API
      const ollamaMessages = this.messages.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Add system message if we have MCP tools
      if (systemMessage) {
        ollamaMessages.unshift({
          role: 'system',
          content: systemMessage
        });
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: this.modelSelect.value,
          messages: ollamaMessages,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`MCP Chat API error: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });
          
          // Split by newlines and process complete lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'text' && data.content) {
                  assistantMessage.content += data.content;
                  this.updateMessage(messageElement, assistantMessage);
                } else if (data.type === 'suggestion' && data.content) {
                  assistantMessage.content += data.content;
                  this.updateMessage(messageElement, assistantMessage);
                } else if (data.type === 'done') {
                  break;
                } else if (data.type === 'error') {
                  assistantMessage.content += `\n\nError: ${data.content}`;
                  this.updateMessage(messageElement, assistantMessage);
                }
              } catch (e) {
                // Skip invalid JSON lines
                console.warn('Failed to parse JSON line:', line);
              }
            }
          }
        }
      }
    } catch (error) {
      assistantMessage.content = `Error connecting to MCP Chat: ${error}`;
      this.updateMessage(messageElement, assistantMessage);
    }
  }

  private renderMessage(message: Message): HTMLElement {
    const messageHtml = ChatMessage.render(message);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = messageHtml;
    const messageElement = tempDiv.firstElementChild as HTMLElement;
    this.messagesContainer.appendChild(messageElement);
    this.scrollToBottom();
    return messageElement;
  }

  private updateMessage(element: HTMLElement, message: Message) {
    // Find the content element within the message element
    const contentElement = element.querySelector('.message-content');
    if (contentElement && message.role === 'assistant') {
      // For streaming updates, process markdown to maintain formatting
      // Use marked.parse() synchronously if available, otherwise use marked() and handle the promise
      try {
        const markdownContent = (marked as any).parse ? (marked as any).parse(message.content) : marked(message.content);
        if (typeof markdownContent === 'string') {
          contentElement.innerHTML = markdownContent;
        } else {
          // Handle promise case
          markdownContent.then((content: string) => {
            contentElement.innerHTML = content;
          });
        }
      } catch (e) {
        // Fallback to text content if markdown fails
        contentElement.textContent = message.content;
      }
    } else if (contentElement) {
      // For user messages, use textContent to prevent XSS
      contentElement.textContent = message.content;
    } else {
      // Fallback to full replacement if content element not found
      const updatedHtml = ChatMessage.render(message);
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = updatedHtml;
      const newElement = tempDiv.firstElementChild as HTMLElement;
      element.replaceWith(newElement);
    }
    this.scrollToBottom();
  }


  private addSystemMessage(content: string) {
    const messageHtml = `
      <div class="message system-message">
        <div class="message-content">${content}</div>
      </div>
    `;
    this.messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
    this.scrollToBottom();
  }

  private scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  private handleStop() {
    this.claudeAPI?.abort();
  }

  private handleClear() {
    if (confirm('Clear all messages?')) {
      this.messages = [];
      this.messagesContainer.innerHTML = '';
      this.addSystemMessage('Chat cleared. Ready for new conversation.');
    }
  }

  private promptForApiKey() {
    const apiKey = prompt('Please enter your Claude API key:');
    if (apiKey) {
      Storage.set('claude_api_key', apiKey);
      this.claudeAPI = new ClaudeAPI(apiKey);
    }
  }

  private showSettings() {
    this.settingsModal.style.display = 'flex';
    const apiKeyInput = this.settingsModal.querySelector('#claude-api-key') as HTMLInputElement;
    apiKeyInput.value = Storage.get('claude_api_key') || '';
  }

  private hideSettings() {
    this.settingsModal.style.display = 'none';
  }

  private saveSettings() {
    const apiKeyInput = this.settingsModal.querySelector('#claude-api-key') as HTMLInputElement;
    if (apiKeyInput.value) {
      Storage.set('claude_api_key', apiKeyInput.value);
      this.claudeAPI = new ClaudeAPI(apiKeyInput.value);
    }
    this.hideSettings();
  }

  private loadSettings() {
    const savedProvider = Storage.get('selected_provider');
    if (savedProvider) {
      this.providerSelect.value = savedProvider;
      this.handleProviderChange();
    }

    const savedModel = Storage.get('selected_model');
    if (savedModel) {
      this.modelSelect.value = savedModel;
    }
  }
}