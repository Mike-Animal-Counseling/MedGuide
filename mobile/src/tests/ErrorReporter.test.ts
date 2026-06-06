import {
  NoopClientErrorReporter,
  SentryHttpErrorReporter,
  createClientErrorReporter,
  redactClientContext,
} from '../observability/errorReporter';

describe('client error reporter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    globalThis.fetch = jest.fn(async () => ({ ok: true })) as jest.Mock;
    delete process.env.EXPO_PUBLIC_SENTRY_DSN;
  });

  it('redacts medication and credential fields before reporting', () => {
    const redacted = redactClientContext({
      screen: 'ScanLabel',
      ocr_text: 'raw medication label text',
      nested: {
        upload_url: 'https://storage.example/upload',
        authorization: 'Bearer access-token',
      },
    });

    expect(redacted).toEqual({
      screen: 'ScanLabel',
      ocr_text: '[REDACTED]',
      nested: {
        upload_url: '[REDACTED]',
        authorization: '[REDACTED]',
      },
    });
  });

  it('uses no-op reporting when Sentry DSN is not configured', () => {
    expect(createClientErrorReporter()).toBeInstanceOf(NoopClientErrorReporter);
  });

  it('uses real Sentry HTTP reporting when Sentry DSN is configured', () => {
    process.env.EXPO_PUBLIC_SENTRY_DSN = 'https://public@example.ingest.sentry.io/1';

    expect(createClientErrorReporter()).toBeInstanceOf(SentryHttpErrorReporter);
  });

  it('sends a redacted Sentry envelope without raw OCR text', () => {
    const reporter = new SentryHttpErrorReporter('https://public@example.ingest.sentry.io/1');

    reporter.reportError(new Error('raw medication label text from error'), {
      ocr_text: 'raw medication label text',
      screen: 'ScanLabel',
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'https://example.ingest.sentry.io/api/1/envelope/',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/x-sentry-envelope' },
        body: expect.any(String),
      }),
    );
    const [, options] = (globalThis.fetch as jest.Mock).mock.calls[0];
    expect(options.body).toContain('[REDACTED]');
    expect(options.body).not.toContain('raw medication label text');
    expect(options.body).toContain('Client error captured');
  });
});
