/**
 * Screen 4: Final consultation report display.
 * Renders the structured markdown report with a disclaimer.
 *
 * @param {{
 *   report: string,
 *   onNewConsultation: () => void,
 * }} props
 */
export default function FinalReport({ report, onNewConsultation }) {

  /**
   * Simple markdown-to-HTML renderer for the report.
   * Handles: headings, bold, lists, horizontal rules, paragraphs.
   */
  function renderMarkdown(text) {
    if (!text) return null;

    const lines = text.split('\n');
    const elements = [];
    let inList = false;
    let listItems = [];
    let key = 0;

    const flushList = () => {
      if (listItems.length > 0) {
        elements.push(
          <ul key={`list-${key++}`} style={{ paddingLeft: '1.5rem', marginBottom: '0.75rem' }}>
            {listItems.map((item, i) => (
              <li key={i} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
            ))}
          </ul>
        );
        listItems = [];
        inList = false;
      }
    };

    const formatInline = (line) => {
      return line
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>');
    };

    for (const line of lines) {
      const trimmed = line.trim();

      // Empty line
      if (!trimmed) {
        flushList();
        continue;
      }

      // Horizontal rule
      if (/^---+$/.test(trimmed) || /^===+$/.test(trimmed)) {
        flushList();
        elements.push(<hr key={`hr-${key++}`} />);
        continue;
      }

      // Headings
      if (trimmed.startsWith('# ')) {
        flushList();
        elements.push(
          <h1 key={`h1-${key++}`} dangerouslySetInnerHTML={{ __html: formatInline(trimmed.slice(2)) }} />
        );
        continue;
      }
      if (trimmed.startsWith('## ')) {
        flushList();
        elements.push(
          <h2 key={`h2-${key++}`} dangerouslySetInnerHTML={{ __html: formatInline(trimmed.slice(3)) }} />
        );
        continue;
      }
      if (trimmed.startsWith('### ')) {
        flushList();
        elements.push(
          <h3 key={`h3-${key++}`} dangerouslySetInnerHTML={{ __html: formatInline(trimmed.slice(4)) }} />
        );
        continue;
      }

      // List items
      if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || /^\d+\.\s/.test(trimmed)) {
        inList = true;
        const content = trimmed.replace(/^[-•]\s/, '').replace(/^\d+\.\s/, '');
        listItems.push(content);
        continue;
      }

      // Regular paragraph
      flushList();
      elements.push(
        <p key={`p-${key++}`} dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }} />
      );
    }

    flushList();
    return elements;
  }

  return (
    <div className="screen-enter">
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-6)' }}>
          <h2 className="section-title" style={{ marginBottom: 0 }}>
            📄 Rapport Final
          </h2>
          <span className="status-badge status-badge-complete">
            ✓ Terminé
          </span>
        </div>

        {/* Report Content */}
        <div className="report-container">
          {renderMarkdown(report)}
        </div>

        {/* Disclaimer */}
        <div className="report-disclaimer">
          ⚕️ <strong>AVERTISSEMENT</strong> : Ce système ne remplace pas une consultation médicale.
          Ce rapport est une orientation clinique préliminaire à des fins académiques uniquement.
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-6)' }}>
          <button
            className="btn btn-primary btn-lg btn-block"
            onClick={onNewConsultation}
            id="new-consultation-btn"
          >
            🩺 Nouvelle Consultation
          </button>
        </div>
      </div>
    </div>
  );
}
