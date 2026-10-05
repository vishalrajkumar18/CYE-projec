import markdown
from xhtml2pdf import pisa

def convert():
    with open('project_report.md', 'r') as f:
        text = f.read()

    # Convert markdown to html
    html = markdown.markdown(text)
    
    # Wrap in basic HTML structure
    html = f"<html><body>{html}</body></html>"

    with open('project_report.pdf', 'wb') as f:
        pisa.CreatePDF(html, dest=f)

if __name__ == "__main__":
    convert()
