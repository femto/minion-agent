import re
from typing import Optional

DEEP_RESEARCH_INSTALL_HINT = "pip install 'minion-agent-x[deep-research]'"


def _missing_deep_research_dependency(error: ImportError) -> ImportError:
    return ImportError(
        f"Report generation requires the deep-research extra ({error.name} is not installed). "
        f"Install it with: {DEEP_RESEARCH_INSTALL_HINT}"
    )


def generate_pdf(answer: str, filename: str = "research_report.pdf") -> None:
    """
    Generate a PDF report from the markdown formatted research answer.
    Uses the first line of the answer as the title.

    Attempts to use pypandoc first, with fallbacks to:
    1. commonmark + xhtml2pdf if pypandoc fails
    2. A clear error message if all methods fail
    Args:
        answer: Markdown-formatted research content
        filename: Output PDF filename
    Returns:
        None. Writes PDF to file.
    """
    try:
        import pypandoc
    except ImportError as e:
        raise _missing_deep_research_dependency(e) from e

    # Extract the first line as title and rest as content
    lines = answer.split("\n")
    title = lines[0].strip("# ")  # Remove any markdown heading characters
    content = "\n".join(lines[1:]).strip()  # Get the rest of the content

    # Remove mermaid diagram blocks for pdf rendering
    content = re.sub(r"\*Figure.*?\*.*?```mermaid.*?```|```mermaid.*?```.*?\*Figure.*?\*", "\n", content, flags=re.DOTALL)
    content = content.strip()  # Remove any extra whitespace that might remain

    disclaimer = (
        "Disclaimer: This AI-generated report may contain hallucinations, bias, or inaccuracies. Always verify information "
        "from independent sources before making decisions based on this content."
    )
    content = f"{disclaimer}\n\n{content}"

    # Create markdown with the extracted title - properly quote the title for YAML
    markdown_with_title = f'---\ntitle: "{title}"\n---\n\n{content}'

    # Try pypandoc first
    try:
        pdf_options = [
            "--pdf-engine=pdflatex",
            "--variable",
            "urlcolor=blue",
            "--variable",
            "colorlinks=true",
            "--variable",
            "linkcolor=blue",
            "--variable",
            "geometry:margin=1in",
        ]

        pypandoc.convert_text(markdown_with_title, "pdf", format="markdown", outputfile=filename, extra_args=pdf_options)
        print(f"PDF generated successfully using pypandoc: {filename}")
        return
    except Exception as pandoc_error:
        print(f"Pypandoc conversion failed: {str(pandoc_error)}")
        print("Trying alternative conversion methods...")

    # Try commonmark + xhtml2pdf as a backup
    try:
        import commonmark
        from xhtml2pdf import pisa

        # Convert markdown to HTML using commonmark
        html_content = commonmark.commonmark(content)

        # Add basic HTML structure with the title
        html_doc = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333366; }}
                a {{ color: #0066cc; }}
                pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
                blockquote {{ border-left: 3px solid #ccc; padding-left: 10px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {html_content}
        </body>
        </html>
        """

        # Convert HTML to PDF using xhtml2pdf
        with open(filename, "w+b") as pdf_file:
            pisa_status = pisa.CreatePDF(html_doc, dest=pdf_file)

        if pisa_status.err:
            raise Exception("xhtml2pdf encountered errors")
        else:
            print(f"PDF generated successfully using commonmark + xhtml2pdf: {filename}")
            return

    except Exception as alt_error:
        error_msg = f"All PDF conversion methods failed. Last error: {str(alt_error)}"
        print(error_msg)
        raise Exception(error_msg)


def generate_html(
    markdown_content: str, toc_image_url: Optional[str] = None, title: Optional[str] = None, base64_audio: Optional[str] = None
) -> str:
    """
    Generate an HTML report from markdown formatted content.
    Returns the generated HTML as a string.
    Args:
        markdown_content: Markdown-formatted content
        toc_image_url: Optional image URL for the TOC/header
        title: Optional report title
        base64_audio: Optional base64-encoded audio for embedding
    Returns:
        HTML string
    """
    try:
        from pymdownx.superfences import SuperFencesCodeExtension
    except ImportError as e:
        raise _missing_deep_research_dependency(e) from e

    try:
        import datetime
        import markdown
        year = datetime.datetime.now().year
        month = datetime.datetime.now().strftime("%B")
        day = datetime.datetime.now().day
        # Extract title from first line if not provided
        lines = markdown_content.split("\n")
        if not title:
            # Remove any markdown heading characters
            title = lines[0].strip("# ")
        content = markdown_content
        # Convert markdown to HTML with table support
        html_body = markdown.markdown(
            content,
            extensions=[
                "tables",
                "fenced_code",
                SuperFencesCodeExtension(custom_fences=[{"name": "mermaid", "class": "mermaid", "format": fence_mermaid}]),
            ],
        )
        # Add mermaid header
        mermaid_header = """<script type=\"module\">\n                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';\n                mermaid.initialize({startOnLoad: true });\n            </script>"""
        # Directly parse HTML to extract headings and build TOC
        heading_pattern = re.compile(r'<h([2-3])(?:\\s+id="([^"]+)")?>([^<]+)</h\\1>')
        toc_items = []
        section_count = 0
        subsection_counts = {}
        # First pass: Add IDs to all headings that don't have them
        modified_html = html_body
        for match in heading_pattern.finditer(html_body):
            level = match.group(1)
            heading_id = match.group(2)
            heading_text = match.group(3)
            # If heading doesn't have an ID, create one and update the HTML
            if not heading_id:
                heading_id = re.sub(r"[^\\w\-]", "-", heading_text.lower())
                heading_id = re.sub(r"-+", "-", heading_id).strip("-")
                # Replace the heading without ID with one that has an ID
                original = f"<h{level}>{heading_text}</h{level}>"
                replacement = f'<h{level} id="{heading_id}">{heading_text}</h{level}>'
                modified_html = modified_html.replace(original, replacement)
        # Update the HTML body with the added IDs
        html_body = modified_html
        # Second pass: Build the TOC items
        for match in heading_pattern.finditer(modified_html):
            level = match.group(1)
            heading_id = match.group(2) or re.sub(r"[^\\w\-]", "-", match.group(3).lower())
            heading_text = match.group(3)
            if level == "2":  # Main section (h2)
                section_count += 1
                subsection_counts[section_count] = 0
                toc_items.append(f'<a class="nav-link py-1" href="#{heading_id}">{section_count}. {heading_text}</a>')
            elif level == "3":  # Subsection (h3)
                parent_section = section_count
                subsection_counts[parent_section] += 1
                subsection_num = subsection_counts[parent_section]
                toc_items.append(
                    f'<a class="nav-link py-1 ps-3" href="#{heading_id}">{parent_section}.{subsection_num}. {heading_text}</a>'
                )
        current_date = datetime.datetime.now().strftime("%B %Y")
        # Create a complete HTML document with enhanced styling and structure
        html_doc = f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
            <meta charset=\"UTF-8\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
            <title>{title}</title>
            <base target=\"_self\">
            <meta name=\"author\" content=\"Research Report\">
            <meta name=\"description\" content=\"Comprehensive research report\">
            <!-- Bootstrap CSS -->
            <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
            <!-- DataTables CSS -->
            <link href=\"https://cdn.datatables.net/1.13.5/css/dataTables.bootstrap5.min.css\" rel=\"stylesheet\">
            <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">
            {mermaid_header}
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                h1 {{
                    font-size: 2.2em;
                    border-bottom: 2px solid #e0e0e0;
                    padding-bottom: 0.5em;
                    margin-bottom: 0.7em;
                }}
                h2 {{
                    font-size: 1.8em;
                    border-bottom: 1px solid #e0e0e0;
                    padding-bottom: 0.3em;
                    margin-top: 2em;
                }}
                p {{
                    margin: 1em 0;
                }}
                code {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                    font-size: 85%;
                    padding: 0.2em 0.4em;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 16px;
                    overflow: auto;
                }}
                pre code {{
                    background-color: transparent;
                    padding: 0;
                }}
                blockquote {{
                    background-color: #f8f9fa;
                    border-left: 4px solid #6c757d;
                    padding: 1em;
                    margin: 1.5em 0;
                }}
                ul, ol {{
                    padding-left: 2em;
                }}
                /* Table styling for non-DataTables tables */
                table:not(.dataTable) {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 1em 0;
                    overflow-x: auto;
                    display: block;
                }}
                table:not(.dataTable) th, table:not(.dataTable) td {{
                    border: 1px solid #dfe2e5;
                    padding: 8px 13px;
                    text-align: left;
                }}
                table:not(.dataTable) th {{
                    background-color: #f0f0f0;
                    font-weight: 600;
                    border-bottom: 2px solid #ddd;
                }}
                table:not(.dataTable) tr:nth-child(even) {{
                    background-color: #f8f8f8;
                }}
                a {{
                    color: #0366d6;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                img {{
                    max-width: 100%;
                }}
                .container {{
                    background-color: white;
                    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
                    border-radius: 8px;
                    padding: 40px;
                }}
                /* Cursor for sortable columns */
                .dataTable thead th {{
                    cursor: pointer;
                }}
                .toc-container {{
                    background-color: #f9f9f9;
                    border-left: 3px solid #0366d6;
                    padding: 15px;
                    border-radius: 4px;
                }}
                .toc-container h5 {{
                    margin-top: 0;
                    margin-bottom: 0.7em;
                }}
                .nav-link {{
                    color: #0366d6;
                    font-size: 0.95em;
                    padding-top: 0.2em;
                    padding-bottom: 0.2em;
                }}
                .report-header {{
                    margin-bottom: 2em;
                }}
                /* Enhanced table styling */
                table:not(.dataTable) th {{
                    background-color: #f0f0f0;
                    font-weight: 600;
                    border-bottom: 2px solid #ddd;
                }}
                /* Print and citation buttons */
                .report-actions {{
                    margin: 2em 0;
                    text-align: right;
                }}
                .print-button, .cite-button {{
                    background-color: #f8f9fa;
                    border: 1px solid #ddd;
                    padding: 8px 15px;
                    border-radius: 4px;
                    margin-left: 10px;
                    color: #495057;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    font-size: 0.9em;
                }}
                .print-button:hover, .cite-button:hover {{
                    background-color: #e9ecef;
                    text-decoration: none;
                }}
                .print-button i, .cite-button i {{
                    margin-right: 5px;
                }}
                /* Academic citation formatting */
                ol.references li {{
                    margin-bottom: 1em;
                    padding-left: 1.5em;
                    text-indent: -1.5em;
                }}
            .report-header img {{
                    max-width: 100%;
                    height: auto;
                    margin-bottom: 1.5em;
                    border-radius: 4px;
                }}
            .audio-container {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    border: 1px solid #e0e0e0;
                    display: flex;
                    align-items: center;
                }}
            .audio-container i {{
                    font-size: 1.8em;
                    color: #0366d6;
                    margin-right: 15px;
                }}
            .audio-container audio {{
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="report-header mb-4">
                    <div class="text-end text-muted mb-2">
                        <small>Research Report | Published: {current_date}</small>
                    </div>
                    {f'<img src="{toc_image_url}" alt="Report Header Image">' if toc_image_url else ''}
                    <h1>{title}</h1>
                    <div class="author-info mb-3">
                        <p class="text-muted">
                            <strong>Disclaimer:</strong>
                            This AI-generated report may contain hallucinations, bias, or inaccuracies.
                            Always verify information from independent sources before making
                            decisions based on this content.
                        </p>
                    </div>
                    {f'<div class="audio-container>'
                     f'<i class="bi bi-music-note-beamed"></i>'
                     f'<audio controls>'
                     f'<source src="{base64_audio}" type="audio/mp3">'
                     f'Your browser does not support the audio element.'
                     f'</audio></div>' if base64_audio else ''}
                </div>
                <div class="report-actions">
                    <a href="#" class="cite-button" onclick="showCitation(); return false;">
                        <i class="bi bi-quote"></i> Cite
                    </a>
                    <a href="#" class="print-button" onclick="window.print(); return false;">
                        <i class="bi bi-printer"></i> Print
                    </a>
                </div>
                <div class="toc-container mb-4">
                    <h5>Table of Contents</h5>
                    <nav id="toc" class="nav flex-column">
                        {"".join(toc_items)}
                    </nav>
                </div>
                {html_body}
            </div>

            <!-- jQuery -->
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <!-- Bootstrap JS Bundle with Popper -->
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <!-- DataTables JS -->
            <script src="https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js"></script>
            <script src="https://cdn.datatables.net/1.13.5/js/dataTables.bootstrap5.min.js"></script>
            <script>
                function showCitation() {{
                    const today = new Date();
                    const year = today.getFullYear();
                    const month = today.toLocaleString('default', {{ month: 'long' }});
                    const day = today.getDate();
                    alert(`Research Report. ({year}). {title}. Retrieved {month} {day}, {year}.`);
                }}

                // Initialize all tables with DataTables
                $(document).ready(function() {{
                    $('table').each(function() {{
                        $(this).addClass('table table-striped table-bordered');
                        $(this).DataTable({{
                            responsive: true,
                            paging: $(this).find('tr').length > 10,
                            searching: $(this).find('tr').length > 10,
                            info: $(this).find('tr').length > 10,
                            order: [] // Disable initial sort
                        }});
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html_doc
    except Exception as error:
        error_msg = f"HTML conversion failed: {str(error)}"
        raise Exception(error_msg)


def save_and_generate_html(
    markdown_content: str,
    filename: Optional[str] = None,
    toc_image_url: Optional[str] = None,
    title: Optional[str] = None,
    base64_audio: Optional[str] = None,
) -> str:
    """
    Generate an HTML report from markdown formatted content and save it to a file if filename is provided.
    Returns the generated HTML.
    Args:
        markdown_content: Markdown-formatted content
        filename: Output HTML filename (optional)
        toc_image_url: Optional image URL for the TOC/header
        title: Optional report title
        base64_audio: Optional base64-encoded audio for embedding
    Returns:
        HTML string
    """
    # Generate the HTML content
    html_doc = generate_html(markdown_content, toc_image_url, title, base64_audio)
    # Save to file if filename is provided
    if filename:
        # Ensure the filename has an .html extension
        if not filename.lower().endswith(".html"):
            filename += ".html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_doc)
        print(f"HTML report generated successfully: {filename}")
    return html_doc

def fence_mermaid(source, language, css_class, options, md, **kwargs):
    """Clean and process mermaid code blocks."""
    # Filter out title lines and clean whitespace
    cleaned_lines = [line.rstrip() for line in source.split("\n") if "title" not in line]
    cleaned_source = "\n".join(cleaned_lines).strip()

    return f'<div class="mermaid">{cleaned_source}</div>'
