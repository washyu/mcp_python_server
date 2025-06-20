export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;
  timestamp: Date;
}

export interface LLMProvider {
  name: string;
  apiKeyRequired: boolean;
  models: string[];
}

export interface Server {
  hostname?: string;
  name?: string;
  description?: string;
}