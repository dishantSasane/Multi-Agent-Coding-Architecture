import { useAppStore } from '@/store/appStore';

const inputClass =
  'h-10 w-full rounded-lg border border-input bg-background px-4 text-sm focus:border-accent focus:outline-none';

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}

const Section = ({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) => (
  <section className="space-y-4 rounded-lg border bg-card p-6 shadow-card">
    <div>
      <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">{title}</h2>
      {hint && <p className="mt-2 text-xs text-muted-foreground">{hint}</p>}
    </div>
    {children}
  </section>
);

export function SettingsPage() {
  const { settings, updateSettings } = useAppStore();

  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Section title="Backend">
        <Field id="backend-url" label="Backend URL">
          <input
            id="backend-url"
            type="text"
            value={settings.backend_url}
            onChange={(e) => updateSettings({ backend_url: e.target.value })}
            className={inputClass}
          />
        </Field>
      </Section>

      <Section title="API keys" hint="Stored in this browser only. They are not sent to the backend.">
        {(['anthropic', 'openai', 'qwen', 'kimi', 'gemini'] as const).map((provider) => (
          <Field key={provider} id={`key-${provider}`} label={`${provider[0].toUpperCase()}${provider.slice(1)} API key`}>
            <input
              id={`key-${provider}`}
              type="password"
              autoComplete="off"
              value={settings.api_keys[provider] ?? ''}
              onChange={(e) => updateSettings({ api_keys: { ...settings.api_keys, [provider]: e.target.value } })}
              className={`${inputClass} font-mono`}
            />
          </Field>
        ))}
      </Section>

      <Section title="Sandbox">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="sandbox-memory" label="Memory limit">
            <input
              id="sandbox-memory"
              type="text"
              value={settings.sandbox_memory_limit}
              onChange={(e) => updateSettings({ sandbox_memory_limit: e.target.value })}
              className={inputClass}
            />
          </Field>
          <Field id="sandbox-timeout" label="Timeout (s)">
            <input
              id="sandbox-timeout"
              type="number"
              value={settings.sandbox_timeout}
              onChange={(e) => updateSettings({ sandbox_timeout: Number(e.target.value) })}
              className={inputClass}
            />
          </Field>
        </div>
      </Section>
    </div>
  );
}
