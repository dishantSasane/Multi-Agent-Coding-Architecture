import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Folder, FolderOpen, FileCode, ChevronRight, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FileNode } from '@/types';

interface FileTreeNodeProps {
  node: FileNode;
  depth: number;
  activePath?: string;
  onSelect: (node: FileNode) => void;
  expandedPaths: Set<string>;
  onToggle: (path: string) => void;
}

function FileTreeNode({
  node,
  depth,
  activePath,
  onSelect,
  expandedPaths,
  onToggle,
}: FileTreeNodeProps) {
  const isExpanded = expandedPaths.has(node.path);
  const isActive = activePath === node.path;
  const hasChildren = node.children && node.children.length > 0;

  const handleClick = () => {
    if (node.isDirectory) {
      onToggle(node.path);
    } else {
      onSelect(node);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={cn(
          'w-full flex items-center gap-2 px-2 py-1.5 text-sm hover:bg-slate-800 transition-colors',
          isActive && 'bg-indigo-600 hover:bg-indigo-700'
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren && (
          <span className="text-slate-500">
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </span>
        )}
        {!hasChildren && <span className="w-4" />}
        
        {node.isDirectory ? (
          isExpanded ? (
            <FolderOpen className="w-4 h-4 text-indigo-400" />
          ) : (
            <Folder className="w-4 h-4 text-indigo-400" />
          )
        ) : (
          <FileCode className="w-4 h-4 text-slate-400" />
        )}
        
        <span className="truncate">{node.name}</span>
      </button>

      {hasChildren && isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
        >
          {node.children!.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              activePath={activePath}
              onSelect={onSelect}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
            />
          ))}
        </motion.div>
      )}
    </div>
  );
}

interface FileTreeProps {
  files: FileNode[];
  activePath?: string;
  onSelectFile: (node: FileNode) => void;
}

export function FileTree({ files, activePath, onSelectFile }: FileTreeProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set(['']));

  const handleToggle = (path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  // Expand root by default
  const rootFiles: FileNode = {
    name: 'root',
    path: '',
    content: '',
    language: '',
    isDirectory: true,
    children: files,
  };

  return (
    <div className="h-full overflow-y-auto bg-slate-900 border-r border-slate-800">
      <div className="p-3 border-b border-slate-800">
        <h3 className="font-semibold text-sm">Files</h3>
      </div>
      <FileTreeNode
        node={rootFiles}
        depth={-1}
        activePath={activePath}
        onSelect={onSelectFile}
        expandedPaths={expandedPaths}
        onToggle={handleToggle}
      />
    </div>
  );
}
