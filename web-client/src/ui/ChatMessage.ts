import { marked } from 'marked';
import hljs from 'highlight.js';
import { Message } from '../types';

export class ChatMessage {
  static render(message: Message): string {
    const time = new Date(message.timestamp).toLocaleTimeString();
    
    if (message.role === 'user') {
      return `
        <div class="message user-message">
          <div class="message-header">
            <span class="message-role">You</span>
            <span class="message-time">${time}</span>
          </div>
          <div class="message-content">${this.escapeHtml(message.content)}</div>
        </div>
      `;
    }

    if (message.role === 'assistant') {
      let html = `
        <div class="message assistant-message">
          <div class="message-header">
            <span class="message-role">Assistant</span>
            <span class="message-time">${time}</span>
          </div>
      `;

      if (message.thinking) {
        html += `
          <details class="thinking-section">
            <summary>View thinking process</summary>
            <div class="thinking-content">${marked(message.thinking)}</div>
          </details>
        `;
      }

      if (message.content) {
        html += `<div class="message-content">${marked(message.content)}</div>`;
      } else {
        html += '<div class="message-content thinking">Thinking...</div>';
      }

      html += '</div>';
      return html;
    }

    return '';
  }

  private static escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  static setupMarkdown() {
    const renderer = new marked.Renderer();
    
    // Custom code rendering with syntax highlighting
    renderer.code = function({ text, lang }: { text: string; lang?: string; escaped?: boolean }) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          const highlighted = hljs.highlight(text, { language: lang }).value;
          return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`;
        } catch (e) {
          console.error('Highlight error:', e);
        }
      }
      return `<pre><code>${text}</code></pre>`;
    };

    marked.setOptions({
      renderer,
      breaks: true,
      gfm: true
    });
  }
}