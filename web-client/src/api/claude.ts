import { Message } from '../types';

export class ClaudeAPI {
  private apiKey: string;
  private controller?: AbortController;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async streamChat(
    messages: Message[],
    model: string,
    systemMessage: string,
    onChunk: (chunk: string) => void,
    onThinking?: (thinking: string) => void,
    tools?: any[]
  ) {
    this.controller = new AbortController();

    // Filter out empty messages and system messages
    const filteredMessages = messages
      .filter(m => m.role !== 'system')
      .filter(m => m.content && m.content.trim() !== '');

    const requestBody: any = {
      model,
      max_tokens: 4096,
      messages: filteredMessages,
      system: systemMessage,
      stream: true
    };

    // Add tools if provided
    if (tools && tools.length > 0) {
      requestBody.tools = tools;
    }

    const apiEndpoint = 'http://localhost:3001/api/claude';
    console.log('Making request to Claude API proxy:', apiEndpoint);
    console.log('Request body:', requestBody);

    const response = await fetch(apiEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.apiKey
      },
      body: JSON.stringify(requestBody),
      signal: this.controller.signal
    });

    console.log('Response received:', response.status, response.statusText);

    if (!response.ok) {
      let errorMessage = `Claude API error: ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.error) {
          errorMessage += ` - ${errorData.error}`;
        }
      } catch (e) {
        // Ignore JSON parse errors
      }
      throw new Error(errorMessage);
    }

    if (!response.body) throw new Error('No response body');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') continue;

          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'message_start' && onThinking && parsed.message?.metadata?.thinking) {
              onThinking(parsed.message.metadata.thinking);
            } else if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
              onChunk(parsed.delta.text);
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }
  }

  abort() {
    this.controller?.abort();
  }
}