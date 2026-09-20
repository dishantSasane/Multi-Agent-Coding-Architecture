import { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { Download } from 'lucide-react';
import type { CodeFile } from '@/types';
import { Button } from '@/components/shared/Button';
import { downloadBlob } from '@/lib/utils';

/** Multi-file viewer. Radix gives roving arrow-key focus and correct tab roles. */
export function FileTabs({ files }: { files: CodeFile[] }) {
  const [active, setActive] = useState(files[0]?.filename);

  const downloadZip = async () => {
    const JSZip = (await import('jszip')).default; // loaded only when asked for
    const zip = new JSZip();
    files.forEach((f) => zip.file(f.filename, f.content));
    downloadBlob(await zip.generateAsync({ type: 'blob' }), 'generated_project.zip');
  };

  return (
    <Tabs.Root value={active} onValueChange={setActive} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Tabs.List aria-label="Generated files" className="flex max-w-full gap-2 overflow-x-auto">
          {files.map((f) => (
            <Tabs.Trigger
              key={f.filename}
              value={f.filename}
              className="h-8 shrink-0 rounded-lg px-4 font-mono text-xs text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary hover:text-foreground active:bg-secondary/70 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              {f.filename}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        <Button variant="secondary" size="sm" onClick={downloadZip}>
          <Download className="h-4 w-4" aria-hidden="true" />
          ZIP
        </Button>
      </div>

      {files.map((f) => (
        <Tabs.Content key={f.filename} value={f.filename} className="space-y-2">
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => downloadBlob(new Blob([f.content], { type: 'text/plain' }), f.filename)}
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Download {f.filename}
            </Button>
          </div>
          <pre
            tabIndex={0}
            aria-label={`${f.filename} source`}
            className="max-h-[640px] min-h-[320px] overflow-auto rounded-lg bg-code p-4 text-sm text-code-foreground"
          >
            <code>{f.content}</code>
          </pre>
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
