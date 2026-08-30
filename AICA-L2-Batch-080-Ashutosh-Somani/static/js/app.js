/* static/js/app.js */
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('file-input');

    if (dropzone && fileInput) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight dropzone
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
        });

        // Handle dropped files
        dropzone.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            let files = dt.files;
            handleFiles(files);
        });

        // Handle clicked upload
        dropzone.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            handleFiles(this.files);
        });

        function handleFiles(files) {
            if (files.length > 0) {
                const file = files[0];
                if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                    showError('Please select a valid PDF file.');
                    return;
                }
                
                uploadFile(file);
            }
        }
        
        function showError(msg) {
            const errDiv = document.getElementById('upload-error');
            if(errDiv) {
                errDiv.innerText = msg;
                errDiv.style.display = 'block';
            } else {
                alert(msg);
            }
        }
        
        function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            dropzone.style.display = 'none';
            document.getElementById('upload-progress').style.display = 'block';
            document.getElementById('upload-error').style.display = 'none';
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.redirect;
                } else {
                    showError(data.error || 'Upload failed');
                    dropzone.style.display = 'block';
                    document.getElementById('upload-progress').style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Network error or server unavailable.');
                dropzone.style.display = 'block';
                document.getElementById('upload-progress').style.display = 'none';
            });
        }
    }
});
