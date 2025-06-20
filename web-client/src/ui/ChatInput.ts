export class ChatInput {
  private element: HTMLTextAreaElement;
  private sendButton: HTMLButtonElement;
  private onSend: (message: string) => void;

  constructor(
    element: HTMLTextAreaElement,
    sendButton: HTMLButtonElement,
    onSend: (message: string) => void
  ) {
    this.element = element;
    this.sendButton = sendButton;
    this.onSend = onSend;
    this.setupEventListeners();
  }

  private setupEventListeners() {
    this.element.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.send();
      }
    });

    this.sendButton.addEventListener('click', () => this.send());

    // Auto-resize textarea
    this.element.addEventListener('input', () => {
      this.element.style.height = 'auto';
      this.element.style.height = this.element.scrollHeight + 'px';
    });
  }

  private send() {
    const message = this.element.value.trim();
    if (message) {
      this.onSend(message);
      this.clear();
    }
  }

  clear() {
    this.element.value = '';
    this.element.style.height = 'auto';
  }

  focus() {
    this.element.focus();
  }

  setEnabled(enabled: boolean) {
    this.element.disabled = !enabled;
    this.sendButton.disabled = !enabled;
  }
}