import { Message, LLMProvider, Server } from './types';
import { ClaudeAPI } from './api/claude';
import { MCPClient } from './mcp/client';
import { ChatMessage } from './ui/ChatMessage';
import { ChatInput } from './ui/ChatInput';
import { Storage } from './utils/storage';

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
      models: ['llama3.2', 'mistral', 'phi', 'neural-chat', 'qwen2.5-coder']
    }
  ];

  constructor() {
    this.initializeUI();
    this.loadSettings();
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
    this.providers.forEach(provider => {
      const option = document.createElement('option');
      option.value = provider.name;
      option.textContent = provider.name;
      this.providerSelect.appendChild(option);
    });
  }

  private populateServers() {
    const servers: Server[] = [
      { hostname: 'localhost', description: 'Local server' },
      { hostname: 'proxmox.local', description: 'Proxmox VE' },
      { hostname: 'lxd.local', description: 'LXD Host' }
    ];

    servers.forEach(server => {
      const option = document.createElement('option');
      option.value = server.hostname || '';
      option.textContent = `${server.hostname} - ${server.description}`;
      this.serverSelect.appendChild(option);
    });
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

    // Build system message
    const systemMessage = this.mcpClient.isConnected() && this.mcpClient.getTools().length > 0
      ? `You have access to MCP tools for LXD container and Proxmox VM management on server "${this.mcpClient.getCurrentServer()}". Available tools: ${this.mcpClient.getTools().map(t => t.name).join(', ')}. When the user asks for infrastructure tasks, use the appropriate tools. The current server context is ${this.mcpClient.getCurrentServer()}.`
      : '';

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
        }
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
    // Ollama implementation would go here
    this.addSystemMessage('Ollama integration not yet implemented');
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
    const updatedHtml = ChatMessage.render(message);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = updatedHtml;
    const newElement = tempDiv.firstElementChild as HTMLElement;
    element.replaceWith(newElement);
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