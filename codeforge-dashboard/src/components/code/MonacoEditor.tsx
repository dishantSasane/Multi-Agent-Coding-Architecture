import React, { useState, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { cn } from '@/lib/utils';
import { getLanguageFromFilename } from '@/lib/utils';

interface MonacoEditorProps {
  value: string;
  language?: string;
  filename?: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
  height?: string | number;
  fontSize?: number;
  wordWrap?: boolean;
  className?: string;
}

export function MonacoEditor({
  value,
  language,
  filename,
  readOnly = false,
  onChange,
  height = '100%',
  fontSize = 14,
  wordWrap = false,
  className = '',
}: MonacoEditorProps) {
  const [editorInstance, setEditorInstance] = useState<Parameters<OnMount>[0] | null>(null);
  
  const detectedLanguage = language || (filename ? getLanguageFromFilename(filename) : 'text');

  const handleEditorMount: OnMount = (editor) => {
    setEditorInstance(editor);
  };

  useEffect(() => {
    if (editorInstance) {
      editorInstance.updateOptions({
        wordWrap: wordWrap ? 'on' : 'off',
        fontSize,
      });
    }
  }, [editorInstance, wordWrap, fontSize]);

  return (
    <div className={cn('w-full h-full', className)}>
      <Editor
        height={typeof height === 'number' ? `${height}px` : height}
        language={detectedLanguage}
        value={value}
        onChange={(newValue) => onChange?.(newValue || '')}
        onMount={handleEditorMount}
        theme="vs-dark"
        options={{
          readOnly,
          minimap: { enabled: true },
          lineNumbers: 'on',
          folding: true,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          detectIndentation: true,
          formatOnPaste: true,
          quickSuggestions: {
            other: true,
            comments: true,
            strings: true,
          },
        }}
      />
    </div>
  );
}
