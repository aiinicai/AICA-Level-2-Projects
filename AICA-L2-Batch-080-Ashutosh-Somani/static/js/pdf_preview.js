document.addEventListener('DOMContentLoaded', () => {
    const pdfUrlInput = document.getElementById('pdf-url');
    if (!pdfUrlInput) return;

    const url = pdfUrlInput.value;

    let pdfDoc = null,
        pageNum = 1,
        pageRendering = false,
        pageNumPending = null,
        scale = 1.0,
        canvas = document.getElementById('pdf-canvas'),
        ctx = canvas.getContext('2d');

    // Specify the workerSrc
    pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/build/pdf.worker.js';

    function renderPage(num) {
        pageRendering = true;
        
        pdfDoc.getPage(num).then(function(page) {
            let viewport = page.getViewport({scale: scale});
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            let renderContext = {
                canvasContext: ctx,
                viewport: viewport
            };
            
            let renderTask = page.render(renderContext);

            renderTask.promise.then(function() {
                pageRendering = false;
                if (pageNumPending !== null) {
                    renderPage(pageNumPending);
                    pageNumPending = null;
                }
            });
        });

        document.getElementById('page-num').textContent = num;
    }

    function queueRenderPage(num) {
        if (pageRendering) {
            pageNumPending = num;
        } else {
            renderPage(num);
        }
    }

    function onPrevPage() {
        if (pageNum <= 1) {
            return;
        }
        pageNum--;
        queueRenderPage(pageNum);
    }
    document.getElementById('prev-page').addEventListener('click', onPrevPage);

    function onNextPage() {
        if (pageNum >= pdfDoc.numPages) {
            return;
        }
        pageNum++;
        queueRenderPage(pageNum);
    }
    document.getElementById('next-page').addEventListener('click', onNextPage);
    
    function onZoomIn() {
        scale += 0.25;
        document.getElementById('zoom-val').textContent = Math.round(scale * 100) + '%';
        queueRenderPage(pageNum);
    }
    document.getElementById('zoom-in').addEventListener('click', onZoomIn);
    
    function onZoomOut() {
        if (scale <= 0.5) return;
        scale -= 0.25;
        document.getElementById('zoom-val').textContent = Math.round(scale * 100) + '%';
        queueRenderPage(pageNum);
    }
    document.getElementById('zoom-out').addEventListener('click', onZoomOut);

    // Asynchronously download PDF
    pdfjsLib.getDocument(url).promise.then(function(pdfDoc_) {
        pdfDoc = pdfDoc_;
        document.getElementById('page-count').textContent = pdfDoc.numPages;

        renderPage(pageNum);
    }).catch(function(error) {
        console.error('Error loading PDF: ', error);
        alert('Failed to load PDF preview.');
    });
});
