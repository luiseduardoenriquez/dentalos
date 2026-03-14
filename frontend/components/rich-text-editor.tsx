"use client";

import * as React from "react";
import { useEditor, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  AlignLeft,
  AlignCenter,
  AlignRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  editable?: boolean;
  placeholder?: string;
  minHeight?: string;
  className?: string;
  /** Called when the editor instance is ready — use for external integrations like variable insertion */
  onEditorReady?: (editor: Editor) => void;
}

// ─── Toolbar Button ──────────────────────────────────────────────────────────

interface ToolbarButtonProps {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  onClick: () => void;
}

function ToolbarButton({ icon: Icon, label, active, onClick }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      // Use onMouseDown + preventDefault to avoid stealing focus from editor
      onMouseDown={(e) => {
        e.preventDefault();
        onClick();
      }}
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-md transition-colors",
        "hover:bg-[hsl(var(--muted))]",
        active
          ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"
          : "text-[hsl(var(--muted-foreground))]",
      )}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

// ─── Toolbar ─────────────────────────────────────────────────────────────────

function Toolbar({ editor }: { editor: Editor }) {
  return (
    <div className="flex flex-wrap items-center gap-0.5 border-b border-[hsl(var(--border))] px-2 py-1.5">
      <ToolbarButton
        icon={Bold}
        label="Negrita"
        active={editor.isActive("bold")}
        onClick={() => editor.chain().focus().toggleBold().run()}
      />
      <ToolbarButton
        icon={Italic}
        label="Cursiva"
        active={editor.isActive("italic")}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      />
      <ToolbarButton
        icon={UnderlineIcon}
        label="Subrayado"
        active={editor.isActive("underline")}
        onClick={() => editor.chain().focus().toggleUnderline().run()}
      />

      <div className="mx-1 h-5 w-px bg-[hsl(var(--border))]" aria-hidden />

      <ToolbarButton
        icon={Heading2}
        label="Título 2"
        active={editor.isActive("heading", { level: 2 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      />
      <ToolbarButton
        icon={Heading3}
        label="Título 3"
        active={editor.isActive("heading", { level: 3 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
      />

      <div className="mx-1 h-5 w-px bg-[hsl(var(--border))]" aria-hidden />

      <ToolbarButton
        icon={List}
        label="Lista con viñetas"
        active={editor.isActive("bulletList")}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      />
      <ToolbarButton
        icon={ListOrdered}
        label="Lista numerada"
        active={editor.isActive("orderedList")}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      />

      <div className="mx-1 h-5 w-px bg-[hsl(var(--border))]" aria-hidden />

      <ToolbarButton
        icon={AlignLeft}
        label="Alinear izquierda"
        active={editor.isActive({ textAlign: "left" })}
        onClick={() => editor.chain().focus().setTextAlign("left").run()}
      />
      <ToolbarButton
        icon={AlignCenter}
        label="Centrar"
        active={editor.isActive({ textAlign: "center" })}
        onClick={() => editor.chain().focus().setTextAlign("center").run()}
      />
      <ToolbarButton
        icon={AlignRight}
        label="Alinear derecha"
        active={editor.isActive({ textAlign: "right" })}
        onClick={() => editor.chain().focus().setTextAlign("right").run()}
      />
    </div>
  );
}

// ─── RichTextEditor ──────────────────────────────────────────────────────────

/**
 * Reusable rich text editor built on TipTap.
 *
 * @example
 * <RichTextEditor
 *   content={html}
 *   onChange={setHtml}
 *   placeholder="Escribe aquí..."
 *   minHeight="200px"
 * />
 */
export function RichTextEditor({
  content,
  onChange,
  editable = true,
  placeholder,
  minHeight = "200px",
  className,
  onEditorReady,
}: RichTextEditorProps) {
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
      }),
      Underline,
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
    ],
    content,
    editable,
    editorProps: {
      attributes: {
        class: cn(
          "prose prose-sm max-w-none focus:outline-none",
          "prose-headings:font-semibold prose-headings:text-foreground",
          "prose-p:text-foreground/90 prose-p:leading-relaxed prose-p:my-1",
          "prose-ul:text-foreground/90 prose-ol:text-foreground/90",
          "prose-strong:text-foreground prose-strong:font-semibold",
          "dark:prose-invert",
        ),
        style: `min-height: ${minHeight}`,
      },
    },
    onUpdate: ({ editor: e }) => {
      onChange(e.getHTML());
    },
  });

  // Notify parent when editor is ready
  React.useEffect(() => {
    if (editor && onEditorReady) {
      onEditorReady(editor);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor]);

  // Sync content from parent when it changes externally
  React.useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
    // Only sync on content prop changes, not on editor updates
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content]);

  if (!editor) return null;

  return (
    <div
      className={cn(
        "rounded-md border border-[hsl(var(--input))] bg-transparent shadow-sm",
        "focus-within:ring-1 focus-within:ring-primary-600",
        !editable && "opacity-60 cursor-not-allowed",
        className,
      )}
    >
      {editable && <Toolbar editor={editor} />}
      <div className="px-3 py-2">
        <EditorContent
          editor={editor}
          className={cn(
            "tiptap-editor",
            placeholder && "[&_.tiptap.ProseMirror_p.is-editor-empty:first-child::before]:content-[attr(data-placeholder)]",
          )}
        />
      </div>
    </div>
  );
}

/**
 * Inserts text at the current cursor position in a TipTap editor.
 * Used for variable insertion (e.g., {{patient_name}}).
 */
export function insertTextAtCursor(editor: Editor | null, text: string) {
  if (!editor) return;
  editor.chain().focus().insertContent(text).run();
}
