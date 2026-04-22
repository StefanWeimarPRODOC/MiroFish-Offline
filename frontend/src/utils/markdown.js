import DOMPurify from 'dompurify'

/**
 * Render markdown content to sanitized HTML.
 * Uses DOMPurify to prevent XSS from LLM-generated content.
 */
export function renderMarkdown(content) {
  if (!content) return ''

  // Remove leading level-2 headings (## xxx), since section title is already shown in parent
  let processedContent = content.replace(/^##\s+.+\n+/, '')

  // Process code blocks
  let html = processedContent.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')

  // Process inline code
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // Process headings
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')

  // Process blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')

  // Process lists - supports sub-lists
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-li" data-level="${level}">${text}</li>`
  })
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-oli" data-level="${level}">${text}</li>`
  })

  // Wrap unordered lists
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  // Wrap ordered lists
  html = html.replace(/(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g, '<ol class="md-ol">$&</ol>')

  // Clean whitespace between list items
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">')
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">')
  html = html.replace(/\s+<\/ul>/g, '</ul>')
  html = html.replace(/\s+<\/ol>/g, '</ol>')

  // Process bold and italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')

  // Process horizontal rules
  html = html.replace(/^---$/gm, '<hr class="md-hr">')

  // Process line breaks - empty lines become paragraph separators, single newline becomes <br>
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')

  // Wrap in paragraphs
  html = '<p class="md-p">' + html + '</p>'

  // Clean empty paragraphs
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p">(<h[2-5])/g, '$1')
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, '$1')
  html = html.replace(/<p class="md-p">(<ul|<ol|<blockquote|<pre|<hr)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')
  // Clean <br> tags around block elements
  html = html.replace(/<br>\s*(<ul|<ol|<blockquote)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>)\s*<br>/g, '$1')
  // Clean <p><br> before block elements (caused by extra blank lines)
  html = html.replace(/<p class="md-p">(<br>\s*)+(<ul|<ol|<blockquote|<pre|<hr)/g, '$2')
  // Clean consecutive <br> tags
  html = html.replace(/(<br>\s*){2,}/g, '<br>')
  // Clean <br> after block elements before paragraph start tag
  html = html.replace(/(<\/ol>|<\/ul>|<\/blockquote>)<br>(<p|<div)/g, '$1$2')

  // Fix numbering for non-consecutive ordered lists
  const tokens = html.split(/(<ol class="md-ol">(?:<li class="md-oli"[^>]*>[\s\S]*?<\/li>)+<\/ol>)/g)
  let olCounter = 0
  let inSequence = false
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].startsWith('<ol class="md-ol">')) {
      const liCount = (tokens[i].match(/<li class="md-oli"/g) || []).length
      if (liCount === 1) {
        olCounter++
        if (olCounter > 1) {
          tokens[i] = tokens[i].replace('<ol class="md-ol">', `<ol class="md-ol" start="${olCounter}">`)
        }
        inSequence = true
      } else {
        olCounter = 0
        inSequence = false
      }
    } else if (inSequence) {
      if (/<h[2-5]/.test(tokens[i])) {
        olCounter = 0
        inSequence = false
      }
    }
  }
  html = tokens.join('')

  return DOMPurify.sanitize(html)
}

/**
 * Sanitize HTML content for use with innerHTML in render functions.
 * Applies DOMPurify to arbitrary HTML strings (e.g. bold + br transforms).
 */
export function sanitizeHtml(html) {
  return DOMPurify.sanitize(html)
}
