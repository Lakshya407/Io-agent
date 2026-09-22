/**
 * Minimal, dependency-free Markdown renderer.
 *
 * Supports the subset an agent actually produces: fenced code blocks (with a
 * copy button), headings, ordered/unordered lists, pipe tables, blockquotes,
 * inline bold/italic/code/links, plus plain line breaks. Output is built as
 * React elements — model content is untrusted, so it is never injected as raw
 * HTML.
 */
import { Check, Copy } from "lucide-react";
import { useState, type ReactNode } from "react";

const INLINE_RE =
  /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let remaining = text;
  let key = 0;
  while (remaining.length > 0) {
    const match = INLINE_RE.exec(remaining);
    if (!match) {
      nodes.push(remaining);
      break;
    }
    const index = match.index;
    if (index > 0) nodes.push(remaining.slice(0, index));
    if (match[2] !== undefined) {
      nodes.push(<strong key={`${keyPrefix}-${key++}`}>{match[2]}</strong>);
    } else if (match[3] !== undefined) {
      nodes.push(<em key={`${keyPrefix}-${key++}`}>{match[3]}</em>);
    } else if (match[4] !== undefined) {
      nodes.push(
        <code key={`${keyPrefix}-${key++}`} className="inline-code">
          {match[4]}
        </code>,
      );
    } else if (match[5] !== undefined) {
      nodes.push(
        <a
          key={`${keyPrefix}-${key++}`}
          href={match[6]}
          target="_blank"
          rel="noreferrer noopener"
        >
          {match[5]}
        </a>,
      );
    }
    remaining = remaining.slice(index + match[0].length);
  }
  return nodes;
}

function splitRow(row: string): string[] {
  return row
    .trim()
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((cell) => cell.trim());
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — the button simply does nothing */
    }
  };
  return (
    <div className="code-block">
      <div className="code-block-head">
        <span>{language || "code"}</span>
        <button type="button" onClick={copy} className="code-copy">
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}

export default function Markdown({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let key = 0;
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    // Fenced code block.
    const fence = line.match(/^```(\w*)\s*$/);
    if (fence) {
      const language = fence[1] || undefined;
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      index += 1; // consume the closing fence (if present)
      blocks.push(
        <CodeBlock
          code={codeLines.join("\n")}
          language={language}
          key={`code-${key++}`}
        />,
      );
      continue;
    }

    // Headings.
    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const Tag = (`h${level + 2}` as "h3" | "h4" | "h5");
      blocks.push(
        <Tag className="md-heading" key={`h-${key++}`}>
          {renderInline(heading[2], `h-${key}`)}
        </Tag>,
      );
      index += 1;
      continue;
    }

    // Blockquote.
    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(
        <blockquote className="md-quote" key={`q-${key++}`}>
          {renderInline(quoteLines.join(" "), `q-${key}`)}
        </blockquote>,
      );
      continue;
    }

    // Pipe table (header row followed by a separator row).
    if (line.includes("|") && index + 1 < lines.length) {
      const next = lines[index + 1];
      if (/^\s*\|?[\s:-]*-{3,}[\s:|-]*\|?\s*$/.test(next)) {
        const header = splitRow(line);
        index += 2;
        const body: string[][] = [];
        while (index < lines.length && lines[index].includes("|")) {
          body.push(splitRow(lines[index]));
          index += 1;
        }
        blocks.push(
          <div className="md-table-wrap" key={`t-${key++}`}>
            <table className="md-table">
              <thead>
                <tr>
                  {header.map((cell, cellIndex) => (
                    <th key={cellIndex}>{renderInline(cell, `th-${key}-${cellIndex}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>{renderInline(cell, `td-${key}-${cellIndex}`)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>,
        );
        continue;
      }
    }

    // Unordered list.
    if (/^\s*[-*+]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*+]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*+]\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ul className="md-list" key={`ul-${key++}`}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item, `li-${key}-${itemIndex}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list.
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ol className="md-list" key={`ol-${key++}`}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item, `li-${key}-${itemIndex}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // Paragraph (consecutive non-blank lines), otherwise a blank line is skipped.
    if (line.trim() === "") {
      index += 1;
      continue;
    }
    const paragraph: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() !== "" &&
      !/^```/.test(lines[index]) &&
      !/^(#{1,3})\s+/.test(lines[index]) &&
      !/^\s*[-*+]\s+/.test(lines[index]) &&
      !/^\s*\d+\.\s+/.test(lines[index]) &&
      !/^>\s?/.test(lines[index])
    ) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(
      <p key={`p-${key++}`}>
        {paragraph.map((text, paragraphIndex) => (
          <span key={paragraphIndex}>
            {renderInline(text, `p-${key}-${paragraphIndex}`)}
            {paragraphIndex < paragraph.length - 1 && <br />}
          </span>
        ))}
      </p>,
    );
  }

  return <div className="markdown">{blocks}</div>;
}
