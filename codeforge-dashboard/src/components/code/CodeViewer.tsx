import React, { useState } from 'react';
import { FileTree } from './FileTree';
import { MonacoEditor } from './MonacoEditor';
import type { FileNode } from '@/types';
import { cn } from '@/lib/utils';

interface CodeViewerProps {
  files: FileNode[];
  initialFile?: FileNode;
}

export function CodeViewer({ files, initialFile }: CodeViewerProps) {
  const [activeFile, setActiveFile] = useState<FileNode | null>(initialFile || files[0] || null);
  const [openFiles, setOpenFiles] = useState<FileNode[]>(initialFile ? [initialFile] : files.slice(0, 1));
  const [wordWrap, setWordWrap] = useState(false);

  const handleSelectFile = (node: FileNode) => {
    if (!openFiles.find((f) => f.path === node.path)) {
      setOpenFiles((prev) => [...prev, node]);
    }
    setActiveFile(node);
  };

  const handleCloseFile = (e: React.MouseEvent, path: string) => {
    e.stopPropagation();
    const newOpenFiles = openFiles.filter((f) => f.path !== path);
    setOpenFiles(newOpenFiles);
    
    if (activeFile?.path === path) {
      setActiveFile(newOpenFiles[newOpenFiles.length - 1] || null);
    }
  };

  return (
    <div className="flex h-full">
      {/* File Tree */}
      <div className="w-60 flex-shrink-0">
        <FileTree
          files={files}
          activePath={activeFile?.path}
          onSelectFile={handleSelectFile}
        />
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Tabs */}
        {openFiles.length > 0 && (
          <div className="flex items-center border-b border-slate-800 bg-slate-900 overflow-x-auto">
            {openFiles.map((file) => (
              <div
                key={file.path}
                onClick={() => setActiveFile(file)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 text-sm border-r border-slate-800 cursor-pointer hover:bg-slate-800 transition-colors',
                  activeFile?.path === file.path ? 'bg-slate-800 text-white' : 'text-slate-400'
                )}
              >
                <span>{file.name}</span>
                <button
                  onClick={(e) => handleCloseFile(e, file.path)}
                  className="hover:text-white transition-colors"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Editor */}
        <div className="flex-1 relative">
          {activeFile ? (
            <MonacoEditor
              value={activeFile.content}
              language={activeFile.language}
              filename={activeFile.name}
              readOnly={true}
              wordWrap={wordWrap}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              Select a file to view
            </div>
          )}
        </div>

        {/* Action Bar */}
        {activeFile && (
          <div className="flex items-center justify-between p-2 border-t border-slate-800 bg-slate-900">
            <span className="text-xs text-slate-400">{activeFile.path}</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setWordWrap(!wordWrap)}
                className={cn(
                  'px-2 py-1 text-xs rounded transition-colors',
                  wordWrap ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                )}
              >
                Word Wrap
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(activeFile.content)}
                className="px-2 py-1 text-xs bg-slate-800 text-slate-400 rounded hover:bg-slate-700 transition-colors"
              >
                Copy
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
