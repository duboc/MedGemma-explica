/**
 * Shared markdown rendering utilities.
 *
 * Handles MedGemma output patterns including:
 * - Standard markdown: ## headings, **bold**, *italic*, `code`
 * - Bullet lists (-, *), numbered lists (1.)
 * - Indented sub-lists
 * - Bold sub-headings like "**Category:**"
 * - Blockquotes (>)
 * - <thought> blocks (stripped)
 * - <end_of_turn> markers (stripped)
 */

/** Escape HTML entities and convert inline markdown to HTML spans. */
export function parseInlineMarkdown(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

/** Strip MedGemma artifacts like <thought> blocks and <end_of_turn>. */
function cleanMedGemmaOutput(text: string): string {
  // Remove <thought>...</thought> blocks
  let cleaned = text.replace(/<thought>[\s\S]*?<\/thought>/gi, "");
  // Handle unclosed <thought> — take text after "Final Answer:" if present
  if (cleaned.trim().toLowerCase().startsWith("<thought>")) {
    const fa = cleaned.indexOf("Final Answer:");
    if (fa !== -1) {
      cleaned = cleaned.slice(fa + "Final Answer:".length);
    }
  }
  // Remove <end_of_turn>
  cleaned = cleaned.replace(/<end_of_turn>/g, "");
  return cleaned.trim();
}

/** Full markdown-to-HTML renderer for chat messages and general content. */
export function renderMarkdownToHtml(rawText: string): string {
  const text = cleanMedGemmaOutput(rawText);
  const lines = text.split("\n");
  const out: string[] = [];
  let inList = false;
  let listType: "ul" | "ol" = "ul";

  const closeList = () => {
    if (inList) {
      out.push(`</${listType}>`);
      inList = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();

    // Empty line
    if (!line) {
      closeList();
      out.push("<br/>");
      continue;
    }

    // Headings: # / ## / ###
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      closeList();
      const level = headingMatch[1].length;
      const tag = level === 1 ? "h3" : "h4";
      out.push(`<${tag} class="md-heading md-h${level}">${parseInlineMarkdown(headingMatch[2])}</${tag}>`);
      continue;
    }

    // Bold line acting as sub-heading: "**Something:**" or "**Something**"
    const boldLine = line.match(/^\*\*(.+?)\*\*:?\s*$/);
    if (boldLine && !line.startsWith("- ") && !line.startsWith("* ")) {
      closeList();
      out.push(`<div class="md-subheading"><strong>${parseInlineMarkdown(boldLine[1])}</strong></div>`);
      continue;
    }

    // Bullet list: - item or * item (with possible indentation)
    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!inList || listType !== "ul") {
        closeList();
        out.push("<ul>");
        inList = true;
        listType = "ul";
      }
      out.push(`<li>${parseInlineMarkdown(bullet[1])}</li>`);
      continue;
    }

    // Numbered list: 1. item
    const num = line.match(/^\d+[.)]\s+(.+)$/);
    if (num) {
      if (!inList || listType !== "ol") {
        closeList();
        out.push("<ol>");
        inList = true;
        listType = "ol";
      }
      out.push(`<li>${parseInlineMarkdown(num[1])}</li>`);
      continue;
    }

    // Blockquote
    if (line.startsWith(">")) {
      closeList();
      const content = line.replace(/^>\s*/, "");
      out.push(`<blockquote class="md-blockquote">${parseInlineMarkdown(content)}</blockquote>`);
      continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(line)) {
      closeList();
      out.push('<hr class="md-hr"/>');
      continue;
    }

    // Regular paragraph
    closeList();
    out.push(`<p class="md-paragraph">${parseInlineMarkdown(line)}</p>`);
  }
  closeList();
  return out.join("\n");
}

