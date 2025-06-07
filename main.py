import os
import sys
import tempfile
import json
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, request, jsonify, send_file
from flask_cors import CORS
import werkzeug.utils

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
CORS(app)  # Enable CORS for all routes
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

def convert_py_to_ipynb(py_file_path, ipynb_file_path):
    """Convert Python file to Jupyter Notebook"""
    with open(py_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    current_cell_type = "code"
    current_cell_content = []
    in_docstring = False

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
            in_docstring = not in_docstring
            if in_docstring:  # Start of a docstring, potentially a markdown cell
                if current_cell_content and current_cell_type == "code":
                    notebook["cells"].append({
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": "".join(current_cell_content)
                    })
                    current_cell_content = []
                current_cell_type = "markdown"
                current_cell_content.append(line)
            else:  # End of a docstring
                current_cell_content.append(line)
                if current_cell_content:
                    notebook["cells"].append({
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": "".join(current_cell_content)
                    })
                current_cell_content = []
                current_cell_type = "code"  # After docstring, assume code again
        elif stripped_line.startswith("# ##") and not in_docstring:
            if current_cell_content:
                if current_cell_type == "code":
                    notebook["cells"].append({
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": "".join(current_cell_content)
                    })
                elif current_cell_type == "markdown":
                    notebook["cells"].append({
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": "".join(current_cell_content)
                    })
            current_cell_content = []
            current_cell_type = "markdown"
            current_cell_content.append(line.lstrip("# ").lstrip("## "))  # Remove leading # and spaces
        else:
            if not in_docstring and current_cell_type == "markdown":
                # If we are in markdown mode but the line is not a docstring or markdown header, it's code
                if current_cell_content:
                    notebook["cells"].append({
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": "".join(current_cell_content)
                    })
                    current_cell_content = []
                current_cell_type = "code"
            current_cell_content.append(line)

    # Add the last cell
    if current_cell_content:
        if current_cell_type == "code":
            notebook["cells"].append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": "".join(current_cell_content)
            })
        elif current_cell_type == "markdown":
            notebook["cells"].append({
                "cell_type": "markdown",
                "metadata": {},
                "source": "".join(current_cell_content)
            })

    with open(ipynb_file_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=4, ensure_ascii=False)

@app.route('/api/convert', methods=['POST'])
def convert_file():
    """API endpoint to convert Python file to Jupyter Notebook"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.endswith('.py'):
        return jsonify({'error': 'File must be a Python file (.py)'}), 400
    
    # Save the uploaded file
    filename = werkzeug.utils.secure_filename(file.filename)
    py_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(py_file_path)
    
    # Convert to Jupyter Notebook
    ipynb_filename = os.path.splitext(filename)[0] + '.ipynb'
    ipynb_file_path = os.path.join(app.config['UPLOAD_FOLDER'], ipynb_filename)
    
    try:
        convert_py_to_ipynb(py_file_path, ipynb_file_path)
        
        # Return the converted file
        return send_file(
            ipynb_file_path,
            as_attachment=True,
            download_name=ipynb_filename,
            mimetype='application/x-ipynb+json'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(py_file_path):
                os.remove(py_file_path)
            if os.path.exists(ipynb_file_path):
                # Only remove after sending
                pass
        except:
            pass

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

