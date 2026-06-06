const SENSITIVE_KEY_MARKERS = [
  'authorization',
  'token',
  'password',
  'secret',
  'api_key',
  'ocr_text',
  'raw_ocr_text',
  'label_text',
  'medication_instruction',
  'signed_url',
  'upload_url',
  'read_url',
];

type ErrorContext = Record<string, unknown>;

export type ClientErrorReporter = {
  reportError: (error: Error, context?: ErrorContext) => void;
};

export class NoopClientErrorReporter implements ClientErrorReporter {
  reportError(): void {
    return undefined;
  }
}

export class SentryHttpErrorReporter implements ClientErrorReporter {
  private endpoint: string;
  private dsn: string;

  constructor(dsn: string) {
    this.dsn = dsn;
    this.endpoint = sentryEnvelopeEndpoint(dsn);
  }

  reportError(error: Error, context: ErrorContext = {}): void {
    const eventId = randomEventId();
    const event = {
      event_id: eventId,
      timestamp: new Date().toISOString(),
      platform: 'javascript',
      level: 'error',
      exception: {
        values: [
          {
            type: error.name,
            value: 'Client error captured',
          },
        ],
      },
      contexts: {
        medguide: redactClientContext(context),
      },
    };
    const envelope = [
      JSON.stringify({ event_id: eventId, dsn: this.dsn, sent_at: new Date().toISOString() }),
      JSON.stringify({ type: 'event' }),
      JSON.stringify(event),
    ].join('\n');

    void fetch(this.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-sentry-envelope' },
      body: envelope,
    }).catch(() => undefined);
  }
}

export function createClientErrorReporter(): ClientErrorReporter {
  const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
  if (!dsn) {
    return new NoopClientErrorReporter();
  }

  try {
    return new SentryHttpErrorReporter(dsn);
  } catch {
    return new NoopClientErrorReporter();
  }
}

export const clientErrorReporter = createClientErrorReporter();

export function reportClientError(error: Error, context?: ErrorContext): void {
  clientErrorReporter.reportError(error, context);
}

export function redactClientContext(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(item => redactClientContext(item));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        isSensitiveKey(key) ? '[REDACTED]' : redactClientContext(item),
      ]),
    );
  }
  if (typeof value === 'string' && value.toLowerCase().startsWith('bearer ')) {
    return '[REDACTED]';
  }
  return value;
}

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return SENSITIVE_KEY_MARKERS.some(marker => normalized.includes(marker));
}

function sentryEnvelopeEndpoint(dsn: string): string {
  const url = new URL(dsn);
  const projectId = url.pathname.replace(/^\/+/, '').split('/').at(-1);
  if (!projectId) {
    throw new Error('Invalid Sentry DSN');
  }
  return `${url.protocol}//${url.host}/api/${projectId}/envelope/`;
}

function randomEventId(): string {
  return Math.random().toString(16).slice(2).padEnd(32, '0').slice(0, 32);
}
