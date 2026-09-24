"""
Generates an inline preview for an uploaded design file, where possible.

- Images (png/jpg/jpeg) are already previewable as-is, no extra work needed.
- PDFs get a thumbnail of their first page, IF the optional PyMuPDF (fitz)
  package is installed. If it isn't installed, we just skip the thumbnail
  and the UI falls back to a generic file icon + download link - nothing
  breaks either way.
- Other formats (docx, pptx, ai, psd, svg) have no generic preview here and
  fall back to the file icon + download link too.
"""

import os


PREVIEWABLE_IMAGE_EXTS = {'png', 'jpg', 'jpeg'}


def generate_preview(file_path, stored_filename, upload_folder):
    """Returns the filename (within upload_folder) to use as a preview image,
    or None if no preview could be made."""
    ext = stored_filename.rsplit('.', 1)[-1].lower() if '.' in stored_filename else ''

    if ext in PREVIEWABLE_IMAGE_EXTS:
        return stored_filename  # the uploaded file itself can be shown directly

    if ext == 'pdf':
        try:
            import fitz  # PyMuPDF - optional dependency
        except ImportError:
            return None

        try:
            doc = fitz.open(file_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.6, 0.6))
            preview_name = f'preview_{stored_filename}.png'
            pix.save(os.path.join(upload_folder, preview_name))
            doc.close()
            return preview_name
        except Exception:
            return None

    return None
