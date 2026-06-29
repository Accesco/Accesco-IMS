import Editor from '@monaco-editor/react';

interface JsonEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  height?: string;
  isDark: boolean;
  language?: string;
}

export default function JsonEditor({
  value,
  onChange,
  readOnly = false,
  height = '200px',
  isDark,
  language = 'json',
}: JsonEditorProps) {
  return (
    <div className="overflow-hidden rounded-md border border-edge">
      <Editor
        height={height}
        language={language}
        value={value}
        onChange={(val) => onChange(val ?? '')}
        theme={isDark ? 'vs-dark' : 'light'}
        options={{
          readOnly,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 12,
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
          lineNumbers: 'on',
          lineNumbersMinChars: 3,
          glyphMargin: false,
          folding: true,
          wordWrap: 'on',
          automaticLayout: true,
          tabSize: 2,
          renderLineHighlight: 'none',
          overviewRulerLanes: 0,
          hideCursorInOverviewRuler: true,
          overviewRulerBorder: false,
          scrollbar: {
            verticalScrollbarSize: 6,
            horizontalScrollbarSize: 6,
          },
          padding: { top: 8, bottom: 8 },
        }}
      />
    </div>
  );
}
