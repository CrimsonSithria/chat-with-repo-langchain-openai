import React from 'react';
import Editor from '@monaco-editor/react';
import { Box } from '@mui/material';

const CodeEditor: React.FC = () => {
  const handleEditorDidMount = (editor: any) => {
    // You can add editor instance related setup here
    editor.focus();
  };

  return (
    <Box sx={{ flexGrow: 1, position: 'relative' }}>
      <Editor
        height="100%"
        defaultLanguage="typescript"
        defaultValue="// Start typing your code here"
        theme="vs-dark"
        options={{
          minimap: { enabled: true },
          fontSize: 14,
          wordWrap: 'on',
          automaticLayout: true,
          scrollBeyondLastLine: false,
          renderWhitespace: 'selection',
          lineNumbers: 'on',
          glyphMargin: true,
          folding: true,
          lineDecorationsWidth: 0,
          lineNumbersMinChars: 3,
        }}
        onMount={handleEditorDidMount}
      />
    </Box>
  );
};

export default CodeEditor; 