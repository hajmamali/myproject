/**
 * Command Palette Component
 * Global command execution interface
 */

import { useState, useCallback, createContext, useContext } from 'react';

interface Command {
  id: string;
  title: string;
  description?: string;
  execute: () => void;
  category?: string;
}

interface CommandPaletteContextType {
  isOpen: boolean;
  open: () => void;
  close: () => void;
}

const CommandPaletteContext = createContext<CommandPaletteContextType | undefined>(undefined);

export function useCommandPalette() {
  const context = useContext(CommandPaletteContext);
  if (!context) {
    throw new Error('useCommandPalette must be used within CommandPaletteProvider');
  }
  return context;
}

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => {
    setIsOpen(false);
    setSearch('');
  }, []);

  const commands: Command[] = [
    {
      id: 'search',
      title: 'Search',
      description: 'Search legal documents',
      category: 'Search',
      execute: () => {
        close();
        console.log('Opening search');
      },
    },
    {
      id: 'upload',
      title: 'Upload Document',
      description: 'Upload a new document',
      category: 'Document',
      execute: () => {
        close();
        console.log('Opening upload');
      },
    },
  ];

  const filtered = search
    ? commands.filter(
        (cmd) =>
          cmd.title.toLowerCase().includes(search.toLowerCase()) ||
          cmd.description?.toLowerCase().includes(search.toLowerCase())
      )
    : commands;

  if (!isOpen) {
    return null;
  }

  return (
    <CommandPaletteContext.Provider value={{ isOpen, open, close }}>
      <div className="fixed inset-0 z-50 bg-black/50 flex items-start justify-center pt-16">
        <div className="w-full max-w-xl bg-white rounded-lg shadow-xl">
          <input
            autoFocus
            type="text"
            placeholder="Type a command..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-3 border-b border-slate-200 focus:outline-none"
          />
          <div className="max-h-96 overflow-y-auto">
            {filtered.map((cmd) => (
              <button
                key={cmd.id}
                onClick={cmd.execute}
                className="w-full px-4 py-3 text-left hover:bg-slate-50 border-b border-slate-100 last:border-b-0"
              >
                <div className="font-medium text-slate-900">{cmd.title}</div>
                {cmd.description && <div className="text-sm text-slate-600">{cmd.description}</div>}
              </button>
            ))}
          </div>
        </div>
      </div>
    </CommandPaletteContext.Provider>
  );
}
