import os


class MDToPDFConverter:
    def __init__(self, markdown_text: str, css_path: str | None = None):
        self.markdown_text = markdown_text
        self.css_path = css_path

        # Default CSS if no custom CSS is provided
        self.default_css = """
        /* Fluent UI Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;600;700&display=swap');

        @page {
          size: A4;
          margin: 2.5cm 2cm;
          @top-center {
            content: "Minh An đẹp trai";
            font-family: 'Segoe UI', 'Noto Sans JP', sans-serif;
            font-size: 10pt;
            font-weight: 600;
            color: #323130;
            border-bottom: 1px solid #0078d4;
            padding-bottom: 0.5cm;
          }
          @bottom-center {
            content: "Trang " counter(page) " / " counter(pages);
            font-family: 'Segoe UI', 'Noto Sans JP', sans-serif;
            font-size: 8pt;
            color: #605e5c;
            border-top: 1px solid #0078d4;
            padding-top: 0.5cm;
          }
        }

        /* Fluent UI Context7 Theme Variables */
        :root {
          /* Primary Colors */
          --primary-color: #0078d4;
          --primary-hover: #106ebe;
          --primary-active: #005a9e;

          /* Neutral Colors */
          --neutral-primary: #323130;
          --neutral-secondary: #605e5c;
          --neutral-tertiary: #a19f9d;
          --neutral-quaternary: #edebe9;
          --neutral-light: #faf9f8;
          --neutral-lighter: #ffffff;

          /* Text Colors */
          --text-color: #323130;
          --text-secondary: #605e5c;
          --text-disabled: #a19f9d;

          /* Background Colors */
          --bg-primary: #ffffff;
          --bg-secondary: #faf9f8;
          --bg-tertiary: #f3f2f1;

          /* Border Colors */
          --border-color: #edebe9;
          --border-hover: #c8c6c4;

          /* Accent Colors */
          --accent-color: #0078d4;
          --accent-hover: #106ebe;

          /* Status Colors */
          --success: #107c10;
          --warning: #ff8c00;
          --error: #d13438;

          /* Spacing (Fluent UI spacing scale) */
          --space-xs: 4px;
          --space-sm: 8px;
          --space-md: 12px;
          --space-lg: 16px;
          --space-xl: 20px;
          --space-xxl: 24px;
          --space-xxxl: 32px;
        }

        /* Fluent UI Body Typography */
        body {
          font-family: 'Segoe UI', 'Noto Sans JP', sans-serif;
          font-size: 12px;
          font-weight: 400;
          line-height: 1.5;
          color: var(--neutral-primary);
          background-color: var(--neutral-lighter);
          margin: 0;
          padding: var(--space-lg);
          max-width: 100%;
        }

        /* Fluent UI Header Typography */
        h1, h2, h3, h4, h5, h6 {
          font-family: 'Segoe UI', 'Noto Sans JP', sans-serif;
          font-weight: 600;
          line-height: 1.3;
          color: var(--neutral-primary);
          margin-top: var(--space-xxl);
          margin-bottom: var(--space-md);
        }

        h1 {
          font-size: 28px;
          font-weight: 700;
          text-align: center;
          margin-top: var(--space-lg);
          margin-bottom: var(--space-lg);
          padding-bottom: var(--space-md);
          border-bottom: 2px solid var(--primary-color);
          color: var(--primary-color);
        }

        h2 {
          font-size: 20px;
          font-weight: 600;
          margin-bottom: var(--space-sm);
          padding-bottom: var(--space-xs);
          border-bottom: 1px solid var(--primary-color);
          color: var(--primary-color);
        }

        h3 {
          font-size: 16px;
          font-weight: 600;
          color: var(--neutral-primary);
        }

        h4 {
          font-size: 14px;
          font-weight: 600;
          color: var(--neutral-primary);
        }

        h5 {
          font-size: 12px;
          font-weight: 600;
          color: var(--neutral-primary);
        }

        h6 {
          font-size: 11px;
          font-weight: 600;
          color: var(--neutral-primary);
        }

        /* Fluent UI Paragraph Typography */
        p {
          font-size: 12px;
          line-height: 1.5;
          color: var(--neutral-primary);
          margin-bottom: var(--space-md);
          text-align: left;
        }

        /* Fluent UI Lists */
        ul, ol {
          padding-left: var(--space-xxl);
          margin-bottom: var(--space-lg);
          margin-top: var(--space-sm);
        }

        li {
          font-size: 12px;
          line-height: 1.5;
          color: var(--neutral-primary);
          margin-bottom: var(--space-xs);
        }

        li > ul, li > ol {
          margin-top: var(--space-xs);
          margin-bottom: var(--space-xs);
        }

        /* Fluent UI Code Elements */
        code {
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 11px;
          font-weight: 400;
          background-color: var(--neutral-light);
          color: var(--neutral-primary);
          padding: var(--space-xs) var(--space-sm);
          border-radius: 2px;
          border: 1px solid var(--border-color);
        }

        /* Fluent UI Code Blocks */
        pre {
          background-color: var(--neutral-light);
          border: 1px solid var(--border-color);
          border-radius: 2px;
          padding: var(--space-lg);
          margin: var(--space-lg) 0;
          overflow-x: auto;
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 11px;
          line-height: 1.4;
        }

        pre code {
          background-color: transparent;
          border: none;
          padding: 0;
          font-size: 11px;
          color: var(--neutral-primary);
          border-radius: 0;
        }

        /* Fluent UI Multilingual Support */
        * {
          text-rendering: optimizeLegibility;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        /* Japanese text specific adjustments */
        [lang="ja"], .japanese {
          font-family: 'Noto Sans JP', 'Segoe UI', sans-serif;
          line-height: 1.6;
        }

        /* Fluent UI Link Styling */
        a {
          color: var(--primary-color);
          text-decoration: none;
        }

        a:hover {
          color: var(--primary-hover);
          text-decoration: underline;
        }

        /* Fluent UI Table Styling */
        table {
          width: 100%;
          border-collapse: collapse;
          margin: var(--space-lg) 0;
          font-size: 12px;
        }

        th, td {
          border: 1px solid var(--border-color);
          padding: var(--space-sm) var(--space-md);
          text-align: left;
        }

        th {
          background-color: var(--neutral-light);
          font-weight: 600;
          color: var(--neutral-primary);
        }

        td {
          color: var(--neutral-primary);
        }

        /* Fluent UI Blockquote */
        blockquote {
          border-left: 4px solid var(--primary-color);
          background-color: var(--neutral-light);
          padding: var(--space-md);
          margin: var(--space-lg) 0;
          font-style: italic;
          color: var(--neutral-secondary);
        }

        /* Rest of CSS as provided */
        """

    def convert(self) -> bytes:
        """
        Convert the markdown text to a styled PDF file using WeasyPrint.
        """
        import io

        import markdown2
        from weasyprint import CSS, HTML

        # Convert markdown to HTML with extra features
        html_content = markdown2.markdown(self.markdown_text, extras=["tables", "fenced-code-blocks", "code-friendly"])

        # Use custom CSS if provided, otherwise use default
        css_content = self.default_css
        if self.css_path and os.path.exists(self.css_path):
            with open(self.css_path) as f:
                css_content = f.read()

        # Create CSS object to properly handle CSS rules
        css = CSS(string=css_content)

        # Create HTML document with proper encoding for multilingual support
        html = HTML(
            string=f"""<html lang="en">
<head>
<meta charset="UTF-8">
</head>
<body>{html_content}</body>
</html>"""
        )

        # Generate PDF into a bytes buffer
        pdf_buffer = io.BytesIO()
        html.write_pdf(pdf_buffer, stylesheets=[css])

        # Return the PDF as bytes
        pdf_buffer.seek(0)
        return pdf_buffer.read()
